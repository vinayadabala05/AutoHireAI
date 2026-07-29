"""Deterministic skill matching: exact / related / missing, with a weighted score.

No embeddings — "related" comes from a curated alias table plus a fuzzy
string-similarity fallback (for near-spellings like "Postgres" vs.
"PostgreSQL"). See docs/resume_intelligence.md for the exact scoring formula.
"""

import difflib

from app.intelligence.models import MissingSkill, SkillInput, SkillMatch

# skill (normalized) -> other normalized skills considered "related" to it.
# Deliberately curated and small — this is a heuristic stand-in for the
# embedding-based similarity an LLM integration will provide later.
_RELATED_SKILLS: dict[str, set[str]] = {
    "python": {"django", "flask", "fastapi", "pandas", "numpy"},
    "django": {"python", "flask", "fastapi"},
    "flask": {"python", "django", "fastapi"},
    "fastapi": {"python", "django", "flask"},
    "javascript": {"typescript", "node.js", "node", "react", "vue", "angular"},
    "typescript": {"javascript", "node.js", "node", "react", "angular"},
    "react": {"javascript", "typescript", "next.js", "redux"},
    "docker": {"kubernetes", "containerization", "k8s"},
    "kubernetes": {"docker", "helm", "k8s"},
    "aws": {"cloud", "azure", "gcp", "ec2", "s3", "lambda"},
    "azure": {"cloud", "aws", "gcp"},
    "gcp": {"cloud", "aws", "azure", "google cloud"},
    "postgresql": {"postgres", "sql", "mysql", "database"},
    "mysql": {"postgresql", "sql", "database"},
    "sql": {"postgresql", "mysql", "database"},
    "machine learning": {"deep learning", "pytorch", "tensorflow", "scikit-learn", "data science"},
    "deep learning": {"machine learning", "pytorch", "tensorflow", "neural network"},
    "tensorflow": {"pytorch", "machine learning", "deep learning", "keras"},
    "pytorch": {"tensorflow", "machine learning", "deep learning"},
    "ci/cd": {"jenkins", "github actions", "gitlab ci", "circleci"},
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


class SkillMatcher:
    fuzzy_threshold: float = 0.85

    def match(
        self,
        user_skills: list[SkillInput],
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> SkillMatch:
        user_norms = {_normalize(skill.name) for skill in user_skills}

        exact_matches: list[str] = []
        related_matches: list[str] = []
        missing: list[MissingSkill] = []

        required_score = self._score_group(
            required_skills, user_norms, exact_matches, related_matches, missing, "required"
        )
        preferred_score: float | None = None
        if preferred_skills:
            preferred_score = self._score_group(
                preferred_skills, user_norms, exact_matches, related_matches, missing, "preferred"
            )

        total_job_skills = len({_normalize(s) for s in [*required_skills, *preferred_skills]})
        coverage = 0.0
        if total_job_skills:
            coverage = (len(exact_matches) + 0.5 * len(related_matches)) / total_job_skills * 100

        weighted = (
            required_score
            if preferred_score is None
            else required_score * 0.7 + preferred_score * 0.3
        )

        return SkillMatch(
            exact_matches=exact_matches,
            related_matches=related_matches,
            missing_skills=missing,
            coverage_percentage=round(coverage, 1),
            weighted_score=round(weighted, 1),
        )

    def _score_group(
        self,
        job_skills: list[str],
        user_norms: set[str],
        exact_out: list[str],
        related_out: list[str],
        missing_out: list[MissingSkill],
        importance: str,
    ) -> float:
        if not job_skills:
            return 0.0

        exact_count = 0
        related_count = 0
        for skill in job_skills:
            norm = _normalize(skill)
            if norm in user_norms:
                exact_count += 1
                if skill not in exact_out:
                    exact_out.append(skill)
            elif self._is_related(norm, user_norms):
                related_count += 1
                if skill not in related_out:
                    related_out.append(skill)
            else:
                missing_out.append(MissingSkill(name=skill, importance=importance))

        return (exact_count + 0.5 * related_count) / len(job_skills) * 100

    def _is_related(self, job_skill_norm: str, user_norms: set[str]) -> bool:
        related_set = _RELATED_SKILLS.get(job_skill_norm, set())
        for user_norm in user_norms:
            if user_norm in related_set or job_skill_norm in _RELATED_SKILLS.get(user_norm, set()):
                return True
            if (
                difflib.SequenceMatcher(None, job_skill_norm, user_norm).ratio()
                >= self.fuzzy_threshold
            ):
                return True
        return False
