"""Adapters wrapping existing Sprint 3-7 services as `GraphNode`s.

Every adapter here only calls its wrapped service's existing public
methods — none of Sprint 3, 3.5, 5, 6, or 7's business logic is modified.
Each adapter's wrapped service instance is supplied at construction time
(these services need live dependencies — an `AsyncSession`, an
`LLMService` — the graph engine has no opinion about how those are built),
and each adapter resolves its arguments from graph inputs or upstream node
outputs via `resolve_input()` (`_common.py`).
"""

from app.graph.adapters.career_profile import CareerProfileNode
from app.graph.adapters.cover_letter_generator import CoverLetterGeneratorNode
from app.graph.adapters.job_discovery import JobDiscoveryNode
from app.graph.adapters.resume_generator import ResumeGeneratorNode
from app.graph.adapters.resume_intelligence import ResumeIntelligenceNode

__all__ = [
    "CareerProfileNode",
    "CoverLetterGeneratorNode",
    "JobDiscoveryNode",
    "ResumeGeneratorNode",
    "ResumeIntelligenceNode",
]
