# Job Discovery Engine (Sprint 7)

## 1. Purpose

The Job Discovery Engine (`app/job_discovery/`) fetches job postings from
public ATS job-board APIs (Greenhouse, Lever, Ashby, Workable),
deduplicates and filters them, and ranks them 0-100 against a
`CareerProfile` (Sprint 3.5) and `ResumeBlueprint` (Sprint 3).
`JobDiscoveryService` is the single facade — nothing else in this package
is a public entrypoint, mirroring the convention every prior sprint
established (`CareerProfileService`, `LLMService`, `ResumeGenerationService`,
`CoverLetterGenerationService`).

**No browser automation, no LinkedIn/Indeed scraping, no Selenium/Playwright.**
Every provider talks to a documented, public job-board JSON API over plain
HTTP (`httpx`) — the same pattern Sprint 4's LLM providers use. See
§7 for how LinkedIn/Indeed would be added once (and if) an authorized API
integration exists.

## 2. Architecture

```
app/job_discovery/
├── models.py           # DiscoveredJob, JobProviderName, JobSearchQuery,
│                       # JobSearchPreferences, JobRankingExplanation/Result,
│                       # JobFilterCriteria, DeduplicationResult, PollingRegistration
├── exceptions.py        # JobDiscoveryError hierarchy
├── interfaces.py         # Protocols: JobProviderProtocol, JobRankingEngineProtocol,
│                         # JobDeduplicatorProtocol, JobFilterProtocol
├── parser.py              # Shared text-extraction helpers reused by every provider
├── providers/
│   ├── base.py             # BaseJobProvider (abstract contract) + self-registration registry
│   ├── greenhouse.py        # GreenhouseProvider
│   ├── lever.py               # LeverProvider
│   ├── ashby.py                # AshbyProvider
│   └── workable.py             # WorkableProvider
├── ranking.py                   # JobRankingEngine: 0-100 score + explanation
├── deduplication.py               # JobDeduplicator: URL + content-hash dedup
├── filters.py                       # JobFilter: criteria-based filtering
├── scheduler.py                       # JobDiscoveryScheduler: registration + run_once (no cron yet)
└── service.py                           # JobDiscoveryService: the single public facade
```

### Dependency direction

```
caller  →  JobDiscoveryService  →  BaseJobProvider (abstract) ← Greenhouse/Lever/Ashby/Workable
                  │                        ▲
                  │                        │ implements, self-registers via @register_provider
                  ├─ JobDeduplicator
                  ├─ JobFilter
                  └─ JobRankingEngine  →  CareerProfile (Sprint 3.5, read-only)
                                       →  ResumeBlueprint (Sprint 3, read-only)
                                       →  SkillMatcher (Sprint 3, reused directly)

providers/*.py  →  parser.py (shared text heuristics)
                →  app.intelligence.keyword_extractor.KeywordExtractor (Sprint 3, reused for skill extraction)
```

No provider imports another provider, `service.py`, `ranking.py`,
`deduplication.py`, or `filters.py` — every provider's only job is to turn
its vendor's JSON into a `DiscoveredJob`. Everything downstream of
discovery (dedup, filter, rank) operates purely on `DiscoveredJob`, never
on a provider's raw payload.

## 3. Provider system

`BaseJobProvider` (`providers/base.py`) is an ABC with:

- `provider_name` (property) — the registry key (`JobProviderName`, e.g. `"greenhouse"`)
- `source` (property) — the `JobSource` category stamped onto every job it returns
- `async fetch_jobs(query: JobSearchQuery) -> list[DiscoveredJob]`
- `async health_check() -> bool` (concrete default: an empty `fetch_jobs()` call)
- `async _get_json(url, params=None) -> Any` (protected shared helper: `httpx.AsyncClient` GET,
  wrapping `httpx.HTTPError` as `ProviderFetchError`)

### Why `JobProviderName` is separate from `JobSource`

