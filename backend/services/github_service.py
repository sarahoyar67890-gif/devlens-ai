"""
DevLens AI - GitHub Data Service
Fetches profile, repos, commits, languages from GitHub API
"""
import httpx
import asyncio
from typing import Optional
from loguru import logger
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.config import settings


class GitHubService:
    def __init__(self):
        self.base_url = settings.GITHUB_API_BASE
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    async def fetch_profile(self, username: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/users/{username}", headers=self.headers)
            if resp.status_code == 404:
                raise ValueError(f"GitHub user '{username}' not found.")
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub API error: {resp.status_code}")
            data = resp.json()
            return {
                "username": data.get("login"),
                "name": data.get("name") or data.get("login"),
                "bio": data.get("bio") or "",
                "avatar_url": data.get("avatar_url"),
                "location": data.get("location") or "Unknown",
                "company": data.get("company") or "",
                "blog": data.get("blog") or "",
                "email": data.get("email") or "",
                "public_repos": data.get("public_repos", 0),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
                "created_at": data.get("created_at", ""),
                "twitter_username": data.get("twitter_username") or "",
                "hireable": data.get("hireable") or False,
            }

    async def fetch_repos(self, username: str) -> list[dict]:
        repos = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            page = 1
            while True:
                resp = await client.get(
                    f"{self.base_url}/users/{username}/repos",
                    headers=self.headers,
                    params={"per_page": 100, "page": page, "sort": "updated"}
                )
                if resp.status_code != 200:
                    break
                batch = resp.json()
                if not batch:
                    break
                for r in batch:
                    repos.append({
                        "name": r.get("name"),
                        "full_name": r.get("full_name"),
                        "description": r.get("description") or "",
                        "language": r.get("language") or "Unknown",
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "watchers": r.get("watchers_count", 0),
                        "open_issues": r.get("open_issues_count", 0),
                        "size": r.get("size", 0),
                        "topics": r.get("topics", []),
                        "has_wiki": r.get("has_wiki", False),
                        "has_pages": r.get("has_pages", False),
                        "license": r.get("license", {}).get("name") if r.get("license") else None,
                        "default_branch": r.get("default_branch", "main"),
                        "created_at": r.get("created_at", ""),
                        "updated_at": r.get("updated_at", ""),
                        "pushed_at": r.get("pushed_at", ""),
                        "homepage": r.get("homepage") or "",
                        "is_fork": r.get("fork", False),
                        "url": r.get("html_url", ""),
                        "clone_url": r.get("clone_url", ""),
                    })
                page += 1
                if page > 10:
                    break
        return repos

    async def fetch_readme(self, username: str, repo_name: str) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            import base64
            resp = await client.get(
                f"{self.base_url}/repos/{username}/{repo_name}/readme",
                headers=self.headers
            )
            if resp.status_code == 200:
                content = resp.json().get("content", "")
                try:
                    return base64.b64decode(content).decode("utf-8", errors="ignore")[:3000]
                except Exception:
                    return ""
        return ""

    async def fetch_languages(self, username: str, repo_name: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{username}/{repo_name}/languages",
                headers=self.headers
            )
            if resp.status_code == 200:
                return resp.json()
        return {}

    async def fetch_commit_count(self, username: str, repo_name: str) -> int:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{username}/{repo_name}/commits",
                headers=self.headers,
                params={"per_page": 1, "author": username}
            )
            if resp.status_code == 200:
                link = resp.headers.get("link", "")
                if 'rel="last"' in link:
                    try:
                        last_part = [x for x in link.split(",") if 'rel="last"' in x][0]
                        page_num = int(last_part.split("page=")[-1].split(">")[0])
                        return page_num
                    except Exception:
                        return len(resp.json())
                return len(resp.json())
        return 0

    async def enrich_repos(self, username: str, repos: list[dict]) -> list[dict]:
        """Add README + languages to each repo (limit to 15 repos to stay in rate limit)"""
        enriched = []
        target_repos = [r for r in repos if not r["is_fork"]][:15]
        for repo in target_repos:
            logger.info(f"Enriching {repo['name']}...")
            readme = await self.fetch_readme(username, repo["name"])
            languages = await self.fetch_languages(username, repo["name"])
            commits = await self.fetch_commit_count(username, repo["name"])
            enriched.append({**repo, "readme": readme, "languages": languages, "commit_count": commits})
            await asyncio.sleep(0.2)  # gentle throttle
        return enriched

    async def get_all_languages(self, repos: list[dict]) -> dict:
        """Aggregate language bytes across all repos"""
        totals = {}
        for r in repos:
            for lang, bytes_count in r.get("languages", {}).items():
                totals[lang] = totals.get(lang, 0) + bytes_count
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))
