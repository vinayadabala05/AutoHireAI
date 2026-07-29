# Browser Automation Engine (Sprint 10)

## 1. Purpose

The Browser Automation Engine (`app/browser_automation/`) receives an
`ApplicationPackage` (Sprint 9) and submits it on a supported job portal
via Playwright/Chromium. It is the final stage of the pipeline: Job
Discovery (7) → Application Planning (9) → **Browser Automation (10)**.

`BrowserAutomationService` is the single facade — nothing else in this
package is a public entrypoint, mirroring every prior sprint's convention.
This supersedes the never-implemented Sprint 1 `app/browser/` placeholder,
left untouched under its own name to avoid ambiguity.

## 2. Architecture

```
app/browser_automation/
├── models.py              # PortalType, SubmissionStatus, FormFieldType, BrowserConfig,
│                          # LoginCredentials, SessionData, FormFillOptions, SubmissionResult, ...
├── exceptions.py            # BrowserAutomationError hierarchy
├── interfaces.py              # PortalAdapterProtocol — the extension point
├── retry.py                     # retry_action(): thin wrapper reusing Sprint 8's RetryPolicy
├── playwright_manager.py           # PlaywrightManager: Chromium process lifecycle
├── browser.py                        # BrowserSession: one reusable BrowserContext + Pages
├── session.py                          # SessionStore: cookie/storage_state persistence + validation
├── portal.py                             # PortalAdapter ABC + registry + 4 concrete adapters
├── navigator.py                            # Generic page navigation (open, click Apply, waits)
├── form_filler.py                            # Populates known fields from CareerProfile
├── uploader.py                                 # Resume/cover-letter file upload + verification
├── executor.py                                   # ApplicationExecutor: the full per-job flow
└── service.py                                      # BrowserAutomationService: the public facade
```

### Dependency direction

```
caller  →  BrowserAutomationService  →  PlaywrightManager / BrowserSession / SessionStore
                    │                            │
                    ├─ FormFiller  ───────────────┴─→  CareerProfile (Sprint 3.5, read-only)
                    ├─ DocumentUploader  ──────────────→  ApplicationPackage (Sprint 9, read-only)
                    └─ ApplicationExecutor  →  Navigator, FormFiller, DocumentUploader
                                            →  retry_action  →  RetryPolicy (Sprint 8, reused)
                                            →  PortalAdapter (registry, portal.py)
```

No portal adapter imports another adapter, `navigator.py`, `form_filler.py`,
`uploader.py`, or `executor.py` — every adapter's only job is to expose
selectors and portal-specific checks (`is_logged_in`, `find_apply_button`,
`submit`, `detect_success`). Everything downstream operates purely on
`PortalAdapterProtocol`, never a concrete adapter class.

## 3. Supported portals (v1)

| Portal | Apply flow | Notes |
|---|---|---|
| **LinkedIn Easy Apply** | Multi-step in-page modal | Name/email/resume pre-filled from the member's profile by LinkedIn itself; no separate cover-letter upload control |
| **Greenhouse** | Form embedded directly on the job page | Resume + cover letter upload fields both present |
| **Lever** | Separate `/apply` page | Resume + cover letter upload fields both present |
| **Ashby** | In-page JS application form | Resume + cover letter upload fields both present |

Adding a fifth portal requires exactly one new class:

```python
# app/browser_automation/portal.py (or a new module importing register_portal)
@register_portal(PortalType.INDEED)          # add INDEED to the PortalType enum first
class IndeedAdapter(PortalAdapter):
    @property
    def portal_type(self) -> PortalType:
        return PortalType.INDEED

    @property
    def field_selectors(self) -> dict[FormFieldType, str]:
        return {...}

    async def is_logged_in(self, page): ...
    async def find_apply_button(self, page): ...
    async def submit(self, page): ...
    async def detect_success(self, page): ...
```

No change to `navigator.py`, `form_filler.py`, `uploader.py`, or
`executor.py` — all depend only on `PortalAdapterProtocol`.

**Selectors are documented, best-effort defaults** for each platform's
typical DOM. Real employer career pages customize styling/markup, so
production use should expect to override `field_selectors` per posting
where needed — this module never falls back to guessing at an unknown
selector; unsupported questions are surfaced, not guessed at (§6).

## 4. Browser lifecycle

`PlaywrightManager` owns exactly one Chromium `Browser` process (headless
by default, configurable via `BrowserConfig`). `BrowserSession` owns one
reusable `BrowserContext` — reused across multiple job applications in the
same run rather than one context per job — and hands out `Page`s.
Cleanup is guaranteed via the async context manager protocol on both:

```python
async with PlaywrightManager(BrowserConfig(headless=True)) as manager:
    async with BrowserSession(manager) as browser_session:
        page = await browser_session.new_page()
        ...
# both the context and the browser process are closed here, even on error
```

## 5. Session management

`SessionStore` persists Playwright's own `storage_state` (cookies + local
storage) as one JSON file per portal/account under
`data/browser_sessions/{portal}/{account_key}.json`. `validate()` checks
two independent things:

1. **TTL** — raises `SessionExpiredError` if the session is older than its
   configured lifetime (default 7 days).
2. **Actual authentication** — defers to the portal adapter's own
   `is_logged_in(page)`, since a TTL alone can't tell you a portal didn't
   revoke the session server-side.

`login()` never embeds real credentials: `LoginCredentials` (with the
password as a Pydantic `SecretStr`) is always supplied by the caller —
from an environment variable, a secrets manager, or an interactive
prompt — never hardcoded in this module.

## 6. Form filling

`FormFiller.fill()` populates every field an adapter's `field_selectors`
maps, sourced from two places:

- **`CareerProfile`** (Sprint 3.5, reused as-is): full name, email, phone,
  location (used for "address"), a summarized education/experience
  history, and a comma-joined skills list.
