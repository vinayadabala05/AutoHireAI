# Resume Generation Engine (Sprint 5)

## 1. Purpose

The resume generation engine (`app/resume/`) turns a `ResumeBlueprint`
(Sprint 3 — what to include and in what order, for a specific job) and a
`CareerProfile` (Sprint 3.5 — the user's full career data) into an
ATS-optimized resume, using `LLMService` (Sprint 4) for the two sections
that benefit from natural-language rewriting. Every other module (`app/`)
should call `ResumeGenerationService`, the single facade — nothing else in
this package is a public entrypoint.

This sprint does not do PDF generation, browser automation, job scraping, or
cover letter generation. It does not modify Sprint 1–4 logic.

## 2. Architecture

```
app/resume/
├── models.py       # ResumeDocument, ResumeSection, ResumeTemplate,
│                   # ResumeSectionType, ResumeValidationIssue/Result,
│                   # ResumeValidationError
├── templates.py    # TemplateSpec registry: section order + emphasis per role
├── generator.py    # ResumeGenerator: blueprint + profile (+ LLMService) -> ResumeDocument
├── formatter.py     # to_markdown(ResumeDocument) -> str (pure, deterministic)
├── renderer.py      # markdown_to_html, to_html, export_markdown_file, export_html_file
├── validator.py     # ResumeValidator: pre-generation input checks + post-generation document checks
└── service.py        # ResumeGenerationService: the single public facade
```

### Dependency direction

```
caller  →  ResumeGenerationService  →  ResumeValidator
                    │                          ▲
                    ├─ ResumeGenerator ─────────┘ (validates inputs before generating)
                    │        │
                    │        └─ LLMService (Sprint 4)      [Summary + Experience bullets only]
                    │        └─ CareerProfile (Sprint 3.5)  [read-only]
                    │        └─ ResumeBlueprint (Sprint 3)  [read-only]
                    │
                    └─ formatter.to_markdown → renderer.to_html / export_*_file
```

No module here imports a concrete LLM provider, a database session, or a
career-profile loader/builder — those stay entirely inside Sprint 3.5/4's
own facades (`CareerProfileService`, `LLMService`), consistent with the
"one facade per subsystem" convention Sprint 4 established.

## 3. Pipeline — a single `generate_document()` call

```
caller                  ResumeGenerationService     ResumeGenerator          LLMService
  |                            |                         |                      |
  |-- generate_document() ---->|                         |                      |
  |                            |-- validate_inputs() -----| (ResumeValidator)    |
  |                            |     (raises if invalid, unless bypassed)        |
  |                            |-- generator.generate() ->|                      |
  |                            |                          |-- render_prompt() -->| (resume/summary_rewrite)
  |                            |                          |-- generate() ------->|
  |                            |                          |<--- LLMResponse -----|
  |                            |                          |-- render_prompt() -->| (resume/bullet_point_rewrite,
  |                            |                          |-- generate() ------->|  once per achievement)
  |                            |                          |<--- LLMResponse -----|
  |                            |                          | (Skills/Projects/Education/Certificates
  |                            |                          |  built deterministically, no LLM call)
  |                            |<---- ResumeDocument ------|                      |
  |<---- ResumeDocument -------|                                                 |
```

Section order comes from `templates.resolve_section_order()`: the
blueprint's own `resume_sections` (computed by Sprint 3's
`SectionOptimizer` for this specific job) wins whenever it parses into at
least one known `ResumeSectionType`; the template's `default_section_order`
is only a fallback for a blueprint that produced nothing usable.

Only `Summary` and each `Experience` achievement go through an LLM rewrite
pass — those are the only two prompts Sprint 4 shipped
(`prompts/resume/summary_rewrite.txt`, `prompts/resume/bullet_point_rewrite.txt`).
`Skills`, `Projects`, `Education`, and `Certificates` are built
deterministically straight from `CareerProfile` fields, ranked/filtered by
the blueprint (e.g. `Projects` are ordered by `ResumeBlueprint.recommended_projects`
confidence, then by `CareerProfile.projects[].priority`). This keeps most of
the document reproducible without mocking the LLM, and callers can pass
`enhance_with_llm=False` to skip the LLM entirely (e.g. for fast validation
previews) or omit `job_title` to skip only the summary rewrite (a
job-specific summary needs a job title; achievement rewriting does not).

## 4. Template system

A "template" here is not visual styling — Markdown/HTML shape is identical
across templates, defined once in `formatter.py`/`renderer.py`. A template is
a role-specific **section ordering + emphasis policy**, expressed as an
immutable `TemplateSpec` (`app/resume/templates.py`):

| Template | Default section order | Emphasized sections |
|---|---|---|
| `software_engineer` | Summary, Experience, Projects, Skills, Education, Certificates | Experience, Projects |
| `ai_engineer` | Summary, Skills, Projects, Experience, Education, Certificates | Skills, Projects |
| `backend_engineer` | Summary, Experience, Projects, Skills, Education, Certificates | Experience |
| `research_engineer` | Summary, Projects, Experience, Skills, Education, Certificates | Projects, Education |

