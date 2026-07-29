"""Career Profile Service: the single entrypoint every caller should use.

Orchestrates `loader.py` -> `builder.py` -> (`validator.py` | `exporter.py`).
This is the class future AI features, API routes, and background jobs
import — none of them should reach for `ProfileDataLoader` or
`CareerProfileBuilder` directly.
"""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.career_profile.builder import CareerProfileBuilder
from app.career_profile.exporter import ProfileExporter
from app.career_profile.loader import ProfileDataLoader
from app.career_profile.models import CareerProfile, ValidationReport
from app.career_profile.validator import ProfileValidator

_DEFAULT_EXPORT_DIR = Path("data/career_profiles")


class CareerProfileService:
    def __init__(self, session: AsyncSession, export_dir: Path | None = None) -> None:
        self._loader = ProfileDataLoader(session)
        self._builder = CareerProfileBuilder()
        self._validator = ProfileValidator()
        self._exporter = ProfileExporter()
        self._export_dir = export_dir or _DEFAULT_EXPORT_DIR

    async def build_profile(self, user_id: uuid.UUID) -> CareerProfile:
        raw = await self._loader.load(user_id)
        return self._builder.build(raw)

    async def validate_profile(self, user_id: uuid.UUID) -> ValidationReport:
        profile = await self.build_profile(user_id)
        return self._validator.validate(profile)

    async def export_json(self, user_id: uuid.UUID, path: Path | None = None) -> Path:
        profile = await self.build_profile(user_id)
        return self._exporter.export_json_file(profile, path or self._default_path(user_id, "json"))

    async def export_yaml(self, user_id: uuid.UUID, path: Path | None = None) -> Path:
        profile = await self.build_profile(user_id)
        return self._exporter.export_yaml_file(profile, path or self._default_path(user_id, "yaml"))

    def _default_path(self, user_id: uuid.UUID, extension: str) -> Path:
        return self._export_dir / f"{user_id}.{extension}"
