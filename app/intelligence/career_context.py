"""Builds a `CareerContext` from the Sprint 2 database models.

The only module in this package that touches the database — every other
component in `app/intelligence/` takes plain value objects, so it's
testable without a database at all. No hardcoded resume content: every
field here is read from the user's actual profile rows via the Sprint 2
repositories.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.models import (
    CareerContext,
    CertificateInput,
    ExperienceInput,
    ProjectInput,
    SkillInput,
)
from app.models.profile import Experience, Project
from app.repositories.profile import (
    CertificateRepository,
    ExperienceRepository,
    ProjectRepository,
    SkillRepository,
)
from app.repositories.user import UserRepository

_DAYS_PER_YEAR = 365.25


class CareerContextBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build(self, user_id: uuid.UUID) -> CareerContext:
        user = await UserRepository(self._session).get(user_id)
        if user is None:
            raise ValueError(f"No user found for id {user_id}")

        skills = await SkillRepository(self._session).list_by_user(user_id)
        projects = await ProjectRepository(self._session).list_by_user(user_id)
        experiences = await ExperienceRepository(self._session).list_by_user(user_id)
        certificates = await CertificateRepository(self._session).list_by_user(user_id)

        return CareerContext(
            user_id=user.id,
            full_name=user.full_name,
            skills=[SkillInput(name=s.name, years_experience=s.years_experience) for s in skills],
            projects=[self._to_project_input(p) for p in projects],
            experiences=[self._to_experience_input(e) for e in experiences],
            certificates=[CertificateInput(name=c.name) for c in certificates],
        )

    def _to_project_input(self, project: Project) -> ProjectInput:
        return ProjectInput(
            id=project.id,
            name=project.name,
            description=project.description or "",
            technologies=list(project.technologies or []),
            achievements=list(project.achievements or []),
            priority=project.priority.value,
            is_ongoing=project.end_date is None,
        )

    def _to_experience_input(self, experience: Experience) -> ExperienceInput:
        years_ago_ended = 0.0
        if not experience.is_current and experience.end_date is not None:
            years_ago_ended = max(0.0, (date.today() - experience.end_date).days / _DAYS_PER_YEAR)

        return ExperienceInput(
            id=experience.id,
            title=experience.title,
            company_name=experience.company_name,
            description=experience.description or "",
            technologies=list(experience.technologies or []),
            achievements=list(experience.achievements or []),
            is_current=experience.is_current,
            years_ago_ended=years_ago_ended,
        )
