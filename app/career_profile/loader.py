"""Loads every raw database row a `CareerProfile` is built from.

The only module in this package that touches the database — `builder.py`
takes the plain `RawProfileData` bundle this produces and is otherwise pure,
so it's testable with hand-built in-memory ORM instances and no database at
all. Uses the existing Sprint 2 repositories exclusively; no new queries or
repository methods were added.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.profile import Certificate, Education, Experience, GithubRepository, Project, Skill
from app.models.resume import Resume
from app.models.user import User
from app.repositories.application import ApplicationRepository
from app.repositories.interview import InterviewRepository
from app.repositories.job import JobRepository
from app.repositories.profile import (
    CertificateRepository,
    EducationRepository,
    ExperienceRepository,
    GithubRepositoryRepository,
    ProjectRepository,
    SkillRepository,
)
from app.repositories.resume import ResumeRepository, ResumeVersionRepository
from app.repositories.user import UserRepository


@dataclass
class RawProfileData:
    """Plain container for everything loaded from the database.

    Deliberately not a Pydantic model — it holds live SQLAlchemy ORM
    instances, not serializable data; `builder.py` is what turns this into
    the serializable `CareerProfile`.
    """

    user: User
    educations: list[Education] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    certificates: list[Certificate] = field(default_factory=list)
    github_repositories: list[GithubRepository] = field(default_factory=list)
    resumes: list[Resume] = field(default_factory=list)
    total_resume_versions: int = 0
    applications: list[Application] = field(default_factory=list)
    jobs_by_id: dict[uuid.UUID, Job] = field(default_factory=dict)
    interviews: list[Interview] = field(default_factory=list)


class ProfileDataLoader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, user_id: uuid.UUID) -> RawProfileData:
        user = await UserRepository(self._session).get(user_id)
        if user is None:
            raise ValueError(f"No user found for id {user_id}")

        resumes = await ResumeRepository(self._session).list_by_user(user_id)
        total_resume_versions = 0
        version_repo = ResumeVersionRepository(self._session)
        for resume in resumes:
            total_resume_versions += len(await version_repo.list_by_resume(resume.id))

        applications = await ApplicationRepository(self._session).list_by_user(user_id)
        job_repo = JobRepository(self._session)
        interview_repo = InterviewRepository(self._session)
        jobs_by_id: dict[uuid.UUID, Job] = {}
        interviews: list[Interview] = []
        for application in applications:
            if application.job_id not in jobs_by_id:
                job = await job_repo.get(application.job_id, include_deleted=True)
                if job is not None:
                    jobs_by_id[application.job_id] = job
            interviews.extend(await interview_repo.list_by_application(application.id))

        return RawProfileData(
            user=user,
            educations=await EducationRepository(self._session).list_by_user(user_id),
            experiences=await ExperienceRepository(self._session).list_by_user(user_id),
            projects=await ProjectRepository(self._session).list_by_user(user_id),
            skills=await SkillRepository(self._session).list_by_user(user_id),
            certificates=await CertificateRepository(self._session).list_by_user(user_id),
            github_repositories=await GithubRepositoryRepository(self._session).list_by_user(
                user_id
            ),
            resumes=resumes,
            total_resume_versions=total_resume_versions,
            applications=applications,
            jobs_by_id=jobs_by_id,
            interviews=interviews,
        )
