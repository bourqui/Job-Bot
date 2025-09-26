# src/jobs/pipeline/normalize.py
"""
Convert Adzuna's raw API response into our standardized JobRaw models.

This module handles the messy details of mapping Adzuna's JSON structure
to our clean, consistent data model.
"""
from typing import Iterable, List
from jobs.models import JobRaw

def normalize_adzuna(results_json: dict) -> List[JobRaw]:
    """
    Transform Adzuna API response into a list of JobRaw objects.
    
    Adzuna returns nested JSON with inconsistent field names and structures.
    This function flattens and standardizes everything into our JobRaw model.
    """
    out: List[JobRaw] = []
    
    # Process each job result from Adzuna's "results" array
    for x in results_json.get("results", []):
        out.append(JobRaw(
            # Convert Adzuna's numeric ID to string (our model expects string)
            id=str(x.get("id")),
            
            # Clean up job title - remove extra whitespace
            title=x.get("title", "").strip(),
            
            # Extract company name from nested "company" object
            # Adzuna puts company info in company.display_name
            company=(x.get("company") or {}).get("display_name"),
            
            # Use Adzuna's redirect URL (this goes to their site, then to the actual job)
            url=x["redirect_url"],
            
            # Extract location from nested "location" object
            # Adzuna puts location info in location.display_name
            location=(x.get("location") or {}).get("display_name"),
            
            # Salary fields come directly from Adzuna (already numeric)
            salary_min=x.get("salary_min"),
            salary_max=x.get("salary_max"),
            
            # Mark this job as coming from Adzuna (for tracking/filtering)
            source="adzuna",
        ))
    return out