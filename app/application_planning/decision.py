"""Decision logic: APPLY vs. SKIP, and application priority.

Deterministic, threshold-based — no ML model, consistent with every other
"scoring" module in this codebase (`app.intelligence.skill_matcher`,
`app.job_discovery.ranking`) being a transparent, explainable heuristic
rather than a black box. Every decision returns a list of human-readable
`reasons` so a caller (or a future review UI) can see exactly why a job
was skipped or prioritized the way it was.
"""

from loguru import logger
from pydantic import BaseModel, Field

from app.application_planning.models import (
    ApplicationDecision,
    ApplicationPriority,
    MatchEvaluation,
)


class DecisionThresholds(BaseModel):
    """Configurable cutoffs driving `DecisionEngine`."""

    apply_score_threshold: float = Field(default=50.0, ge=0.0, le=100.0)
    high_priority_threshold: float = Field(default=80.0, ge=0.0, le=100.0)
    medium_priority_threshold: float = Field(default=60.0, ge=0.0, le=100.0)
    max_missing_required_skills: int = Field(default=3, ge=0)


class DecisionEngine:
    def __init__(self, thresholds: DecisionThresholds | None = None) -> None:
        self.thresholds = thresholds or DecisionThresholds()

    def decide(
        self, evaluation: MatchEvaluation
    ) -> tuple[ApplicationDecision, ApplicationPriority, list[str]]:
        reasons: list[str] = []
        missing_required = evaluation.missing_required_skills

        if evaluation.match_score < self.thresholds.apply_score_threshold:
            reasons.append(
                f"Match score {evaluation.match_score:.1f} is below the apply threshold of "
                f"{self.thresholds.apply_score_threshold:.1f}."
            )
            return self._finalize(ApplicationDecision.SKIP, ApplicationPriority.LOW, reasons)

        if len(missing_required) > self.thresholds.max_missing_required_skills:
            reasons.append(
                f"{len(missing_required)} required skill(s) missing exceeds the maximum of "
                f"{self.thresholds.max_missing_required_skills}."
            )
            return self._finalize(ApplicationDecision.SKIP, ApplicationPriority.LOW, reasons)

        reasons.append(
            f"Match score {evaluation.match_score:.1f} meets the apply threshold of "
            f"{self.thresholds.apply_score_threshold:.1f}."
        )
        if missing_required:
            reasons.append(
                f"{len(missing_required)} required skill(s) missing, within the acceptable "
                f"maximum of {self.thresholds.max_missing_required_skills}."
            )
        else:
            reasons.append("No required skills are missing.")

        if evaluation.match_score >= self.thresholds.high_priority_threshold:
            priority = ApplicationPriority.HIGH
        elif evaluation.match_score >= self.thresholds.medium_priority_threshold:
            priority = ApplicationPriority.MEDIUM
        else:
            priority = ApplicationPriority.LOW
        reasons.append(f"Assigned {priority.value} priority based on match score.")

        return self._finalize(ApplicationDecision.APPLY, priority, reasons)

    def _finalize(
        self, decision: ApplicationDecision, priority: ApplicationPriority, reasons: list[str]
    ) -> tuple[ApplicationDecision, ApplicationPriority, list[str]]:
        logger.info(
            "Decision: {} (priority={}) — {}", decision.value, priority.value, "; ".join(reasons)
        )
        return decision, priority, reasons
