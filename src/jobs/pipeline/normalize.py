# src/jobs/pipeline/normalize.py
from typing import Iterable, List
from jobs.models import JobRaw

def normalize_adzuna(results_json: dict) -> List[JobRaw]:
    out: List[JobRaw] = []
    for x in results_json.get("results", []):
        out.append(JobRaw(
            id=str(x.get("id")),
            title=x.get("title", "").strip(),
            company=(x.get("company") or {}).get("display_name"),
            url=x["redirect_url"],
            location=(x.get("location") or {}).get("display_name"),
            salary_min=x.get("salary_min"),
            salary_max=x.get("salary_max"),
            source="adzuna",
        ))
    return out