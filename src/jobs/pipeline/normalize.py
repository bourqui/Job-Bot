# src/jobs/pipeline/normalize.py
"""
Convert Adzuna's raw API response into our standardized JobRaw models.

This module handles the messy details of mapping Adzuna's JSON structure
to our clean, consistent data model.
"""
from typing import Iterable, List
from jobs.models import JobRaw

def _created_ymd(raw: str | None) -> str:
    # Adzuna format: "2025-09-26T07:20:13Z"
    if not raw:
        return ""
    # keep it simple and robust on py3.10
    try:
        return raw.split("T", 1)[0]  # "YYYY-MM-DD"
    except Exception:
        return ""


def normalize_adzuna(results_json: dict) -> List[JobRaw]:
    """
    Transform Adzuna API response into a list of JobRaw objects.
    
    Adzuna returns nested JSON with inconsistent field names and structures.
    This function flattens and standardizes everything into our JobRaw model.
    """
    out: List[JobRaw] = []
    
    # Process each job result from Adzuna's "results" array
    for x in results_json.get("results", []):
        out.append({
            "id": str(x.get("id")),
            "title": (x.get("title") or "").strip(),
            "company": (x.get("company") or {}).get("display_name"),
            "url": x.get("redirect_url", ""),
            "location": (x.get("location") or {}).get("display_name"),
            "salary_min": x.get("salary_min"),
            "salary_max": x.get("salary_max"),
            # NEW:
            "salary_estimated": x.get("salary_is_predicted"),  # "1" if predicted
            "created": _created_ymd(x.get("created")),  # e.g. "2025-09-24"
        })
    return out