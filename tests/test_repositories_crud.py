"""CRUD tests for the repository layer.

Exercises a representative slice of the 19 models rather than every single
one 1:1 — `BaseRepository` is shared code, so these tests validate its
generic get/list/create/update/delete behavior (including the soft-delete
vs. hard-delete branching) plus a few entity-specific repository methods.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApplicationEventType, ApplicationStatus, JobSource
from app.repositories.application import ApplicationEventRepository, ApplicationRepository
from app.repositories.company import CompanyRepository
from app.repositories.job import JobRepository
from app.repositories.resume import ResumeRepository, ResumeVersionRepository
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    user = await repo.create(email="jane@example.com", full_name="Jane Doe")
    await db_session.commit()
    assert user.id is not None
    assert user.is_active is True

    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.email == "jane@example.com"

    by_email = await repo.get_by_email("jane@example.com")
    assert by_email is not None
    assert by_email.id == user.id

    updated = await repo.update(fetched, full_name="Jane R. Doe")
    await db_session.commit()
    assert updated.full_name == "Jane R. Doe"

    await repo.delete(updated)
    await db_session.commit()

    assert await repo.get(user.id) is None
    assert (await repo.get(user.id, include_deleted=True)) is not None


@pytest.mark.asyncio
async def test_company_and_job_repository(db_session: AsyncSession) -> None:
    company_repo = CompanyRepository(db_session)
    job_repo = JobRepository(db_session)

    company = await company_repo.create(name="Acme Corp")
    await db_session.commit()

    job = await job_repo.create(
        company_id=company.id,
        title="Backend Engineer",
        source=JobSource.LINKEDIN,
        external_id="linkedin-123",
    )
    await db_session.commit()

    found = await job_repo.get_by_source_external_id(JobSource.LINKEDIN, "linkedin-123")
    assert found is not None
    assert found.id == job.id

    jobs_for_company = await job_repo.list_by_company(company.id)
    assert [j.id for j in jobs_for_company] == [job.id]

    same_company = await company_repo.get_by_name("Acme Corp")
    assert same_company is not None
    assert same_company.id == company.id


@pytest.mark.asyncio
async def test_application_event_hard_delete_vs_application_soft_delete(
    db_session: AsyncSession,
) -> None:
    user_repo = UserRepository(db_session)
    company_repo = CompanyRepository(db_session)
    job_repo = JobRepository(db_session)
    application_repo = ApplicationRepository(db_session)
    event_repo = ApplicationEventRepository(db_session)

    user = await user_repo.create(email="applicant@example.com", full_name="Applicant One")
    company = await company_repo.create(name="Initech")
    job = await job_repo.create(company_id=company.id, title="SRE")
    await db_session.commit()

    application = await application_repo.create(
        user_id=user.id, job_id=job.id, applied_at=datetime.now(UTC)
    )
    await db_session.commit()

    event = await event_repo.create(
        application_id=application.id,
        event_type=ApplicationEventType.STATUS_CHANGE,
        from_status=ApplicationStatus.APPLIED,
        to_status=ApplicationStatus.INTERVIEW,
        occurred_at=datetime.now(UTC),
    )
    await db_session.commit()

    events = await event_repo.list_by_application(application.id)
    assert len(events) == 1
    assert events[0].id == event.id

    # Application supports soft delete (SoftDeleteMixin) ...
    await application_repo.delete(application)
    await db_session.commit()
    assert await application_repo.get(application.id) is None
    assert (await application_repo.get(application.id, include_deleted=True)) is not None

    # ... but ApplicationEvent is an append-only audit trail with no
    # deleted_at column, so BaseRepository.delete() falls back to a real DELETE.
    await event_repo.delete(event)
    await db_session.commit()
    assert await event_repo.get(event.id) is None
    assert await event_repo.get(event.id, include_deleted=True) is None


@pytest.mark.asyncio
async def test_resume_version_next_version_number(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)

    user = await user_repo.create(email="candidate@example.com", full_name="Candidate")
    await db_session.commit()

    resume = await resume_repo.create(user_id=user.id, title="Backend track")
    await db_session.commit()

    assert await version_repo.next_version_number(resume.id) == 1

    v1 = await version_repo.create(
        resume_id=resume.id,
        version_number=await version_repo.next_version_number(resume.id),
        role="Backend Engineer",
        generated_at=datetime.now(UTC),
    )
    await db_session.commit()
    assert v1.version_number == 1

    next_number = await version_repo.next_version_number(resume.id)
    assert next_number == 2

    v2 = await version_repo.create(
        resume_id=resume.id,
        version_number=next_number,
        role="Senior Backend Engineer",
        generated_at=datetime.now(UTC),
    )
    await db_session.commit()

    versions = await version_repo.list_by_resume(resume.id)
    assert [v.id for v in versions] == [v2.id, v1.id]  # newest first
