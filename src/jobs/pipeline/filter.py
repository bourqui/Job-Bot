# src/jobs/pipeline/filter.py
from typing import Iterable, List, Set, Dict

def filter_new(jobs: Iterable[Dict], processed_ids: Set[str]) -> List[Dict]:
    """
    Keep only jobs whose 'id' (as a string) is NOT in processed_ids.
    Jobs are plain dicts.
    """
    out: List[Dict] = []
    for j in jobs:
        jid = j.get("id")
        if jid is None:
            continue  # if no id, skip
        if str(jid) not in processed_ids:
            out.append(j)
    return out