from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db
from ..models import User
from ..services.github import GitHubClient
from ..auth import get_current_user

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
