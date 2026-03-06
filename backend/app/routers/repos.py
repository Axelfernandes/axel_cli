from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db, async_session_maker
from ..models import User, RepoStatus
from ..services.github import GitHubClient
from ..auth import get_current_user
from ..services.embeddings import get_embedding_service
from .chat import get_user_api_key
from fastapi import BackgroundTasks

router = APIRouter(prefix="/repos", tags=["repos"])

class ContentsResponse(BaseModel):
    name: str
    path: str
    type: str
    size: Optional[int] = None
    content: Optional[str] = None

class BranchResponse(BaseModel):
    name: str
    sha: str

class CreateBranchRequest(BaseModel):
    branch_name: str
    source_branch: Optional[str] = None

class UpdateFileRequest(BaseModel):
    path: str
    content: str
    message: str
    branch: str
    sha: Optional[str] = None

class CreatePRRequest(BaseModel):
    title: str
    body: str
    head: str
    base: str

async def get_github_client(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> GitHubClient:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    return GitHubClient(user.github_token)

@router.get("")
async def list_repos(
    page: int = 1,
    search: Optional[str] = None,
    github: GitHubClient = Depends(get_github_client),
):
    if search:
        results = await github.search_repos(search, page)
        return {
            "repos": results.get("items", []),
            "total_count": results.get("total_count", 0),
        }
    repos = await github.get_user_repos(page)
    return {"repos": repos}

@router.get("/{owner}/{repo}/contents")
async def get_contents(
    owner: str,
    repo: str,
    path: str = "",
    ref: Optional[str] = None,
    github: GitHubClient = Depends(get_github_client),
):
    try:
        contents = await github.get_contents(owner, repo, path, ref)
        return contents
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{owner}/{repo}/file")
async def get_file(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
    github: GitHubClient = Depends(get_github_client),
):
    content = await github.get_file_content(owner, repo, path, ref)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": content}

@router.get("/{owner}/{repo}/branches")
async def list_branches(
    owner: str,
    repo: str,
    github: GitHubClient = Depends(get_github_client),
):
    branches = await github.get_branches(owner, repo)
    return {"branches": branches}

@router.post("/{owner}/{repo}/branches")
async def create_branch(
    owner: str,
    repo: str,
    request: CreateBranchRequest,
    github: GitHubClient = Depends(get_github_client),
):
    if request.source_branch:
        source_sha = await github.get_branch_sha(owner, repo, request.source_branch)
    else:
        default_branch = await github.get_default_branch(owner, repo)
        source_sha = await github.get_branch_sha(owner, repo, default_branch)
    
    result = await github.create_branch(owner, repo, request.branch_name, source_sha)
    return result

@router.put("/{owner}/{repo}/contents")
async def update_file(
    owner: str,
    repo: str,
    request: UpdateFileRequest,
    github: GitHubClient = Depends(get_github_client),
):
    if request.sha is None:
        try:
            existing = await github.get_file_content(owner, repo, request.path, request.branch)
            if existing:
                import base64
                existing_data = await github.get_contents(owner, repo, request.path, request.branch)
                if isinstance(existing_data, dict):
                    request.sha = existing_data.get("sha")
        except:
            pass
    
    result = await github.update_file(
        owner, repo, request.path, request.content,
        request.message, request.branch, request.sha,
    )
    return result

@router.post("/{owner}/{repo}/pulls")
async def create_pull_request(
    owner: str,
    repo: str,
    request: CreatePRRequest,
    github: GitHubClient = Depends(get_github_client),
):
    result = await github.create_pull_request(
        owner, repo, request.title, request.body,
        request.head, request.base,
    )
    return result

async def run_indexing(owner: str, repo: str, github: GitHubClient, user_id: str, openai_key: Optional[str], gemini_key: Optional[str]):
    """Background task to index all files in a repository."""
    repo_full_name = f"{owner}/{repo}"
    
    async with async_session_maker() as db:
        try:
            # 1. Initialize Status
            result = await db.execute(
                select(RepoStatus).where(
                    RepoStatus.user_id == user_id, 
                    RepoStatus.repo_full_name == repo_full_name
                )
            )
            status_record = result.scalar_one_or_none()
            if not status_record:
                status_record = RepoStatus(
                    user_id=user_id,
                    repo_full_name=repo_full_name,
                    status="indexing",
                    progress=0
                )
                db.add(status_record)
            else:
                status_record.status = "indexing"
                status_record.progress = 0
            
            await db.commit()
            await db.refresh(status_record)

            # 2. Get all file metadata
            files_metadata = await github.get_all_contents_recursive(owner, repo)
            
            # 3. Filter for text files
            text_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.md', '.json', '.txt', '.yml', '.yaml', '.Dockerfile'}
            files_to_fetch = [
                item for item in files_metadata 
                if any(item['name'].endswith(ext) for ext in text_extensions)
            ]
            
            status_record.total_files = len(files_to_fetch)
            await db.commit()

            # 4. Fetch and Index individually to show progress
            to_index = []
            indexed_count = 0
            
            try:
                embedding_service = get_embedding_service(openai_key=openai_key, gemini_key=gemini_key)
            except ValueError as ve:
                print(f"Embedding Service Error: {ve}")
                if status_record:
                    status_record.status = "failed"
                    await db.commit()
                return

            for item in files_to_fetch:
                content = await github.get_file_content(owner, repo, item['path'])
                if content and isinstance(content, str):
                    embedding_service.index_files([{"path": item['path'], "content": content}])
                    indexed_count += 1
                    
                    # Update progress every few files or every file
                    status_record.indexed_files = indexed_count
                    status_record.progress = int((indexed_count / len(files_to_fetch)) * 100)
                    await db.commit()
            
            status_record.status = "completed"
            status_record.progress = 100
            await db.commit()
            
            print(f"Successfully indexed {indexed_count} files for {repo_full_name}")
        except Exception as e:
            if status_record:
                status_record.status = "failed"
                await db.commit()
            print(f"Indexing Error for {repo_full_name}: {str(e)}")

@router.post("/{owner}/{repo}/index")
async def index_repo(
    owner: str,
    repo: str,
    background_tasks: BackgroundTasks,
    github: GitHubClient = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    # Get user for API key access
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    
    # Pass decrypted key and user_id to background task
    openai_key = get_user_api_key(user, "openai")
    gemini_key = get_user_api_key(user, "gemini")
    background_tasks.add_task(run_indexing, owner, repo, github, user.id, openai_key, gemini_key)
    return {"message": "Indexing started in the background"}

@router.get("/{owner}/{repo}/index-status")
async def get_index_status(
    owner: str,
    repo: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    
    repo_full_name = f"{owner}/{repo}"
    result = await db.execute(
        select(RepoStatus).where(
            RepoStatus.user_id == user.id,
            RepoStatus.repo_full_name == repo_full_name
        )
    )
    status_record = result.scalar_one_or_none()
    
    if not status_record:
        return {"status": "none", "progress": 0}
    
    return {
        "status": status_record.status,
        "progress": status_record.progress,
        "total_files": status_record.total_files,
        "indexed_files": status_record.indexed_files,
        "updated_at": status_record.updated_at.isoformat()
    }

@router.post("/{owner}/{repo}/scaffold")
async def scaffold_repo(
    owner: str,
    repo: str,
    template_type: str = "react-native",
    github: GitHubClient = Depends(get_github_client),
):
    """Scaffold a new project structure in a dedicated branch."""
    if template_type != "react-native":
        raise HTTPException(status_code=400, detail="Only react-native template is currently supported")
    
    branch_name = "axel/mobile-base"
    
    # 1. Create the branch (from default branch)
    try:
        default_branch = await github.get_default_branch(owner, repo)
        source_sha = await github.get_branch_sha(owner, repo, default_branch)
        await github.create_branch(owner, repo, branch_name, source_sha)
    except Exception as e:
        # If branch exists, we just proceed or handle it
        if "already exists" not in str(e).lower():
            raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")

    # 2. Define React Native boilerplate files
    files = [
        {
            "path": "App.tsx",
            "content": "import React from 'react';\nimport { StyleSheet, Text, View } from 'react-native';\n\nexport default function App() {\n  return (\n    <View style={styles.container}>\n      <Text>Welcome to Axel Mobile!</Text>\n    </View>\n  );\n}\n\nconst styles = StyleSheet.create({\n  container: {\n    flex: 1,\n    backgroundColor: '#fff',\n    alignItems: 'center',\n    justifyContent: 'center',\n  },\n});"
        },
        {
            "path": "package.json",
            "content": "{\n  \"name\": \"AxelMobileApp\",\n  \"version\": \"0.0.1\",\n  \"private\": true,\n  \"scripts\": {\n    \"android\": \"react-native run-android\",\n    \"ios\": \"react-native run-ios\",\n    \"start\": \"react-native start\"\n  },\n  \"dependencies\": {\n    \"react\": \"18.2.0\",\n    \"react-native\": \"0.72.6\"\n  }\n}"
        },
        {
            "path": "axel-project.json",
            "content": "{\n  \"template\": \"react-native\",\n  \"created_by\": \"Axel Agent\"\n}"
        }
    ]
    
    # 3. Push files in bulk
    try:
        await github.create_bulk_files(
            owner, repo, files, 
            message="Initial Axel React Native scaffolding", 
            branch=branch_name
        )
        return {"message": f"Successfully scaffolded {template_type} in branch {branch_name}", "branch": branch_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scaffolding failed: {str(e)}")
