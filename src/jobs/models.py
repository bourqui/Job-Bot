# src/jobs/models.py
"""
Pydantic models used to represent job records as they come from external sources
(e.g., APIs like Adzuna) before any transformation/normalization.

This module defines lightweight data containers with validation.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional


class JobRaw(BaseModel):
    """
    Minimal representation of a job posting as received from a source API.

    Notes
    - This model is intended for ingestion/IO boundaries. Keep it close to the
      source payload shape and avoid derived fields.
    - Validation is provided by Pydantic (e.g., `url` must be a valid URL).
    """

    # Unique identifier provided by the source system (e.g., Adzuna job ID)
    id: str

    # Human-readable job title
    title: str

    # Company name if available in the payload
    company: Optional[str] = None

    # Canonical job posting URL
    url: HttpUrl

    # Free-text location or region/city if provided
    location: Optional[str] = None

    # Minimum salary (numeric) if present in the source; currency not enforced here
    salary_min: Optional[float] = None

    # Maximum salary (numeric) if present in the source; currency not enforced here
    salary_max: Optional[float] = None

    # Name of the upstream provider/source (e.g., "adzuna")
    source: str