- **`FormFillOptions`** (new, per-application): work authorization, visa
  sponsorship, notice period, and salary expectation — none of these
  belong on `CareerProfile` itself (they're per-application or
  employer-policy facts, not stable career history), so they're supplied
  by the caller per submission.

Dispatch by the target element's actual DOM shape (checked via
`element.tagName`/`element.type`, not assumed from the field's semantic
type): `<select>` → `select_option()`, `type=checkbox` → `check()`/
`uncheck()` from a Yes/No-ish value, `type=radio` → `check()`, anything
else → `fill()` (plain text). **If a field is present on the page but no
value is available, it is returned as an `UnsupportedQuestion` — never
guessed.** A field simply absent from the current posting's form (adapter
defines a selector, but this job doesn't ask it) is silently skipped, not
reported as unsupported.

## 7. Document upload

`DocumentUploader` writes `ApplicationPackage.resume_markdown` /
`cover_letter_markdown` to a temporary `.md` file and uploads it via
Playwright's `set_input_files`, then verifies the upload by checking
`element.files.length > 0` — raising `UploadError` if the field wasn't
found or the browser never registered the file.

Sprint 5/6 deliberately don't generate PDF output yet (documented in their
own sprints as future work); this uploader works with whatever
`ApplicationPackage` provides today and needs no change once a future
sprint adds PDF export — only the temp-file extension/content would
change.

## 8. Retry strategy

`retry.py`'s `retry_action()` is a thin wrapper, not a new policy
hierarchy — Sprint 8 (`app.graph.retry`) already ships a fully-tested one
(immediate, fixed-delay, exponential backoff, configurable retryable-
exception filtering). `ApplicationExecutor` applies an injected
`RetryPolicy` (`NoRetryPolicy` by default) around navigation and submit
actions:

```python
from app.graph.retry import ExponentialBackoffRetryPolicy

executor = ApplicationExecutor(
    retry_policy=ExponentialBackoffRetryPolicy(base_delay=1.0, max_retries=3),
)
```

## 9. Error handling & failure recovery

`ApplicationExecutor.execute()` never raises for a normal submission
failure — it always returns a `SubmissionResult`:

- `status=SUBMITTED` — success, every question answered.
- `status=PARTIAL` — submitted, but one or more questions were left
  unanswered (`metadata["unsupported_questions"]` lists them).
- `status=FAILED` — navigation, form-fill, upload, or submission failed;
  `error_message` is set, and a **screenshot is captured** (best-effort —
  a screenshot failure itself is logged and swallowed, never masking the
  original error) at `screenshot_path`.

Structured exceptions (`NavigationError`, `FormFillError`, `UploadError`,
`SubmissionError`, `LoginError`, `SessionExpiredError`,
`PortalNotSupportedError`) let a caller distinguish failure classes when
inspecting logs, even though `execute()` itself catches them into a
`SubmissionResult`.

## 10. Usage example

```python
from app.browser_automation.models import BrowserConfig, FormFillOptions, LoginCredentials, PortalType
from app.browser_automation.playwright_manager import PlaywrightManager
from app.browser_automation.browser import BrowserSession
from app.browser_automation.service import BrowserAutomationService

service = BrowserAutomationService()
options = FormFillOptions(
    work_authorization="US Citizen", visa_sponsorship_required=False,
    notice_period="2 weeks", salary_expectation="$150,000",
)

async with PlaywrightManager(BrowserConfig(headless=True)) as manager:
    async with BrowserSession(manager) as browser_session:
        page = await browser_session.new_page()

        if not await service.validate_session(PortalType.GREENHOUSE, "me@example.com", page):
            await service.login(
                PortalType.GREENHOUSE, "me@example.com",
                LoginCredentials(username=login_email, password=login_password),  # never hardcoded
                login_url="https://example.com/login",
            )

        result = await service.submit_application(
            PortalType.GREENHOUSE, page, application_package, career_profile,
            options=options, plan=application_plan, job=discovered_job,
        )
        print(result.status, result.application_url, result.error_message)
```

## 11. Testing strategy

91 tests, 100% line coverage on `app/browser_automation/` (target: >95%).
**No real browser is launched** — every Playwright interaction
(`Page.goto`, `.click`, `.locator(...)`, `BrowserContext.new_page`,
`Browser.new_context`, `async_playwright()` itself) is behind a small
fake object (`tests/browser_automation_fixtures.py`) implementing just the
async surface this package calls, mirroring how Sprint 4/7 test LLM/HTTP
providers by faking the one boundary method rather than hitting a real
network — here, a real Chromium process.

- `test_browser_automation_models.py`, `test_browser_automation_interfaces.py` — data models, structural conformance
- `test_browser_automation_retry.py` — success, immediate failure, eventual recovery, exhaustion, positive delay
- `test_browser_automation_playwright_manager.py`, `test_browser_automation_browser.py` — lifecycle, idempotency, cleanup guarantees
- `test_browser_automation_session.py` — save/load/expiry/validate/delete
- `test_browser_automation_portal.py` — registry + all four adapters' full lifecycle (login detection, apply button, submit, success detection)
- `test_browser_automation_navigator.py` — navigation, timeout handling, tolerated missing-navigation-event, redirect waits
- `test_browser_automation_form_filler.py` — every field-type dispatch (text/select/checkbox/radio), unsupported-question reporting, absent-field skipping
- `test_browser_automation_uploader.py` — successful upload, missing selector, unverified upload
- `test_browser_automation_executor.py` — full success, partial, every failure mode, retries, screenshot capture (including screenshot-capture-itself-failing), application-id extraction
- `test_browser_automation_service.py` — login (success/failure), session validation, form filling, document upload, full submit-with-context-enrichment
