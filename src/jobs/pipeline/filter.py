# src/jobs/pipeline/filter.py
from typing import Iterable, List, Set
from jobs.models import JobRaw

def filter_new(jobs: Iterable[JobRaw], processed_ids: Set[str]) -> List[JobRaw]:
    """
    Keep only jobs whose id is NOT in processed_ids.
    """
    return [j for j in jobs if j.id not in processed_ids]