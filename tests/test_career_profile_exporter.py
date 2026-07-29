"""Unit tests for `ProfileExporter` — pure serialization, no database."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.career_profile.exporter import ProfileExporter
from app.career_profile.models import CareerProfile, PersonalInfo, SkillProfile

exporter = ProfileExporter()


def _sample_profile() -> CareerProfile:
    return CareerProfile(
        user_id=uuid.uuid4(),
        generated_at=datetime.now(UTC),
        personal_info=PersonalInfo(full_name="Jordan Smith", email="jordan@example.com"),
        skills=[SkillProfile(name="Python", years_experience=5)],
    )


def test_to_json_round_trips_the_profile() -> None:
    profile = _sample_profile()

    payload = json.loads(exporter.to_json(profile))

    assert payload["personal_info"]["full_name"] == "Jordan Smith"
    assert payload["skills"][0]["name"] == "Python"
    assert payload["user_id"] == str(profile.user_id)


def test_to_yaml_round_trips_the_profile() -> None:
    profile = _sample_profile()

    payload = yaml.safe_load(exporter.to_yaml(profile))

    assert payload["personal_info"]["email"] == "jordan@example.com"
    assert payload["skills"][0]["years_experience"] == 5


def test_export_json_file_writes_readable_json(tmp_path: Path) -> None:
    profile = _sample_profile()
    target = tmp_path / "profile.json"

    written_path = exporter.export_json_file(profile, target)

    assert written_path == target
    assert (
        json.loads(target.read_text(encoding="utf-8"))["personal_info"]["full_name"]
        == "Jordan Smith"
    )


def test_export_yaml_file_writes_readable_yaml(tmp_path: Path) -> None:
    profile = _sample_profile()
    target = tmp_path / "nested" / "profile.yaml"

    written_path = exporter.export_yaml_file(profile, target)

    assert written_path == target
    assert target.exists()
    assert (
        yaml.safe_load(target.read_text(encoding="utf-8"))["personal_info"]["email"]
        == "jordan@example.com"
    )
