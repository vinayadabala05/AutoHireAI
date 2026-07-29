"""Document upload: writes the generated resume/cover letter to temporary
files and uploads them via Playwright's file-input API, verifying the
browser actually registered the file.

Sprint 5/6 deliberately do not generate PDF output yet (documented in
their own sprints as future work) — this uploader works with whatever
`ApplicationPackage` provides today (Markdown) and needs no change once a
future sprint adds PDF export; only the temp-file extension/content would
change here.
"""

import tempfile
from pathlib import Path

from loguru import logger
from playwright.async_api import Page

from app.application_planning.models import ApplicationPackage
from app.browser_automation.exceptions import UploadError
from app.browser_automation.interfaces import PortalAdapterProtocol
from app.browser_automation.models import FormFieldType, UploadResult


class DocumentUploader:
    def __init__(self, temp_dir: Path | str | None = None) -> None:
        self._temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())

    async def upload_all(
        self, page: Page, adapter: PortalAdapterProtocol, package: ApplicationPackage
    ) -> list[UploadResult]:
        """Upload the resume and/or cover letter, whichever selectors `adapter` defines."""
        results: list[UploadResult] = []
        resume_selector = adapter.field_selectors.get(FormFieldType.RESUME_UPLOAD)
        if resume_selector:
            results.append(await self.upload_resume(page, package, resume_selector))
        cover_letter_selector = adapter.field_selectors.get(FormFieldType.COVER_LETTER_UPLOAD)
        if cover_letter_selector:
            results.append(await self.upload_cover_letter(page, package, cover_letter_selector))
        return results

    async def upload_resume(
        self, page: Page, package: ApplicationPackage, selector: str
    ) -> UploadResult:
        path = self._write_temp_file(f"{package.job_id}_resume", package.resume_markdown)
        return await self._upload(page, selector, path, FormFieldType.RESUME_UPLOAD)

    async def upload_cover_letter(
        self, page: Page, package: ApplicationPackage, selector: str
    ) -> UploadResult:
        path = self._write_temp_file(
            f"{package.job_id}_cover_letter", package.cover_letter_markdown
        )
        return await self._upload(page, selector, path, FormFieldType.COVER_LETTER_UPLOAD)

    async def _upload(
        self, page: Page, selector: str, path: Path, field_type: FormFieldType
    ) -> UploadResult:
        locator = page.locator(selector)
        if await locator.count() == 0:
            raise UploadError(f"No upload field found at selector '{selector}'.")

        await locator.set_input_files(str(path))
        uploaded = await locator.evaluate("el => el.files && el.files.length > 0")
        if not uploaded:
            raise UploadError(f"Upload to '{selector}' could not be verified.")

        logger.bind(field=field_type.value, path=str(path)).info("Uploaded document.")
        return UploadResult(field_type=field_type, file_path=str(path), uploaded=True)

    def _write_temp_file(self, name: str, content: str) -> Path:
        path = self._temp_dir / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        return path
