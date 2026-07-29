"""Master Career Profile Engine.

Aggregates everything known about a user (personal info, education,
experience, projects, skills, certificates, GitHub activity, and
application/interview history) into one `CareerProfile` — the single
source of truth every future AI feature (resume generation, cover letters,
job applications, interview prep, chat, browser automation) reads from
instead of hardcoding assumptions or querying the database directly.

See docs/career_profile.md for architecture, data flow, and the
completeness-scoring formula.
"""

from app.career_profile.builder import CareerProfileBuilder
from app.career_profile.exporter import ProfileExporter
from app.career_profile.loader import ProfileDataLoader, RawProfileData
from app.career_profile.service import CareerProfileService
from app.career_profile.validator import ProfileValidator

__all__ = [
    "CareerProfileBuilder",
    "CareerProfileService",
    "ProfileDataLoader",
    "ProfileExporter",
    "ProfileValidator",
    "RawProfileData",
]
