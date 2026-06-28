"""
DevLens AI - Analysis Orchestrator
Coordinates the full analysis pipeline
"""
import asyncio
from loguru import logger
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.services.github_service import GitHubService
from backend.services.ai_service import AIAnalysisService


class AnalysisPipeline:
    def __init__(self):
        self.github = GitHubService()
        self.ai = AIAnalysisService()

    async def run(self, username: str, progress_callback=None) -> dict:
        """Run the full analysis pipeline for a GitHub username"""

        def notify(step: str, pct: int):
            logger.info(f"[{pct}%] {step}")
            if progress_callback:
                progress_callback(step, pct)

        notify("Fetching GitHub profile...", 5)
        profile = await self.github.fetch_profile(username)

        notify("Fetching repositories...", 15)
        repos_raw = await self.github.fetch_repos(username)

        if not repos_raw:
            return {"error": "No public repositories found."}

        notify(f"Enriching {min(15, len(repos_raw))} repositories with README & languages...", 25)
        repos = await self.github.enrich_repos(username, repos_raw)

        notify("Aggregating language statistics...", 45)
        all_languages = await self.github.get_all_languages(repos)

        notify("Running AI analysis on each repository...", 55)
        analyses = []
        for i, repo in enumerate(repos):
            notify(f"Analyzing {repo['name']}...", 55 + int((i / len(repos)) * 20))
            analysis = await self.ai.analyze_repo(repo)
            analyses.append({**analysis, "repo_name": repo["name"]})

        notify("Generating developer profile & skills...", 78)
        developer_profile = await self.ai.generate_developer_profile(
            profile, repos, analyses, all_languages
        )

        notify("Assembling final report...", 92)
        result = {
            **developer_profile,
            "repos": [
                {**repo, "analysis": analyses[i]}
                for i, repo in enumerate(repos)
            ],
            "analyses": analyses,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        notify("Analysis complete!", 100)
        return result
