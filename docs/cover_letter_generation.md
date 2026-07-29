# Cover Letter Generation Engine (Sprint 6)

## 1. Purpose

The cover letter generation engine (`app/cover_letter/`) turns a
`CareerProfile` (Sprint 3.5), a `ResumeBlueprint` (Sprint 3), and an
already-generated `ResumeDocument` (Sprint 5) into a personalized,
ATS-friendly cover letter for a specific job and company, using
`LLMService` (Sprint 4) for the one section that benefits from
natural-language writing. `CoverLetterGenerationService` is the single
facade — nothing else in this package is a public entrypoint, mirroring the
convention `ResumeGenerationService` (Sprint 5) and `CareerProfileService`
(Sprint 3.5) established.

This sprint does not do PDF generation, browser automation, job scraping,
or resume generation — it consumes Sprint 5's resume output, it does not
re-implement it. No Sprint 1–5 logic was modified.

## 2. Architecture

```
app/cover_letter/
├── models.py       # CoverLetterDocument, CoverLetterSection, CoverLetterTemplate,
│                   # CoverLetterSectionType, CoverLetterValidationIssue/Result,
│                   # CoverLetterValidationError
├── templates.py    # TemplateSpec registry: which resume sections to
│                   # summarize + closing phrase, per role
├── generator.py    # CoverLetterGenerator: profile + blueprint + resume
│                   # document (+ LLMService) -> CoverLetterDocument
├── formatter.py     # to_markdown(CoverLetterDocument) -> str (pure, deterministic)
├── renderer.py       # markdown_to_html, to_html, export_markdown_file, export_html_file
├── validator.py       # CoverLetterValidator: pre-generation input checks +
│                       # post-generation document checks
└── service.py          # CoverLetterGenerationService: the single public facade
```

### Dependency direction

```
caller  →  CoverLetterGenerationService  →  CoverLetterValidator
                     │                             ▲
                     ├─ CoverLetterGenerator ───────┘ (validates inputs before generating)
                     │        │
                     │        ├─ LLMService (Sprint 4)       [Body section only]
                     │        ├─ CareerProfile (Sprint 3.5)   [read-only]
                     │        ├─ ResumeBlueprint (Sprint 3)    [read-only]
                     │        └─ ResumeDocument (Sprint 5)      [read-only — source of career_summary]
                     │
                     └─ formatter.to_markdown → renderer.to_html / export_*_file
```

`app/cover_letter/` imports `ResumeSectionType`/`ResumeDocument` from
`app.resume.models` (a read-only type dependency) but does not import
`app.resume.generator`, `formatter`, or `renderer` — its own
`formatter.py`/`renderer.py` are self-contained, so each generation engine
stays independently testable, exactly as `app.resume` stayed independent of
`app.llm.providers`.

## 3. Generation pipeline — a single `generate_document()` call

```
caller                 CoverLetterGenerationService   CoverLetterGenerator        LLMService
  |                            |                            |                        |
  |-- generate_document() ---->|                            |                        |
  |                            |-- validate_inputs() --------| (CoverLetterValidator)  |
  |                            |     (raises if invalid, unless bypassed)              |
  |                            |-- generator.generate() ---->|                        |
  |                            |                             |-- build career_summary  |
  |                            |                             |   from ResumeDocument   |
  |                            |                             |   sections (per template)|
  |                            |                             |-- render_prompt() ----->| (cover_letter/generate_cover_letter)
  |                            |                             |-- generate() ---------->|
  |                            |                             |<--- LLMResponse --------|
  |                            |                             | (Greeting/Closing/Signature
  |                            |                             |  built deterministically,
  |                            |                             |  no LLM call)
  |                            |<---- CoverLetterDocument ----|                        |
  |<---- CoverLetterDocument --|                                                       |
```

