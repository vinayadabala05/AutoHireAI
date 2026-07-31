"""Adapters wrapping existing Sprint 3-10 services as `GraphNode`s.

Every adapter here only calls its wrapped service's existing public
methods — none of Sprint 3, 3.5, 5, 6, 7, 9, or 10's business logic is
modified. Each adapter's wrapped service instance is supplied at
construction time (these services need live dependencies — an
`AsyncSession`, an `LLMService`, a Playwright `Page` — the graph engine
has no opinion about how those are built), and each adapter resolves its
arguments from graph inputs or upstream node outputs via `resolve_input()`
(`_common.py`).

`application_planning.py`/`browser_automation.py` (Sprint 11's dispatcher)
are deliberately **not** re-exported here, unlike the five below: they
depend on `app.application_planning`/`app.browser_automation`, both of
which depend back on *this* package's `resume_generator`/
`cover_letter_generator` modules — eagerly importing them at package-init
time would create an import cycle the moment anything imports this
package. Import them directly from their own submodules instead:
`from app.graph.adapters.application_planning import ApplicationPlanningNode`.
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
