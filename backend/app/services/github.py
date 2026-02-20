import httpx
from typing import Optional, List, Dict, Any, Union

GITHUB_API_URL = "https://api.github.com"

class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def get_user_repos(self, page: int = 1, per_page: int = 30):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/user/repos",
                params={"page": page, "per_page": per_page, "sort": "updated"},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def search_repos(self, query: str, page: int = 1, per_page: int = 30):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/search/repositories",
                params={"q": query, "page": page, "per_page": per_page},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo(self, owner: str, repo: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_contents(self, owner: str, repo: str, path: str = "", ref: Optional[str] = None):
        async with httpx.AsyncClient() as client:
            params = {}
            if ref:
                params["ref"] = ref
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_file_content(self, owner: str, repo: str, path: str, ref: Optional[str] = None):
        async with httpx.AsyncClient() as client:
            params = {}
            if ref:
                params["ref"] = ref
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                params=params,
                headers=self.headers,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("encoding") == "base64":
                import base64
                return base64.b64decode(data["content"]).decode("utf-8")
            return data
    
    async def get_branches(self, owner: str, repo: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/branches",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_default_branch(self, owner: str, repo: str):
        repo_data = await self.get_repo(owner, repo)
        return repo_data.get("default_branch", "main")
    
    async def get_branch_sha(self, owner: str, repo: str, branch: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/branches/{branch}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()["commit"]["sha"]
    
    async def create_branch(self, owner: str, repo: str, branch_name: str, source_sha: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs",
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": source_sha,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None,
    ):
        import base64
        async with httpx.AsyncClient() as client:
            data = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
            }
            if sha:
                data["sha"] = sha
            response = await client.put(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                json=data,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_pull_request(self, owner: str, repo: str, pull_number: int):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pull_number}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_all_contents_recursive(self, owner: str, repo: str, path: str = "", ref: Optional[str] = None) -> List[Dict]:
        """Recursively fetch all file metadata from a repository."""
        results = []
        contents = await self.get_contents(owner, repo, path, ref)
        
        if isinstance(contents, list):
            for item in contents:
                if item["type"] == "dir":
                    results.extend(await self.get_all_contents_recursive(owner, repo, item["path"], ref))
                else:
                    results.append(item)
        elif isinstance(contents, dict):
            # Single file
            results.append(contents)
            
        return results

    async def create_bulk_files(
        self,
        owner: str,
        repo: str,
        files: List[Dict[str, str]],  # List of {"path": "...", "content": "..."}
        message: str,
        branch: str,
    ):
        """Create multiple files in a single commit using the Trees API."""
        async with httpx.AsyncClient() as client:
            # 1. Get the latest commit SHA of the branch
            ref_resp = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                headers=self.headers
            )
            ref_resp.raise_for_status()
            base_sha = ref_resp.json()["object"]["sha"]

            # 2. Get the tree SHA of that commit
            commit_resp = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits/{base_sha}",
                headers=self.headers
            )
            commit_resp.raise_for_status()
            base_tree_sha = commit_resp.json()["tree"]["sha"]

            # 3. Create a new tree with the new files
            tree_data = []
            for f in files:
                tree_data.append({
                    "path": f["path"],
                    "mode": "100644",
                    "type": "blob",
                    "content": f["content"]
                })

            tree_resp = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees",
                json={
                    "base_tree": base_tree_sha,
                    "tree": tree_data
                },
                headers=self.headers
            )
            tree_resp.raise_for_status()
            new_tree_sha = tree_resp.json()["sha"]

            # 4. Create a new commit
            new_commit_resp = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits",
                json={
                    "message": message,
                    "tree": new_tree_sha,
                    "parents": [base_sha]
                },
                headers=self.headers
            )
            new_commit_resp.raise_for_status()
            new_commit_sha = new_commit_resp.json()["sha"]

            # 5. Update the reference
            final_resp = await client.patch(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                json={"sha": new_commit_sha},
                headers=self.headers
            )
            final_resp.raise_for_status()
            return final_resp.json()
