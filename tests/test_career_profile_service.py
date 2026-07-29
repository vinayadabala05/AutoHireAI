"""Integration tests for `CareerProfileService` — the one path that touches
a real database, exercising loader -> builder -> validator/exporter end to end.
"""

import json
import uuid
from datetime import date
from pathlib import Path

import pytest
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.career_profile.service import CareerProfileService
from app.models.enums import ProjectPriority
from app.models.profile import Education, Project, Skill
from app.models.user import User


async def _seed_user(session: AsyncSession) -> User:
    user = User(
        email="integration@example.com",
        full_name="Integration User",
        linkedin_url="https://linkedin.com/in/integration",
    )
    session.add(user)
    await session.flush()

    session.add(
        Education(
            user_id=user.id,
            institution="MIT",
            degree="BSc Computer Science",
            start_date=date(2018, 9, 1),
        )
    )
    session.add(Skill(user_id=user.id, name="Python", years_experience=5))
    session.add(
        Project(
            user_id=user.id,
            name="Market Data Platform",
            description="Built with FastAPI.",
            technologies=["FastAPI"],
            priority=ProjectPriority.FEATURED,
        )
    )
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_build_profile_reads_real_rows(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    service = CareerProfileService(db_session)

    profile = await service.build_profile(user.id)

    assert profile.user_id == user.id
    assert profile.personal_info.full_name == "Integration User"
    assert profile.education[0].institution == "MIT"
    assert profile.skills[0].name == "Python"
    assert profile.projects[0].name == "Market Data Platform"


@pytest.mark.asyncio
async def test_validate_profile_reports_missing_phone_and_github(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    service = CareerProfileService(db_session)

    report = await service.validate_profile(user.id)

    fields = {issue.field for issue in report.issues}
    assert "personal_info.phone" in fields
    assert "github_repositories" in fields
    assert report.completeness.overall_score > 0


@pytest.mark.asyncio
async def test_export_json_and_yaml_write_files(db_session: AsyncSession, tmp_path: Path) -> None:
    user = await _seed_user(db_session)
    service = CareerProfileService(db_session, export_dir=tmp_path)

    json_path = await service.export_json(user.id)
    yaml_path = await service.export_yaml(user.id)

    assert json_path == tmp_path / f"{user.id}.json"
    assert yaml_path == tmp_path / f"{user.id}.yaml"

    json_content = json.loads(json_path.read_text(encoding="utf-8"))
    yaml_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    assert json_content["personal_info"]["full_name"] == "Integration User"
    assert yaml_content["personal_info"]["full_name"] == "Integration User"


@pytest.mark.asyncio
async def test_build_profile_raises_for_unknown_user(db_session: AsyncSession) -> None:
    service = CareerProfileService(db_session)

    with pytest.raises(ValueError, match="No user found"):
        await service.build_profile(uuid.uuid4())
