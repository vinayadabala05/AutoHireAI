"""Relationship, constraint, and soft-delete behavior tests.

These exercise the ORM mapping directly (not through repositories) to
verify cascades, uniqueness constraints, and the shared `application_status`
Postgres ENUM actually work the way the model docstrings claim.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationEvent
from app.models.company import Company
from app.models.cover_letter import CoverLetter
from app.models.enums import ApplicationEventType, ApplicationStatus
from app.models.job import Job
from app.models.profile import Education, Skill
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


async def _make_user(session: AsyncSession, email: str = "user@example.com") -> User:
    user = User(email=email, full_name="Test User")
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_user_education_relationship_and_cascade_delete(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(
        Education(
            user_id=user.id,
            institution="MIT",
            degree="BSc Computer Science",
            start_date=date(2018, 9, 1),
        )
    )
    await db_session.commit()

    stmt = select(User).where(User.id == user.id).options(selectinload(User.educations))
    reloaded = (await db_session.execute(stmt)).scalar_one()
    assert len(reloaded.educations) == 1
    assert reloaded.educations[0].user_id == user.id

    # Deleting the user hard-deletes it (session.delete bypasses the
    # soft-delete repository layer on purpose here) and the ORM-level
    # cascade="all, delete-orphan" must take the Education row with it.
    await db_session.delete(reloaded)
    await db_session.commit()

    remaining = await db_session.execute(select(Education).where(Education.user_id == user.id))
    assert remaining.scalars().all() == []


@pytest.mark.asyncio
async def test_skill_unique_constraint_per_user(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Skill(user_id=user.id, name="Python"))
    await db_session.commit()

    db_session.add(Skill(user_id=user.id, name="Python"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_application_unique_user_job_constraint(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    company = Company(name="Acme")
    db_session.add(company)
    await db_session.flush()
    job = Job(company_id=company.id, title="Engineer")
    db_session.add(job)
    await db_session.flush()

    db_session.add(Application(user_id=user.id, job_id=job.id, applied_at=datetime.now(UTC)))
    await db_session.commit()

    db_session.add(Application(user_id=user.id, job_id=job.id, applied_at=datetime.now(UTC)))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_cover_letter_is_one_to_one_with_application(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    company = Company(name="Globex")
    db_session.add(company)
    await db_session.flush()
    job = Job(company_id=company.id, title="Engineer")
    db_session.add(job)
    await db_session.flush()
    application = Application(user_id=user.id, job_id=job.id, applied_at=datetime.now(UTC))
    db_session.add(application)
    await db_session.flush()

    cover_letter = CoverLetter(
        user_id=user.id,
        application_id=application.id,
        title="Cover letter",
        content="Dear hiring manager...",
        generated_at=datetime.now(UTC),
    )
    db_session.add(cover_letter)
    await db_session.commit()

    stmt = (
        select(Application)
        .where(Application.id == application.id)
        .options(selectinload(Application.cover_letter))
    )
    reloaded = (await db_session.execute(stmt)).scalar_one()
    assert reloaded.cover_letter is not None
    assert reloaded.cover_letter.id == cover_letter.id

    # A second cover letter for the same application violates the
    # one-to-one unique constraint on `application_id`.
    db_session.add(
        CoverLetter(
            user_id=user.id,
            application_id=application.id,
            title="Duplicate",
            content="...",
            generated_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_resume_version_unique_constraint_and_ordering(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    resume = Resume(user_id=user.id, title="Main resume")
    db_session.add(resume)
    await db_session.flush()

    db_session.add(
        ResumeVersion(
            resume_id=resume.id, version_number=1, role="Engineer", generated_at=datetime.now(UTC)
        )
    )
    await db_session.commit()

    db_session.add(
        ResumeVersion(
            resume_id=resume.id,
            version_number=1,
            role="Engineer v2",
            generated_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_soft_delete_mixin_is_deleted_property(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    skill = Skill(user_id=user.id, name="Rust")
    db_session.add(skill)
    await db_session.commit()

    assert skill.is_deleted is False

    skill.deleted_at = datetime.now(UTC)
    await db_session.commit()

    assert skill.is_deleted is True


@pytest.mark.asyncio
async def test_application_status_enum_shared_across_tables(db_session: AsyncSession) -> None:
    """`application_status` is declared once and reused by both
    `Application.status` and `ApplicationEvent.from_status/to_status` — this
    confirms both columns round-trip the same Python enum through Postgres.
    """
    user = await _make_user(db_session)
    company = Company(name="Umbrella")
    db_session.add(company)
    await db_session.flush()
    job = Job(company_id=company.id, title="Researcher")
    db_session.add(job)
    await db_session.flush()

    application = Application(
        user_id=user.id,
        job_id=job.id,
        applied_at=datetime.now(UTC),
        status=ApplicationStatus.INTERVIEW,
    )
    db_session.add(application)
    await db_session.flush()

    event = ApplicationEvent(
        application_id=application.id,
        event_type=ApplicationEventType.STATUS_CHANGE,
        from_status=ApplicationStatus.APPLIED,
        to_status=ApplicationStatus.INTERVIEW,
        occurred_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.commit()

    reloaded_app = await db_session.get(Application, application.id)
    assert reloaded_app is not None
    assert reloaded_app.status is ApplicationStatus.INTERVIEW

    reloaded_event = await db_session.get(ApplicationEvent, event.id)
    assert reloaded_event is not None
    assert reloaded_event.from_status is ApplicationStatus.APPLIED
    assert reloaded_event.to_status is ApplicationStatus.INTERVIEW
