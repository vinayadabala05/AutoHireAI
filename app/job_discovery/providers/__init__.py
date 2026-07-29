"""Concrete job board provider implementations.

Importing this package registers every built-in provider with the registry
in `providers/base.py` via the `@register_provider` decorator on each
class. Adding LinkedIn or Indeed later means adding one new module here
(subclassing `BaseJobProvider`, decorated with `@register_provider`) and
one import line below — no other module in `app.job_discovery` changes.
"""

from app.job_discovery.models import JobProviderName
from app.job_discovery.providers.ashby import AshbyProvider
from app.job_discovery.providers.base import BaseJobProvider
from app.job_discovery.providers.greenhouse import GreenhouseProvider
from app.job_discovery.providers.lever import LeverProvider
from app.job_discovery.providers.workable import WorkableProvider

__all__ = [
    "AshbyProvider",
    "BaseJobProvider",
    "GreenhouseProvider",
    "JobProviderName",
    "LeverProvider",
    "WorkableProvider",
]