Only the `Body` section is LLM-generated, using
`prompts/cover_letter/generate_cover_letter.txt` (Sprint 4's one cover
letter prompt) with variables `full_name`, `job_title`, `company_name`,
`career_summary`, and `job_description`. `Greeting` (`"Dear {hiring_manager
or 'Hiring Manager'},"`), `Closing` (the template's `closing_phrase`), and
`Signature` (the candidate's full name) are built deterministically — so
three of the four sections are reproducible without mocking the LLM, and
`enhance_with_llm=False` makes the `Body` section deterministic too (it
falls back to the raw `career_summary` text).

`career_summary` is assembled by concatenating the `ResumeDocument`
sections a template emphasizes (`templates.get_template_spec(template).emphasize_resume_sections`,
each truncated to 400 characters) plus `ResumeBlueprint.recommended_skills`
— this is the sprint's core integration point: cover letter generation
reads Sprint 5's *output*, it does not re-derive a summary from
`CareerProfile` itself.

## 4. Template system

Like `app.resume.templates`, a cover letter "template" is not visual
styling (Markdown/HTML shape is identical across templates) — it is a
role-specific policy for which parts of an already-generated resume are
worth summarizing, plus a closing phrase:

| Template | Resume sections emphasized (in order) | Closing phrase |
|---|---|---|
| `software_engineer` | Summary, Experience, Projects, Skills | "Sincerely," |
| `ai_engineer` | Summary, Projects, Skills, Experience | "Sincerely," |
| `backend_engineer` | Summary, Experience, Skills, Projects | "Sincerely," |
| `research_engineer` | Summary, Projects, Education, Experience | "Respectfully," |

## 5. Validation rules

`CoverLetterValidator` (`app/cover_letter/validator.py`) exposes two
independent passes, mirroring `ResumeValidator`:

- **`validate_inputs(profile, blueprint, resume_document, company_name, job_title)`**
  — runs before generation:
  - `missing_company_name` (error) — blank/whitespace-only company name.
  - `missing_job_title` (error) — blank/whitespace-only job title.
  - `missing_contact_info` (error) — profile has no email for the signature block.
  - `no_source_material` (error) — the resume document has none of
    `Summary`/`Experience`/`Projects` to summarize.
  - `empty_recommended_skills` (warning) — blueprint recommends no skills.
- **`validate_document(document)`** — runs after generation:
  - `missing_section` (error) — one of `Greeting`/`Body`/`Closing`/`Signature`
    is absent.
  - `empty_section` (error) — a present section has blank content.
  - `image_reference` (error) — a section contains `![...]` Markdown image syntax.
  - `possible_table` (warning) — a section looks like it contains a Markdown table.
  - `tab_character` (warning) — a section contains a literal tab.
  - `unfilled_placeholder` (error) — a section still contains bracket/brace
    placeholder text (e.g. `[Company Name]`, `{{job_title}}`) that should
    have been substituted — this is the sprint's ATS/personalization
    safety net: it catches a company- or job-specific placeholder the LLM
    or a template left unfilled.

As with Sprint 5, `is_valid` is `False` only when at least one `error`
severity issue is present; `CoverLetterGenerationService.generate_document()`
runs `validate_inputs` first and raises `CoverLetterValidationError` unless
`require_valid_inputs=False`.

## 6. Usage

```python
from app.cover_letter.models import CoverLetterTemplate
from app.cover_letter.service import CoverLetterGenerationService

service = CoverLetterGenerationService(llm_service)  # llm_service: Sprint 4 LLMService

document = await service.generate_document(
    profile,               # CareerProfile, from CareerProfileService (Sprint 3.5)
    blueprint,             # ResumeBlueprint, from ResumePlanner (Sprint 3)
    resume_document,       # ResumeDocument, from ResumeGenerationService (Sprint 5)
    company_name="Acme Corp",
    job_title="Backend Engineer",
    job_description=job_posting.description,
    template=CoverLetterTemplate.BACKEND_ENGINEER,
    hiring_manager="Alex Lee",  # optional; falls back to "Hiring Manager"
)

result = service.validate_document(document)
markdown_path = service.export_markdown(document)
html_path = service.export_html(document)
```

PDF export is intentionally not implemented — `service.to_html(document)`
is available for a future sprint to feed into a headless renderer, matching
Sprint 5's approach.

## 7. Extension guide

**Adding a fifth template** requires one new `TemplateSpec` entry in
`app/cover_letter/templates.py` plus a new `CoverLetterTemplate` enum value
in `models.py` — `CoverLetterGenerator`, `CoverLetterGenerationService`, and
every caller are unaffected, since they only pass a `CoverLetterTemplate`
value through to `get_template_spec()`.

**Changing what goes into `career_summary`**: adjust
`emphasize_resume_sections` for a template, or the truncation length
(`_MAX_SECTION_CHARS` in `generator.py`) — no change needed to
`formatter.py`, `renderer.py`, or `validator.py`, since they operate on the
finished `CoverLetterDocument`/Markdown, not on how the `Body` section's
content was produced.

**Adding a new deterministic section** (e.g. a `Postscript`): add it to
`CoverLetterSectionType` in `models.py`, a content-builder in
`CoverLetterGenerator.generate()`, and optionally add it to
`REQUIRED_SECTIONS` in `validator.py` if it should be mandatory.

**Adding LLM enhancement to another section** (e.g. a custom greeting that
references something specific about the company): add a new prompt
template under `prompts/cover_letter/`, add a generator method mirroring
`_body_content`, and call it from `generate()`.

## 8. Testing strategy

Sprint 6 has no database dependency and no real LLM calls — every test uses
`tests/resume_fixtures.ScriptedResumeProvider` (reused from Sprint 5) via
`tests/cover_letter_fixtures.py`, which also builds a *real* `ResumeDocument`
using Sprint 5's own `ResumeGenerator` (not a hand-rolled stand-in) so
cover letter tests exercise genuine cross-sprint integration:

- `test_cover_letter_templates.py` — template registration and emphasis ordering.
- `test_cover_letter_formatter.py` — deterministic Markdown output, header block, section ordering.
- `test_cover_letter_renderer.py` — Markdown→HTML conversion, HTML escaping, file export.
- `test_cover_letter_validator.py` — every input/document validation code path,
  including the `unfilled_placeholder` ATS-personalization check.
- `test_cover_letter_generator.py` — unit tests against a real `ResumeDocument`
  and `ResumeBlueprint`, covering LLM-enhanced vs. deterministic generation,
  hiring-manager personalization, per-template closing phrases, and
  determinism given a fixed script.
- `test_cover_letter_service.py` — integration tests across all four
  templates and three job descriptions (`backend_engineer`, `ai_engineer`,
  `research_engineer`), input-validation enforcement/bypass, and
  Markdown/HTML export round-trips via `tmp_path`.
