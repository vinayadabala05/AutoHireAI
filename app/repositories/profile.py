"""Repositories for the user-profile building blocks (see `app/models/profile.py`)."""

import uuid

from sqlalchemy import select

from app.models.profile import Certificate, Education, Experience, GithubRepository, Project, Skill
from app.repositories.base import BaseRepository


class EducationRepository(BaseRepository[Education]):
    model = Education

    async def list_by_user(self, user_id: uuid.UUID) -> list[Education]:
        stmt = self._apply_not_deleted(
            select(Education).where(Education.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExperienceRepository(BaseRepository[Experience]):
    model = Experience

    async def list_by_user(self, user_id: uuid.UUID) -> list[Experience]:
        stmt = self._apply_not_deleted(
            select(Experience).where(Experience.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_by_user(self, user_id: uuid.UUID) -> list[Project]:
        stmt = self._apply_not_deleted(
            select(Project).where(Project.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class SkillRepository(BaseRepository[Skill]):
    model = Skill

    async def list_by_user(self, user_id: uuid.UUID) -> list[Skill]:
        stmt = self._apply_not_deleted(
            select(Skill).where(Skill.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class CertificateRepository(BaseRepository[Certificate]):
    model = Certificate

    async def list_by_user(self, user_id: uuid.UUID) -> list[Certificate]:
        stmt = self._apply_not_deleted(
            select(Certificate).where(Certificate.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GithubRepositoryRepository(BaseRepository[GithubRepository]):
    model = GithubRepository

    async def list_by_user(self, user_id: uuid.UUID) -> list[GithubRepository]:
        stmt = self._apply_not_deleted(
            select(GithubRepository).where(GithubRepository.user_id == user_id),
            include_deleted=False,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
