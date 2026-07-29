"""Combines job analysis, skill matching, project/experience ranking, and
section optimization into a single `ResumeBlueprint` — no LLM involved.
"""

from app.intelligence.experience_ranker import ExperienceRanker
from app.intelligence.job_analyzer import JobAnalyzer
from app.intelligence.models import (
    CareerContext,
    ExperienceRanking,
    JobPostingInput,
    ProjectRanking,
    ResumeBlueprint,
    SectionPlan,
    SkillMatch,
)
from app.intelligence.project_ranker import ProjectRanker
from app.intelligence.section_optimizer import SectionOptimizer
from app.intelligence.skill_matcher import SkillMatcher

_TOP_PROJECTS = 5
_TOP_N_FOR_SCORE = 3
_SKILL_WEIGHT = 0.5
_PROJECT_WEIGHT = 0.25
_EXPERIENCE_WEIGHT = 0.25
_MAX_MISSING_IN_REASON = 5


class ResumePlanner:
    def __init__(
        self,
        job_analyzer: JobAnalyzer | None = None,
        skill_matcher: SkillMatcher | None = None,
        project_ranker: ProjectRanker | None = None,
        experience_ranker: ExperienceRanker | None = None,
        section_optimizer: SectionOptimizer | None = None,
    ) -> None:
        self._job_analyzer = job_analyzer or JobAnalyzer()
        self._skill_matcher = skill_matcher or SkillMatcher()
        self._project_ranker = project_ranker or ProjectRanker()
        self._experience_ranker = experience_ranker or ExperienceRanker()
        self._section_optimizer = section_optimizer or SectionOptimizer()

    def plan(self, job: JobPostingInput, context: CareerContext) -> ResumeBlueprint:
        job_analysis = self._job_analyzer.analyze(job)
        skill_match = self._skill_matcher.match(
            context.skills, job_analysis.required_skills, job_analysis.preferred_skills
        )
        project_rankings = self._project_ranker.rank(context.projects, job_analysis)
        experience_rankings = self._experience_ranker.rank(context.experiences, job_analysis)
        section_plan = self._section_optimizer.optimize(
            job_analysis, skill_match, project_rankings, experience_rankings
        )

        top_projects = [ranking for ranking in project_rankings if ranking.confidence > 0][
            :_TOP_PROJECTS
        ]
        recommended_skills = list(skill_match.exact_matches)
        recommended_skills += [
            s for s in skill_match.related_matches if s not in recommended_skills
        ]

        match_score = self._compute_match_score(skill_match, project_rankings, experience_rankings)
        reasoning = self._build_reasoning(
            skill_match, top_projects, experience_rankings, section_plan
        )

        return ResumeBlueprint(
            match_score=match_score,
            recommended_projects=top_projects,
            recommended_skills=recommended_skills,
            missing_skills=skill_match.missing_skills,
            resume_sections=section_plan.order,
            reasoning=reasoning,
        )

    def _compute_match_score(
        self,
        skill_match: SkillMatch,
        project_rankings: list[ProjectRanking],
        experience_rankings: list[ExperienceRanking],
    ) -> float:
        top_project_avg = (
            sum(r.confidence for r in project_rankings[:_TOP_N_FOR_SCORE])
            / min(_TOP_N_FOR_SCORE, len(project_rankings))
            if project_rankings
            else 0.0
        )
        top_experience_avg = (
            sum(r.score for r in experience_rankings[:_TOP_N_FOR_SCORE])
            / min(_TOP_N_FOR_SCORE, len(experience_rankings))
            if experience_rankings
            else 0.0
        )
        score = (
            skill_match.weighted_score * _SKILL_WEIGHT
            + top_project_avg * _PROJECT_WEIGHT
            + top_experience_avg * _EXPERIENCE_WEIGHT
        )
        return round(min(100.0, max(0.0, score)), 1)

    def _build_reasoning(
        self,
        skill_match: SkillMatch,
        top_projects: list[ProjectRanking],
        experience_rankings: list[ExperienceRanking],
        section_plan: SectionPlan,
    ) -> list[str]:
        reasoning = [
            f"Matched {len(skill_match.exact_matches)} skill(s) exactly and "
            f"{len(skill_match.related_matches)} via related skills "
            f"({skill_match.coverage_percentage}% coverage)."
        ]
        if skill_match.missing_skills:
            names = ", ".join(m.name for m in skill_match.missing_skills[:_MAX_MISSING_IN_REASON])
            reasoning.append(f"Missing skill(s): {names}.")
        if top_projects:
            best = top_projects[0]
            reasoning.append(
                f"Top project '{best.name}' scored {best.confidence}% relevance: "
                f"{'; '.join(best.reasons)}."
            )
        if experience_rankings:
            best_experience = experience_rankings[0]
            reasoning.append(
                f"Most relevant experience: '{best_experience.title}' at "
                f"{best_experience.company_name} ({best_experience.score}%)."
            )
        reasoning.append(section_plan.reasoning)
        return reasoning
