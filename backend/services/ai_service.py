"""
DevLens AI - AI Analysis Service
Uses Ollama local LLM to analyze repos and generate insights
Falls back to rule-based analysis if Ollama is unavailable
"""
import httpx
import json
import re
from loguru import logger
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.config import settings


class AIAnalysisService:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self._ollama_available = None

    async def _check_ollama(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                self._ollama_available = resp.status_code == 200
        except Exception:
            self._ollama_available = False
        logger.info(f"Ollama available: {self._ollama_available}")
        return self._ollama_available

    async def _ask_ollama(self, prompt: str, max_tokens: int = 800) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}},
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
        return ""

    async def analyze_repo(self, repo: dict) -> dict:
        """Analyze a single repository with AI"""
        use_ai = await self._check_ollama()
        if use_ai:
            return await self._ai_repo_analysis(repo)
        return self._rule_based_repo_analysis(repo)

    async def _ai_repo_analysis(self, repo: dict) -> dict:
        readme_snippet = repo.get("readme", "")[:800]
        languages = list(repo.get("languages", {}).keys())
        prompt = f"""Analyze this GitHub repository and respond ONLY in JSON format.

Repository: {repo['name']}
Description: {repo.get('description', 'No description')}
Languages: {', '.join(languages) if languages else repo.get('language', 'Unknown')}
Stars: {repo.get('stars', 0)}
Forks: {repo.get('forks', 0)}
Size (KB): {repo.get('size', 0)}
Topics: {', '.join(repo.get('topics', []))}
README preview: {readme_snippet}

Return ONLY this JSON (no extra text):
{{
  "purpose": "one sentence what this project does",
  "architecture": "brief architecture description",
  "complexity": 7,
  "code_quality": 7,
  "documentation_score": 6,
  "originality": 7,
  "maintainability": 7,
  "difficulty_level": "Intermediate",
  "learning_value": 8,
  "tech_tags": ["Python", "FastAPI"],
  "summary": "2-3 sentence overall project summary"
}}"""
        raw = await self._ask_ollama(prompt)
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return self._rule_based_repo_analysis(repo)

    def _rule_based_repo_analysis(self, repo: dict) -> dict:
        """Fallback rule-based analysis when Ollama is unavailable"""
        size = repo.get("size", 0)
        stars = repo.get("stars", 0)
        has_readme = bool(repo.get("readme", ""))
        topics = repo.get("topics", [])
        languages = list(repo.get("languages", {}).keys())
        lang = repo.get("language") or (languages[0] if languages else "Unknown")
        commits = repo.get("commit_count", 0)

        # Score heuristics
        complexity = min(10, max(1, int(size / 200) + (3 if commits > 20 else 1)))
        doc_score = 7 if has_readme else 3
        quality = min(10, max(1, doc_score - 1 + (1 if topics else 0) + (1 if commits > 10 else 0)))
        originality = min(10, max(3, 5 + (1 if stars > 5 else 0) + (1 if len(topics) > 2 else 0)))

        if complexity <= 3:
            difficulty = "Beginner"
        elif complexity <= 6:
            difficulty = "Intermediate"
        else:
            difficulty = "Advanced"

        # Build purpose from description
        purpose = repo.get("description") or f"A {lang} project"

        return {
            "purpose": purpose,
            "architecture": f"{'Multi-language' if len(languages) > 2 else lang}-based project",
            "complexity": complexity,
            "code_quality": quality,
            "documentation_score": doc_score,
            "originality": originality,
            "maintainability": quality,
            "difficulty_level": difficulty,
            "learning_value": min(10, quality + 1),
            "tech_tags": languages[:5] or [lang],
            "summary": f"{purpose}. Built with {lang}. {'Well documented.' if has_readme else 'Lacks documentation.'}"
        }

    async def generate_developer_profile(self, profile: dict, repos: list[dict], analyses: list[dict], all_languages: dict) -> dict:
        """Generate complete developer profile analysis"""
        use_ai = await self._check_ollama()
        skills = self._detect_skills(repos, all_languages)
        radar = self._generate_radar(skills, repos, analyses)
        internship = self._estimate_internship_readiness(skills, repos, analyses)
        rankings = self._rank_repos(repos, analyses)
        timeline = self._build_timeline(repos)
        career = self._generate_career_roadmap(skills)

        ai_summary = ""
        if use_ai:
            ai_summary = await self._generate_ai_summary(profile, repos, skills, internship)

        return {
            "profile": profile,
            "skills": skills,
            "radar": radar,
            "internship_readiness": internship,
            "repo_rankings": rankings,
            "timeline": timeline,
            "career_roadmap": career,
            "ai_summary": ai_summary or self._rule_based_summary(profile, skills, internship),
            "total_repos": len(repos),
            "total_stars": sum(r.get("stars", 0) for r in repos),
            "total_forks": sum(r.get("forks", 0) for r in repos),
            "languages_breakdown": all_languages,
            "top_languages": list(all_languages.keys())[:8],
        }

    def _detect_skills(self, repos: list[dict], all_languages: dict) -> dict:
        """Detect skills from repos and languages"""
        skill_map = {
            "Python": ["python", ".py", "django", "flask", "fastapi", "pytorch", "tensorflow", "pandas"],
            "JavaScript": ["javascript", "js", "node", "react", "vue", "angular", "express"],
            "TypeScript": ["typescript", "ts"],
            "Java": ["java", "spring", "maven", "gradle"],
            "C++": ["c++", "cpp", "cmake"],
            "C#": ["c#", "csharp", "dotnet", ".net"],
            "Go": ["golang", "go"],
            "Rust": ["rust", "cargo"],
            "React": ["react", "jsx", "tsx", "nextjs", "next.js"],
            "FastAPI": ["fastapi", "fast-api"],
            "Django": ["django"],
            "Flask": ["flask"],
            "Machine Learning": ["scikit", "sklearn", "machine learning", "ml", "xgboost", "lightgbm"],
            "Deep Learning": ["pytorch", "tensorflow", "keras", "neural", "deep learning", "cnn", "lstm"],
            "NLP": ["nlp", "transformers", "bert", "gpt", "spacy", "nltk", "hugging"],
            "Computer Vision": ["opencv", "cv2", "yolo", "image classification", "object detection"],
            "LLMs": ["langchain", "llamaindex", "llm", "openai", "ollama", "rag", "embeddings"],
            "Data Science": ["pandas", "numpy", "matplotlib", "seaborn", "jupyter", "analysis"],
            "Docker": ["docker", "dockerfile", "docker-compose", "container"],
            "SQL": ["sql", "sqlite", "mysql", "postgresql", "postgres"],
            "MongoDB": ["mongodb", "mongo", "pymongo", "mongoose"],
            "Redis": ["redis", "celery"],
            "API Development": ["api", "rest", "restful", "graphql", "fastapi", "flask"],
            "Git": ["git", "github", "gitlab"],
            "Cloud": ["aws", "azure", "gcp", "heroku", "vercel", "netlify", "cloud"],
            "DevOps": ["ci/cd", "github actions", "jenkins", "kubernetes", "k8s", "terraform"],
        }

        lang_names = [l.lower() for l in all_languages.keys()]
        all_text = []
        for repo in repos:
            all_text.append(repo.get("description", "").lower())
            all_text.append(" ".join(repo.get("topics", [])).lower())
            all_text.append(repo.get("readme", "")[:1000].lower())
        combined = " ".join(all_text) + " " + " ".join(lang_names)

        detected = {}
        for skill, keywords in skill_map.items():
            hits = sum(1 for kw in keywords if kw in combined)
            if hits > 0:
                base_score = min(95, 50 + hits * 10)
                # Boost if it's a primary language
                if skill.lower() in lang_names:
                    base_score = min(95, base_score + 15)
                detected[skill] = base_score

        return dict(sorted(detected.items(), key=lambda x: x[1], reverse=True))

    def _generate_radar(self, skills: dict, repos: list[dict], analyses: list[dict]) -> dict:
        """Generate radar chart scores across dimensions"""
        def avg(keys):
            vals = [skills.get(k, 0) for k in keys if k in skills]
            return round(sum(vals) / len(vals)) if vals else 20

        total_repos = len(repos)
        avg_complexity = sum(a.get("complexity", 5) for a in analyses) / max(len(analyses), 1)
        avg_doc = sum(a.get("documentation_score", 5) for a in analyses) / max(len(analyses), 1)

        return {
            "Programming": avg(["Python", "JavaScript", "Java", "C++", "TypeScript", "Go", "Rust"]),
            "AI & ML": avg(["Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLMs"]),
            "Backend": avg(["FastAPI", "Django", "Flask", "API Development", "SQL", "MongoDB"]),
            "Frontend": avg(["JavaScript", "React", "TypeScript"]),
            "Database": avg(["SQL", "MongoDB", "Redis"]),
            "DevOps": avg(["Docker", "Cloud", "DevOps", "Git"]),
            "Architecture": min(95, int(avg_complexity * 9)),
            "Documentation": min(95, int(avg_doc * 9)),
            "Project Scale": min(95, total_repos * 6),
            "Data Science": avg(["Data Science", "Machine Learning"]),
        }

    def _estimate_internship_readiness(self, skills: dict, repos: list[dict], analyses: list[dict]) -> dict:
        """Estimate readiness for different internship roles"""
        def score(role_skills, bonus_repos=0):
            vals = [skills.get(s, 0) for s in role_skills if s in skills]
            base = sum(vals) / len(role_skills) if role_skills else 0
            return min(100, int(base * 0.85 + bonus_repos * 3))

        non_fork = [r for r in repos if not r.get("is_fork")]
        return {
            "Backend Engineer": {"score": score(["Python", "FastAPI", "Django", "Flask", "SQL", "API Development"], len(non_fork)), "reason": "Based on backend frameworks and API projects"},
            "Frontend Engineer": {"score": score(["JavaScript", "React", "TypeScript"], 0), "reason": "Based on frontend skills detected"},
            "AI Engineer": {"score": score(["Machine Learning", "Deep Learning", "LLMs", "Python"], len(non_fork)), "reason": "Based on AI/ML projects and skills"},
            "ML Engineer": {"score": score(["Machine Learning", "Deep Learning", "Data Science", "Python"], 0), "reason": "Based on ML frameworks and data projects"},
            "Data Scientist": {"score": score(["Data Science", "Python", "Machine Learning", "SQL"], 0), "reason": "Based on data analysis and ML skills"},
            "Software Engineer": {"score": score(["Python", "JavaScript", "Git", "API Development"], len(non_fork)), "reason": "Based on general software engineering skills"},
            "Research Engineer": {"score": score(["Machine Learning", "Deep Learning", "NLP", "Computer Vision"], 0), "reason": "Based on research-level ML skills"},
        }

    def _rank_repos(self, repos: list[dict], analyses: list[dict]) -> dict:
        """Rank repos across multiple categories"""
        if not repos:
            return {}

        sorted_by_stars = sorted(repos, key=lambda r: r.get("stars", 0), reverse=True)
        sorted_by_complexity = sorted(zip(repos, analyses), key=lambda x: x[1].get("complexity", 0), reverse=True)
        sorted_by_doc = sorted(zip(repos, analyses), key=lambda x: x[1].get("documentation_score", 0), reverse=True)

        def repo_card(r, a=None):
            return {"name": r["name"], "url": r.get("url", ""), "description": r.get("description", ""), "stars": r.get("stars", 0), "language": r.get("language", ""), "analysis": a}

        return {
            "most_popular": [repo_card(r) for r in sorted_by_stars[:3]],
            "most_complex": [repo_card(r, a) for r, a in sorted_by_complexity[:3]],
            "best_documented": [repo_card(r, a) for r, a in sorted_by_doc[:3]],
            "most_original": [repo_card(r, a) for r, a in sorted(zip(repos, analyses), key=lambda x: x[1].get("originality", 0), reverse=True)[:3]],
            "best_overall": [repo_card(r, a) for r, a in sorted(zip(repos, analyses), key=lambda x: (x[1].get("complexity", 0) + x[1].get("code_quality", 0) + x[0].get("stars", 0) * 2), reverse=True)[:3]],
        }

    def _build_timeline(self, repos: list[dict]) -> list[dict]:
        """Build developer growth timeline"""
        events = []
        for r in repos:
            if r.get("created_at"):
                events.append({
                    "date": r["created_at"][:10],
                    "event": f"Created {r['name']}",
                    "language": r.get("language", ""),
                    "stars": r.get("stars", 0),
                    "type": "repo"
                })
        return sorted(events, key=lambda x: x["date"])

    def _generate_career_roadmap(self, skills: dict) -> dict:
        """Generate career roadmap based on current skills"""
        top_skills = list(skills.keys())[:5]
        is_ml = any(s in top_skills for s in ["Machine Learning", "Deep Learning", "LLMs"])
        is_backend = any(s in top_skills for s in ["FastAPI", "Django", "Flask", "Python"])

        if is_ml:
            focus = "AI/ML Engineer"
            next_steps = ["Learn MLOps (MLflow, DVC)", "Study System Design for ML", "Contribute to Hugging Face", "Build an end-to-end ML product"]
            resources = [
                {"type": "Course", "title": "Fast.ai Practical Deep Learning", "url": "https://fast.ai"},
                {"type": "Book", "title": "Designing Machine Learning Systems - Chip Huyen"},
                {"type": "Project", "title": "Build a RAG chatbot with LangChain + local LLM"},
                {"type": "Certification", "title": "AWS Certified ML Specialty or Google Professional ML Engineer"},
            ]
        elif is_backend:
            focus = "Backend/Software Engineer"
            next_steps = ["Learn System Design", "Master Docker & Kubernetes", "Study DSA & LeetCode", "Build a production API with auth"]
            resources = [
                {"type": "Course", "title": "System Design Interview - Alex Xu"},
                {"type": "Book", "title": "Clean Architecture - Robert C. Martin"},
                {"type": "Project", "title": "Build a full-stack SaaS product"},
                {"type": "Certification", "title": "AWS Certified Developer Associate"},
            ]
        else:
            focus = "Full-Stack Developer"
            next_steps = ["Pick a specialization (AI or Backend)", "Learn TypeScript deeply", "Build a real product and deploy it", "Contribute to open source"]
            resources = [
                {"type": "Course", "title": "The Odin Project (Full-Stack)"},
                {"type": "Book", "title": "The Pragmatic Programmer"},
                {"type": "Project", "title": "Build and deploy a full-stack app"},
                {"type": "Open Source", "title": "Find a beginner-friendly repo on GitHub and contribute"},
            ]

        return {
            "recommended_focus": focus,
            "next_steps": next_steps,
            "resources": resources,
            "timeline_months": {
                "0-3": "Strengthen fundamentals and build 1-2 solid projects",
                "3-6": "Start applying for internships, contribute to open source",
                "6-12": "Land internship, learn from real projects, expand tech stack",
                "12+": "Target full-time roles, specialize deeper",
            }
        }

    async def _generate_ai_summary(self, profile: dict, repos: list[dict], skills: dict, internship: dict) -> str:
        top_skills = list(skills.keys())[:6]
        best_role = max(internship.items(), key=lambda x: x[1]["score"])[0]
        prompt = f"""Write a professional developer profile summary for {profile.get('name', profile['username'])}.

Bio: {profile.get('bio', 'No bio')}
Top Skills: {', '.join(top_skills)}
Repos: {len(repos)}
Best internship fit: {best_role} ({internship[best_role]['score']}/100)

Write 3 paragraphs:
1. Who they are as a developer
2. Their technical strengths
3. Career trajectory and potential

Keep it professional, motivating, and honest. Max 200 words."""
        return await self._ask_ollama(prompt, 300)

    def _rule_based_summary(self, profile: dict, skills: dict, internship: dict) -> str:
        name = profile.get("name") or profile.get("username")
        top = list(skills.keys())[:4]
        best_role = max(internship.items(), key=lambda x: x[1]["score"])
        score = best_role[1]["score"]
        return f"""{name} is a developer with demonstrated skills in {', '.join(top)}. Their GitHub profile shows active project development across multiple domains.

Their strongest technical areas are {', '.join(top[:2])}, with growing expertise in {', '.join(top[2:4]) if len(top) > 2 else 'other technologies'}.

Based on their project portfolio, they are best suited for a {best_role[0]} role with a readiness score of {score}/100. Continued focus on building real-world projects and deepening their core skills will accelerate their career growth."""

    async def generate_readme(self, repo: dict, analysis: dict) -> str:
        """Generate a professional README for a repository"""
        use_ai = await self._check_ollama()
        if use_ai:
            prompt = f"""Generate a professional GitHub README.md for this project:

Name: {repo['name']}
Description: {repo.get('description', '')}
Language: {repo.get('language', '')}
Purpose: {analysis.get('purpose', '')}
Architecture: {analysis.get('architecture', '')}
Tech tags: {', '.join(analysis.get('tech_tags', []))}

Include: Title, badges, description, features, installation, usage, contributing, license.
Use proper Markdown. Make it look professional."""
            result = await self._ask_ollama(prompt, 600)
            if result:
                return result

        # Fallback
        name = repo['name']
        lang = repo.get('language', 'Python')
        desc = repo.get('description') or analysis.get('purpose', 'A software project')
        tags = " ".join(f"`{t}`" for t in analysis.get('tech_tags', [lang]))
        return f"""# {name}

> {desc}

![Language]( https://img.shields.io/badge/language-{lang}-blue)

## Tech Stack
{tags}

## Features
- {analysis.get('purpose', 'Core functionality')}
- Clean and maintainable code
- Well-structured architecture

## Installation
```bash
git clone https://github.com/username/{name}.git
cd {name}
pip install -r requirements.txt
```

## Usage
```bash
python main.py
```

## License
MIT License
"""
