# src/jobs/io/sheets.py

# This "future import" just makes type hints a bit more flexible across Python versions.
from __future__ import annotations

import pandas as pd
from typing import List, Set  # <-- lets us be explicit about what types functions return

# ------------------------------
# Utility function to build the "CSV export" URL for a Google Sheet.
# Every Google Sheet has:
#   - a document ID (the long string in the URL after /d/)
#   - a gid (the internal numeric ID of a specific tab/worksheet in that sheet)
# When you hit ".../export?format=csv&gid=<gid>" you get the tab as raw CSV.
# ------------------------------
def csv_export_url(sheet_id: str, gid: str | int) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

# ------------------------------
# These constants are just the "addresses" of your sheet + tabs.
# - SHEET_ID_MAIN is the whole Google Sheet document.
# - GID_SEARCH_TERMS is the numeric ID for the tab that holds your search phrases.
# - GID_JOBS is the numeric ID for the tab that holds job records (with Adzuna IDs).
# ------------------------------
SHEET_ID_MAIN = "1-bG7_sqsq83OSnMOatR9CEue0pnEVEePgq5Lyctn0FI"
GID_SEARCH_TERMS = "806664812"  # "search_terms for API"
GID_JOBS = "0"                  # "Jobs" (has "Adzuna ID")

def _read_csv_via_httpx(url: str) -> pd.DataFrame:
    # httpx uses certifi cert bundle; avoids macOS urllib cert issues
    with httpx.Client(timeout=20) as client:
        r = client.get(url)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text))

def read_search_terms() -> List[dict]:
    url = csv_export_url(SHEET_ID_MAIN, GID_SEARCH_TERMS)
    df = _read_csv_via_httpx(url)
    needed = [c for c in ["what_phrase", "title_only"] if c in df.columns]
    return df[needed].dropna(how="all").to_dict(orient="records")

def read_processed_adzuna_ids() -> Set[str]:
    url = csv_export_url(SHEET_ID_MAIN, GID_JOBS)
    df = _read_csv_via_httpx(url)
    col = "Adzuna ID"
    if col not in df.columns:
        return set()
    return set(df[col].dropna().astype(str).tolist())