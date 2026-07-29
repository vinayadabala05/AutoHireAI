"""Unit tests for `app.browser_automation.uploader.DocumentUploader`."""

from pathlib import Path

import pytest

from app.application_planning.models import ApplicationPackage
from app.browser_automation.exceptions import UploadError
from app.browser_automation.models import FormFieldType
from app.browser_automation.portal import GreenhouseAdapter
from app.browser_automation.uploader import DocumentUploader
from tests.browser_automation_fixtures import FakePage
from tests.resume_fixtures import make_llm_service, sample_career_profile


async def _sample_package(job_id: str = "job-1") -> ApplicationPackage:
    from app.cover_letter.service import CoverLetterGenerationService
    from app.intelligence.resume_planner import ResumePlanner
    from app.resume.service import ResumeGenerationService
    from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    resume_service = ResumeGenerationService(make_llm_service([]))
    cover_letter_service = CoverLetterGenerationService(make_llm_service([]))

    from app.application_planning.package_builder import ApplicationPackageBuilder

    builder = ApplicationPackageBuilder(
        resume_service, cover_letter_service, enhance_with_llm=False
    )
    return await builder.build(_fake_job(), profile, blueprint, job_id)


def _fake_job():  # noqa: ANN202 - test helper, avoids circular import churn
    from tests.job_discovery_fixtures import sample_job

    return sample_job()


async def test_upload_resume_writes_temp_file_and_uploads(tmp_path: Path) -> None:
    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()
    page.selector_counts["input[type=file].resume"] = 1

    result = await uploader.upload_resume(page, package, "input[type=file].resume")

    assert result.uploaded is True
    assert Path(result.file_path).exists()
    assert Path(result.file_path).read_text(encoding="utf-8") == package.resume_markdown


async def test_upload_cover_letter_writes_temp_file_and_uploads(tmp_path: Path) -> None:
    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()
    page.selector_counts["input[type=file].cover"] = 1

    result = await uploader.upload_cover_letter(page, package, "input[type=file].cover")

    assert result.uploaded is True
    assert Path(result.file_path).read_text(encoding="utf-8") == package.cover_letter_markdown


async def test_upload_raises_when_upload_cannot_be_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.browser_automation_fixtures import FakeLocator

    async def _never_verifies(self: FakeLocator, script: str) -> bool:
        return False

    monkeypatch.setattr(FakeLocator, "evaluate", _never_verifies)

    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()
    page.selector_counts["input[type=file].resume"] = 1

    with pytest.raises(UploadError, match="could not be verified"):
        await uploader.upload_resume(page, package, "input[type=file].resume")


async def test_upload_raises_when_selector_not_found(tmp_path: Path) -> None:
    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()  # selector never registered

    with pytest.raises(UploadError):
        await uploader.upload_resume(page, package, "input[type=file].missing")


async def test_upload_all_uploads_both_when_adapter_defines_both_selectors(tmp_path: Path) -> None:
    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()

    class _UploadAdapter(GreenhouseAdapter):
        @property
        def field_selectors(self) -> dict:
            return {
                FormFieldType.RESUME_UPLOAD: "input.resume",
                FormFieldType.COVER_LETTER_UPLOAD: "input.cover",
            }

    page.selector_counts["input.resume"] = 1
    page.selector_counts["input.cover"] = 1

    results = await uploader.upload_all(page, _UploadAdapter(), package)
    assert {r.field_type for r in results} == {
        FormFieldType.RESUME_UPLOAD,
        FormFieldType.COVER_LETTER_UPLOAD,
    }


async def test_upload_all_returns_empty_when_adapter_has_no_upload_selectors(
    tmp_path: Path,
) -> None:
    class _NoUploadAdapter(GreenhouseAdapter):
        @property
        def field_selectors(self) -> dict:
            return {}

    package = await _sample_package()
    uploader = DocumentUploader(temp_dir=tmp_path)
    page = FakePage()
    results = await uploader.upload_all(page, _NoUploadAdapter(), package)
    assert results == []


def test_default_temp_dir_is_system_tempdir() -> None:
    import tempfile

    uploader = DocumentUploader()
    assert uploader._temp_dir == Path(tempfile.gettempdir())  # noqa: SLF001