`JobSource` (`app.models.enums`, Sprint 2) is the *category* a job's origin
falls under for display/filtering purposes (`LINKEDIN`, `INDEED`,
`GLASSDOOR`, `COMPANY_SITE`, ...). Greenhouse, Lever, Ashby, and Workable
are four distinct **integrations** that all report `JobSource.COMPANY_SITE`
(a company's own careers site, as opposed to a third-party aggregator) —
keying the provider registry by `JobSource` would collide the moment a
second provider shared a category. `JobProviderName` (defined in
`models.py`, not `providers/base.py`, to avoid a circular import with
`PollingRegistration`) is the registry key instead.

### Self-registration

Each provider decorates its class with `@register_provider(JobProviderName.X)`;
`providers/__init__.py` imports every built-in provider module so those
decorators run. `get_provider_class(name)` looks a provider up by name;
`available_providers()` lists every registered name.

### Each provider's API and field mapping

| Provider | Public API endpoint | Notable structured fields | Falls back to `parser.py` for |
|---|---|---|---|
| **Greenhouse** | `GET boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | title, location, HTML content, `absolute_url`, `updated_at` | remote/hybrid/onsite, experience level, salary, skills |
| **Lever** | `GET api.lever.co/v0/postings/{token}?mode=json` | `categories.commitment` (employment type), `workplaceType` (when present), `createdAt` (epoch ms) | remote/hybrid/onsite when `workplaceType` absent, experience level, salary, skills |
| **Ashby** | `GET api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true` | `isRemote` (bool), `employmentType`, structured `compensation.summaryComponents` | remote/hybrid/onsite when not remote, experience level, skills |
| **Workable** | `GET apply.workable.com/api/v1/widget/accounts/{account}` | `location.remote` (bool), `employment_type`, `published_on` | remote/hybrid/onsite when not flagged remote, experience level, skills |

### Adding LinkedIn or Indeed later

Adding a fifth provider requires exactly one new file:

```python
# app/job_discovery/providers/linkedin.py
from app.job_discovery.providers.base import BaseJobProvider, register_provider
from app.job_discovery.models import JobProviderName

@register_provider(JobProviderName.LINKEDIN)  # add to the JobProviderName enum in models.py
class LinkedInProvider(BaseJobProvider):
    @property
    def provider_name(self) -> JobProviderName:
        return JobProviderName.LINKEDIN

    @property
    def source(self) -> JobSource:
        return JobSource.LINKEDIN

    async def fetch_jobs(self, query): ...
    # implement against LinkedIn's official Talent/Jobs API — never scrape
    # linkedin.com directly; that is explicitly out of scope for this engine.
```

Then: add `LINKEDIN = "linkedin"` to `JobProviderName` (`models.py`), and
import the new module in `providers/__init__.py`. `JobDiscoveryService`,
`JobRankingEngine`, `JobDeduplicator`, and `JobFilter` are all unaffected —
none of them import a concrete provider class. The same recipe applies to
Indeed, using Indeed's Publisher/XML feed API. **Neither is implemented in
this sprint** because neither has a straightforward public, authenticated,
ToS-compliant JSON API available without a partner agreement — this
package deliberately never falls back to HTML scraping to fill that gap.

## 4. Job model

`DiscoveredJob` (`models.py`) is a provider-agnostic DTO — deliberately
named to avoid colliding with the persistence-layer `app.models.job.Job`
(a SQLAlchemy row), since a discovered job exists before it is ever
persisted. It carries every field the mission specifies: `title`,
`company`, `location`, `remote_type` (covers "remote"/"hybrid" via a single
`RemoteType` enum — see below), `salary_min`/`salary_max`/`currency`,
`employment_type`, `experience_level`, `description`, `requirements`,
`skills`, `source`, `source_url`, `posted_date`, `company_logo`, `metadata`.

**Design note — `remote_type` instead of separate `remote`/`hybrid` booleans:**
a `RemoteType` enum (`REMOTE`/`HYBRID`/`ONSITE`, reused from
`app.models.enums`, Sprint 2/3) makes "remote" and "hybrid" mutually
exclusive by construction, with `is_remote`/`is_hybrid`/`is_onsite`
convenience properties — two independent booleans could otherwise both be
`True`, an invalid state a caller would have to guard against everywhere.

## 5. Ranking algorithm

`JobRankingEngine.rank(job, profile, blueprint=None, *, preferences=None)`
returns a `JobRankingResult`: an overall 0-100 `score` plus one
`JobRankingExplanation` per factor (`factor`, `score`, `weight`, `detail`),
so a caller can see *why* a job scored the way it did.

| Factor | Weight | Source |
|---|---|---|
| Skills | 40% | Sprint 3's `SkillMatcher` (reused directly — `CareerProfile.skills` converted to `SkillInput`, matched against `job.skills`); + up to 10 bonus points for overlap with `ResumeBlueprint.recommended_skills` |
| Experience | 15% | Candidate's total years of experience (summed from `CareerProfile.experience` date ranges) mapped to an `ExperienceLevel`, compared by distance to `job.experience_level` |
| Location | 15% | `CareerProfile.preferences.application.preferred_locations` (or an explicit `JobSearchPreferences` override) vs. `job.location` |
| Remote preference | 10% | `...preferred_remote_types` vs. `job.remote_type` |
| Salary | 10% | `...observed_salary_min` (or an explicit `salary_floor` override) vs. `job.salary_max`/`salary_min` |
| Company preference | 10% | `JobSearchPreferences.preferred_companies`/`excluded_companies` only — see below |

Every factor returns a **neutral** score (not zero) when the relevant data
is missing on either side (e.g. no salary preference on file, or a job
that doesn't disclose salary) — an unknown should never be penalized as
badly as a known mismatch.

**Why company preference has no `CareerProfile` field:** Sprint 3.5's
`CareerProfile` has no notion of preferred/excluded companies today, so
this factor is sourced *only* from an explicit `JobSearchPreferences` the
caller supplies; without one, every job gets the same neutral 70 for this
factor. Adding a persisted preference in a future sprint only requires
wiring it into `ranking.py`'s `_score_company` fallback, the same way
location/remote/salary already fall back to `CareerProfile.preferences.application`.

`rank_all(jobs, ...)` scores every job and returns them sorted by score,
descending.

## 6. Deduplication

`JobDeduplicator.deduplicate(jobs) -> DeduplicationResult` catches
duplicates via two independent signals, either of which is sufficient to
drop a job:

1. **Exact URL match** (normalized: trimmed, lowercased) — the strongest
   signal, since the same posting always has the same canonical URL.
2. **Content hash** — a SHA-256 hash of the normalized
   `(title, company, location)` tuple (see `content_key`/`content_hash`),
   catching the same role posted at a different URL (e.g. cross-posted on
   two different ATS boards, or a re-opened requisition).

`DeduplicationResult.duplicates_removed` reports how many were dropped, for
observability.

## 7. Filters

`JobFilter.apply(jobs, criteria)` composes every set `JobFilterCriteria`
field with **AND** semantics (a job must satisfy every constraint that is
set; unset fields impose no constraint):

- `work_arrangement` — a single optional `RemoteType`, covering remote-only/hybrid/onsite
  as one field rather than three independent booleans (see §4's rationale)
- `experience_levels` — list of acceptable `ExperienceLevel`s
- `salary_min` — minimum acceptable salary (checked against `job.salary_max` if set, else `salary_min`)
- `countries` / `cities` — substring-matched against `job.location`
- `technologies` — matched against `job.skills` (any overlap passes)
- `keywords` — substring-matched against `job.title` + `job.description`

## 8. Scheduler architecture (no cron yet)

`JobDiscoveryScheduler` (`scheduler.py`) implements **registration and a
single-shot execution path only** — no interval timer, no cron, per the
mission's explicit instruction. It is deliberately decoupled from both
`JobDiscoveryService` and any concrete provider: `register()` takes an
injected async `fetch` callable (typically a provider's own `fetch_jobs`),
so `scheduler.py` has no import dependency on `service.py` and no
circular-import risk.

```python
scheduler = JobDiscoveryScheduler()
scheduler.register(JobProviderName.GREENHOUSE, JobSearchQuery(keywords=["python"]), 3600, provider.fetch_jobs)
jobs = await scheduler.run_once(JobProviderName.GREENHOUSE)  # executes immediately, once
```

**Wiring a real periodic backend later** (APScheduler, Celery beat, or a
plain cron entrypoint) only needs to call `run_once(provider_name)` on a
timer matching each `PollingRegistration.interval_seconds` — no change to
`JobDiscoveryScheduler`, `JobDiscoveryService`, or any provider is required.

## 9. Usage

```python
from app.job_discovery.models import JobFilterCriteria, JobSearchPreferences, JobSearchQuery
from app.job_discovery.providers.greenhouse import GreenhouseProvider
from app.job_discovery.providers.lever import LeverProvider
from app.job_discovery.service import JobDiscoveryService

service = JobDiscoveryService(providers=[
    GreenhouseProvider(board_token="acme"),
    LeverProvider(board_token="acme"),
])

results = await service.discover_ranked(
    JobSearchQuery(keywords=["backend"], limit=50),
    profile,             # CareerProfile, from CareerProfileService (Sprint 3.5)
    blueprint,           # ResumeBlueprint, from ResumePlanner (Sprint 3), optional
    criteria=JobFilterCriteria(work_arrangement=RemoteType.REMOTE, salary_min=120000.0),
    preferences=JobSearchPreferences(preferred_companies=["Acme Corp"]),
)
for result in results:
    print(result.job.title, result.score, [e.detail for e in result.explanations])
```

## 10. Future LinkedIn integration

LinkedIn has no public, unauthenticated job-search API — only the
Talent Solutions Partner APIs, which require a formal partnership
agreement and OAuth credentials. When (and if) such an agreement exists:

1. Add `LINKEDIN = "linkedin"` to `JobProviderName` (already present in
   `JobSource` from Sprint 2 — only the provider-registry enum needs it).
2. Add `app/job_discovery/providers/linkedin.py` implementing
   `BaseJobProvider`, authenticating via the partner API's OAuth flow
   (credentials sourced the same way Sprint 4's `LLMSettings` sources API
   keys — environment variables, never hardcoded).
3. Import it in `providers/__init__.py`.

No scraping of `linkedin.com`, no Selenium/Playwright, no headless browser
— this package's contract is "documented API or nothing," and that
contract does not change for LinkedIn.

## 11. Future Indeed integration

Indeed's public Job Search API was deprecated for most new integrations;
current access requires an Indeed Apply/XML partner feed agreement. The
integration path is identical in shape to LinkedIn's:
`app/job_discovery/providers/indeed.py` implementing `BaseJobProvider`,
registered under a new `JobProviderName.INDEED`, authenticated per
Indeed's partner program terms. Until such an agreement and credentials
exist, no Indeed provider ships in this codebase — again, never
substituted with scraping.

## 12. Testing strategy

Sprint 7 has no database dependency and no real network calls — every
provider test monkeypatches `_get_json` directly (mirroring
`tests/test_llm_providers.py`'s pattern of monkeypatching a provider's
`_send`), and one test (`test_get_json_wraps_httpx_errors` /
`test_get_json_returns_parsed_json_on_success`) fakes `httpx.AsyncClient`
itself to exercise the shared HTTP helper's both branches without a real
request. Coverage across `app/job_discovery/` is 100% (target: >95%):

- `test_job_discovery_models.py` — `DiscoveredJob` computed properties, model defaults
- `test_job_discovery_parser.py` — every shared text-heuristic function and edge case
- `test_job_discovery_providers.py` — registry, base contract, and all four providers' payload parsing (including malformed-entry skipping and fallback heuristics)
- `test_job_discovery_ranking.py` — every scoring factor, neutral-score fallbacks, bonuses/penalties, `rank_all` ordering
- `test_job_discovery_deduplication.py` — URL match, content-hash match, case/whitespace normalization
- `test_job_discovery_filters.py` — every filter criterion individually and composed with AND semantics
- `test_job_discovery_scheduler.py` — registration, unregistration, `run_once` execution and bookkeeping
- `test_job_discovery_service.py` — end-to-end discover → filter → rank pipeline, multi-provider aggregation, provider-failure tolerance
- `test_job_discovery_interfaces.py` — structural conformance of every concrete class to its `Protocol`
