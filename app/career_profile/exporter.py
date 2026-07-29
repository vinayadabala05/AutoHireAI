"""Exports a `CareerProfile` to JSON or YAML.

Both formats are meant to be consumed by future AI providers (resume
generation, cover letters, interview prep, chat) as a single structured
context document — this module only serializes; it never talks to the
database or knows about a `user_id` (see `service.py` for that).
"""

from pathlib import Path

import yaml

from app.career_profile.models import CareerProfile


class ProfileExporter:
    def to_json(self, profile: CareerProfile, *, indent: int = 2) -> str:
        return profile.model_dump_json(indent=indent)

    def to_yaml(self, profile: CareerProfile) -> str:
        data = profile.model_dump(mode="json")
        return str(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def export_json_file(self, profile: CareerProfile, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(profile), encoding="utf-8")
        return path

    def export_yaml_file(self, profile: CareerProfile, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(profile), encoding="utf-8")
        return path
