"""The one intelligence test that touches a real database — everything
else in this package is pure-Python and needs no DB at all.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.career_context import CareerContextBuilder
from app.models.enums import ProjectPriority
from app.models.profile import Experience, Project, Skill
from app.models.user import User


@pytest.mark.asyncio
async def test_builds_career_context_from_database_rows(db_session: AsyncSession) -> None:
    user = User(email="context@example.com", full_name="Context User")
    db_session.add(user)
    await db_session.flush()

    db_session.add(Skill(user_id=user.id, name="Python", years_experience=4))
    db_session.add(
        Project(
            user_id=user.id,
            name="Market Data Platform",
            description="Built with FastAPI and PostgreSQL.",
            technologies=["FastAPI", "PostgreSQL"],
            priority=ProjectPriority.FEATURED,
            end_date=None,
        )
    )
    db_session.add(
        Experience(
            user_id=user.id,
            company_name="Acme Corp",
            title="Backend Engineer",
            start_date=date(2022, 1, 1),
            end_date=None,
            is_current=True,
            technologies=["Python", "FastAPI"],
        )
    )
    await db_session.commit()

    context = await CareerContextBuilder(db_session).build(user.id)

    assert context.full_name == "Context User"
    assert [s.name for s in context.skills] == ["Python"]
    assert context.projects[0].name == "Market Data Platform"
    assert context.projects[0].priority == "featured"
    assert context.projects[0].is_ongoing is True
    assert context.experiences[0].is_current is True
    assert context.experiences[0].years_ago_ended == 0.0


@pytest.mark.asyncio
async def test_raises_for_unknown_user(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="No user found"):
        await CareerContextBuilder(db_session).build(uuid.uuid4())
