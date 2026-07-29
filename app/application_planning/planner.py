"""`ApplicationPlanner`: scores a job and decides whether to apply.

Composes `JobMatchScorer` (scoring) and `DecisionEngine` (decision +
priority) — deliberately the *only* thing this class does. Resume/cover
letter generation is `package_builder.py`'s job, kept separate so a caller
can cheaply evaluate hundreds of discovered jobs without generating
documents for the ones it's going to skip.
"""

from app.application_planning.decision import DecisionEngine
from app.application_planning.models import EvaluatedJob
from app.application_planning.scorer import JobMatchScorer
from app.career_profile.models import CareerProfile
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob, JobSearchPreferences


class ApplicationPlanner:
    def __init__(
        self,
        scorer: JobMatchScorer | None = None,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self._scorer = scorer or JobMatchScorer()
        self._decision_engine = decision_engine or DecisionEngine()

    def evaluate_job(
        self,
        job: DiscoveredJob,
        profile: CareerProfile,
        blueprint: ResumeBlueprint | None = None,
        *,
        preferences: JobSearchPreferences | None = None,
    ) -> EvaluatedJob:
        evaluation = self._scorer.evaluate(job, profile, blueprint, preferences=preferences)
        decision, priority, reasons = self._decision_engine.decide(evaluation)
        return EvaluatedJob(
            job=job, evaluation=evaluation, decision=decision, priority=priority, reasons=reasons
        )
