"""Job filtering: skills, experience, location, employment type, remote
preference, salary, company block/allow lists, keywords, and arbitrary
user-defined rules.

Reuses Sprint 7's `JobFilter`/`JobFilterCriteria` directly for every
criterion it already supports (remote/hybrid/onsite, experience level,
salary, country/city, technologies/"skills", keywords) rather than a
second filtering implementation — this module only adds what Sprint 7's
job-discovery-scoped filter has no reason to know about: a company block/
allow list, a minimum-skill-overlap check against the *candidate's own*
`CareerProfile`, and fully custom predicate rules.
"""

from collections.abc import Callable

from app.career_profile.models import CareerProfile
from app.job_discovery.filters import JobFilter
from app.job_discovery.models import DiscoveredJob
from app.job_monitoring.models import MonitoringFilterCriteria

CustomRule = Callable[[DiscoveredJob], bool]


class MonitoringJobFilter:
    def __init__(self, custom_rules: list[CustomRule] | None = None) -> None:
        self._base_filter = JobFilter()
        self._custom_rules = list(custom_rules or [])

    def matches(
        self,
        job: DiscoveredJob,
        criteria: MonitoringFilterCriteria,
        profile: CareerProfile | None = None,
    ) -> bool:
        if not self._base_filter.apply([job], criteria.base):
            return False
        if not self._passes_company_lists(job, criteria):
            return False
        if not self._passes_skill_overlap(job, criteria, profile):
            return False
        return all(rule(job) for rule in self._custom_rules)

    def _passes_company_lists(self, job: DiscoveredJob, criteria: MonitoringFilterCriteria) -> bool:
        company_norm = job.company.strip().lower()
        if criteria.company_blacklist:
            blacklist = {name.strip().lower() for name in criteria.company_blacklist}
            if company_norm in blacklist:
                return False
        if criteria.company_whitelist:
            whitelist = {name.strip().lower() for name in criteria.company_whitelist}
            if company_norm not in whitelist:
                return False
        return True

    def _passes_skill_overlap(
        self,
        job: DiscoveredJob,
        criteria: MonitoringFilterCriteria,
        profile: CareerProfile | None,
    ) -> bool:
        if criteria.min_skill_overlap <= 0 or profile is None:
            return True
        job_skills = {skill.lower() for skill in job.skills}
        profile_skills = {skill.name.lower() for skill in profile.skills}
        return len(job_skills & profile_skills) >= criteria.min_skill_overlap