`emphasize_sections` is metadata for future use (e.g. a future sprint could
spend more LLM budget or verbosity on emphasized sections); Sprint 5 itself
only uses `default_section_order` today.

## 5. Validation

`ResumeValidator` (`app/resume/validator.py`) exposes two independent
passes:

- **`validate_inputs(blueprint, profile)`** — runs before generation:
  - `empty_skills` (error) — profile has no skills.
  - `empty_recommended_skills` (warning) — blueprint recommends none.
  - `no_track_record` (error) — profile has neither experience nor projects.
  - `duplicate_project` (error, one per name) — the same project name
    appears more than once in `profile.projects`.
- **`validate_document(document)`** — runs after generation:
  - `missing_section` (error) — one of `Summary`/`Experience`/`Skills`/`Education`
    is absent from the generated document.
  - `empty_section` (error) — a present section has blank content.
  - `image_reference` (error) — a section contains `![...]` Markdown image syntax.
  - `possible_table` (warning) — a section looks like it contains a Markdown table.
  - `tab_character` (warning) — a section contains a literal tab.
  - `excess_blank_lines` (warning) — three or more consecutive blank lines.
  - `non_standard_bullet` (warning) — a bullet glyph other than `-` is used.

`ResumeValidationResult.is_valid` is `False` only when at least one `error`
severity issue is present; warnings never block generation. By default,
`ResumeGenerationService.generate_document()` runs `validate_inputs` first
and raises `ResumeValidationError` if it fails — pass
`require_valid_inputs=False` to generate anyway (e.g. to preview what a
thin profile would produce).

## 6. Resume generation flow (usage)

```python
from app.resume.models import ResumeTemplate
from app.resume.service import ResumeGenerationService

service = ResumeGenerationService(llm_service)  # llm_service: Sprint 4 LLMService

document = await service.generate_document(
    blueprint,             # ResumeBlueprint, from ResumePlanner (Sprint 3)
    profile,               # CareerProfile, from CareerProfileService (Sprint 3.5)
    template=ResumeTemplate.BACKEND_ENGINEER,
    job_title="Backend Engineer",
    job_description=job_posting.description,
)

result = service.validate_document(document)
markdown_path = service.export_markdown(document)   # Markdown export
html_path = service.export_html(document)            # HTML export
```

PDF export is intentionally not implemented — a future sprint can feed
`service.to_html(document)` into a headless renderer without changing this
module.

## 7. Extension guide

**Adding a fifth template** requires one new `TemplateSpec` entry:

```python
# app/resume/templates.py
ResumeTemplate.DATA_ENGINEER: TemplateSpec(
    template=ResumeTemplate.DATA_ENGINEER,
    display_name="Data Engineer",
    default_section_order=(...),
    emphasize_sections=(...),
),
```

...plus adding `DATA_ENGINEER = "data_engineer"` to the `ResumeTemplate`
enum in `models.py`. `ResumeGenerator`, `ResumeGenerationService`, and every
caller are unaffected — they only ever pass a `ResumeTemplate` value
through to `resolve_section_order()`.

**Adding a new section type** (e.g. `Publications` for research roles)
requires adding it to `ResumeSectionType` in `models.py`, a content-builder
branch in `ResumeGenerator._build_section()`, and (optionally) adding it to
`REQUIRED_SECTIONS` in `validator.py` if it should be mandatory. Since
`ResumeBlueprint.resume_sections` is just `list[str]` from Sprint 3, no
upstream change is needed for a template to start requesting the new
section — only unrecognized strings are dropped by
`resolve_section_order()`.

**Adding LLM enhancement to another section** (e.g. rewriting project
descriptions): add a new prompt template under `prompts/resume/`, add a
method to `ResumeGenerator` mirroring `_rewrite_bullet`/`_summary_content`,
and call it from `_build_section()`. No change to `formatter.py`,
`renderer.py`, `validator.py`, or `service.py` is needed — they operate on
`ResumeDocument`/Markdown, not on how a section's content was produced.

## 8. Testing strategy

Sprint 5 has no database dependency and no real LLM calls — every test uses
`tests/resume_fixtures.ScriptedResumeProvider`, a fake `BaseLLMProvider`
that echoes a scripted response per `generate()` call (mirroring the
`_ScriptedProvider` pattern Sprint 4's own tests already use):

- `test_resume_templates.py` — section-order resolution and fallback.
- `test_resume_formatter.py` — deterministic Markdown output, section ordering.
- `test_resume_renderer.py` — Markdown→HTML conversion, HTML escaping, file export.
- `test_resume_validator.py` — every input/document validation code path.
- `test_resume_generator.py` — unit tests against a real `ResumeBlueprint`
  (built via Sprint 3's `ResumePlanner` + `tests/intelligence_fixtures.py`),
  covering LLM-enhanced vs. deterministic generation, project ranking, and
  determinism given a fixed script.
- `test_resume_service.py` — integration tests across all four templates and
  three job descriptions (`backend_engineer`, `ai_engineer`,
  `research_engineer`), input-validation enforcement/bypass, and
  Markdown/HTML export round-trips via `tmp_path`.
