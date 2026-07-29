"""Filters a list of `DiscoveredJob` against a `JobFilterCriteria`.

Every criterion is optional (an empty list / `None` means "no constraint");
a job passes only if it satisfies every criterion that *is* set — filters
compose with AND semantics, never OR.
"""

from app.job_discovery.models import DiscoveredJob, JobFilterCriteria


def _normalize(value: str) -> str:
    return value.strip().lower()


class JobFilter:
    def apply(self, jobs: list[DiscoveredJob], criteria: JobFilterCriteria) -> list[DiscoveredJob]:
        return [job for job in jobs if self._matches(job, criteria)]

    def _matches(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        return (
            self._matches_work_arrangement(job, criteria)
            and self._matches_experience(job, criteria)
            and self._matches_salary(job, criteria)
            and self._matches_location(job, criteria.countries)
            and self._matches_location(job, criteria.cities)
            and self._matches_technologies(job, criteria)
            and self._matches_keywords(job, criteria)
        )

    def _matches_work_arrangement(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        if criteria.work_arrangement is None:
            return True
        return job.remote_type is criteria.work_arrangement

    def _matches_experience(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        if not criteria.experience_levels:
            return True
        return job.experience_level in criteria.experience_levels

    def _matches_salary(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        if criteria.salary_min is None:
            return True
        job_salary = job.salary_max if job.salary_max is not None else job.salary_min
        if job_salary is None:
            return False
        return job_salary >= criteria.salary_min

    def _matches_location(self, job: DiscoveredJob, needles: list[str]) -> bool:
        if not needles:
            return True
        if not job.location:
            return False
        haystack = _normalize(job.location)
        return any(_normalize(needle) in haystack for needle in needles)

    def _matches_technologies(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        if not criteria.technologies:
            return True
        job_skills = {_normalize(skill) for skill in job.skills}
        wanted = {_normalize(tech) for tech in criteria.technologies}
        return bool(job_skills & wanted)

    def _matches_keywords(self, job: DiscoveredJob, criteria: JobFilterCriteria) -> bool:
        if not criteria.keywords:
            return True
        haystack = _normalize(f"{job.title} {job.description}")
        return any(_normalize(keyword) in haystack for keyword in criteria.keywords)
