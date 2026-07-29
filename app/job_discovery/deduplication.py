"""Deduplicates `DiscoveredJob`s fetched from multiple providers.

The same posting frequently appears more than once — a company might list
on both Greenhouse and its own Lever board, or a provider might return the
same job twice across paginated pages. Two independent signals catch this:
an exact-URL match (the strongest signal — the same posting always has the
same canonical URL) and a normalized content hash of
`(title, company, location)` (catches the same role re-posted at a
different URL, e.g. a re-opened requisition).
"""

import hashlib

from app.job_discovery.models import DeduplicationResult, DiscoveredJob


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def content_key(job: DiscoveredJob) -> str:
    """The normalized `(title, company, location)` tuple used for hashing."""
    return "|".join([_normalize(job.title), _normalize(job.company), _normalize(job.location)])


def content_hash(job: DiscoveredJob) -> str:
    """A stable SHA-256 hash of `content_key(job)`, used as the dedup identity."""
    return hashlib.sha256(content_key(job).encode("utf-8")).hexdigest()


class JobDeduplicator:
    def deduplicate(self, jobs: list[DiscoveredJob]) -> DeduplicationResult:
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        unique: list[DiscoveredJob] = []
        duplicates_removed = 0

        for job in jobs:
            url_key = _normalize(job.source_url)
            hash_key = content_hash(job)
            if url_key in seen_urls or hash_key in seen_hashes:
                duplicates_removed += 1
                continue
            seen_urls.add(url_key)
            seen_hashes.add(hash_key)
            unique.append(job)

        return DeduplicationResult(unique_jobs=unique, duplicates_removed=duplicates_removed)
