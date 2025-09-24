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

# ------------------------------
# Function: read_search_terms
# - Pulls the search_terms tab as a DataFrame
# - Keeps only the columns you care about (what_phrase, title_only)
# - Drops empty rows
# - Returns it as a list of dicts, e.g.:
#   [{"what_phrase": "data engineer", "title_only": ""}, ...]
# ------------------------------
def read_search_terms() -> List[dict]:
    url = csv_export_url(SHEET_ID_MAIN, GID_SEARCH_TERMS)
    df = pd.read_csv(url)
    needed = [c for c in ["what_phrase", "title_only"] if c in df.columns]
    return df[needed].dropna(how="all").to_dict(orient="records")

# ------------------------------
# Function: read_processed_adzuna_ids
# - Pulls the Jobs tab
# - Looks for a column called "Adzuna ID"
# - Returns a Python set of IDs (fast to check membership later, e.g. if job_id in processed_ids)
# ------------------------------
def read_processed_adzuna_ids() -> Set[str]:
    url = csv_export_url(SHEET_ID_MAIN, GID_JOBS)
    df = pd.read_csv(url)
    col = "Adzuna ID"
    if col not in df.columns:
        return set()
    return set(df[col].dropna().astype(str).tolist())