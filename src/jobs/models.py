# src/jobs/models.py
"""
Lightweight typed dictionaries to represent job records as they come from
external sources (e.g., APIs like Adzuna) before any transformation/normalization.

Everything is a plain dict with type hints.
"""

from typing import Optional, TypedDict


class JobRaw(TypedDict, total=False):
    """
    Minimal representation of a job posting as received from a source API.

    Notes:
    - `TypedDict` provides type hints (what keys exist, and their value types).
    - At runtime, this is just a dict: {"id": "123", "title": "Data Engineer", ...}.
    - No validation is enforced (unlike Pydantic). If you want validation later,
      you could reintroduce Pydantic models.
    """

    # Unique identifier provided by the source system (e.g., Adzuna job ID)
    id: str

    # Human-readable job title
    title: str

    # Company name if available in the payload
    company: Optional[str]

    # Canonical job posting URL
    url: str  # plain string, not validated as URL

    # Free-text location or region/city if provided
    location: Optional[str]

    # Minimum salary (numeric) if present in the source
    salary_min: Optional[float]

    # Maximum salary (numeric) if present in the source
    salary_max: Optional[float]

    # Name of the upstream provider/source (e.g., "adzuna")
    source: str