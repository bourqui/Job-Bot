# src/jobs/io/sheets.py
from __future__ import annotations
import io
import httpx
import pandas as pd
from typing import List, Set
import datetime as dt

try:
    import gspread
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

def csv_export_url(sheet_id: str, gid: str | int) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

SHEET_ID_MAIN = "1-bG7_sqsq83OSnMOatR9CEue0pnEVEePgq5Lyctn0FI"
GID_SEARCH_TERMS = 806664812  # ints are nicer when using gspread (worksheet.id)
GID_JOBS = 0

def _read_csv_via_httpx(url: str) -> pd.DataFrame:
    with httpx.Client(timeout=20) as client:
        r = client.get(url)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text))

def _read_df_with_gspread(sheet_id: str, gid: int) -> pd.DataFrame:
    if not HAS_GSPREAD:
        raise RuntimeError("gspread not installed. `pip install gspread google-auth`")
    gc = gspread.service_account(filename="service_account_jobbot.json")
    sh = gc.open_by_key(sheet_id)
    ws = next((ws for ws in sh.worksheets() if ws.id == gid), None)
    if ws is None:
        raise ValueError(f"No worksheet with gid={gid}")
    rows = ws.get_all_records()  # list[dict]
    return pd.DataFrame(rows)

def _read_tab(sheet_id: str, gid: int) -> pd.DataFrame:
    # Try public CSV first; if 401 and gspread available, use service account
    url = csv_export_url(sheet_id, gid)
    try:
        return _read_csv_via_httpx(url)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401 and HAS_GSPREAD:
            return _read_df_with_gspread(sheet_id, gid)
        raise

def read_search_terms() -> List[dict]:
    df = _read_tab(SHEET_ID_MAIN, GID_SEARCH_TERMS)
    needed = [c for c in ["what_phrase", "title_only"] if c in df.columns]
    return df[needed].dropna(how="all").to_dict(orient="records")

def read_processed_adzuna_ids() -> Set[str]:
    df = _read_tab(SHEET_ID_MAIN, GID_JOBS)
    col = "Adzuna ID"
    if col not in df.columns:
        return set()
    return set(df[col].dropna().astype(str).tolist())

def append_jobs_rows(rows: list[dict]) -> int:
    """
    Append a list of dicts to the 'Jobs' worksheet.
    - Dict keys must match the sheet's header row exactly.
    - Raises if worksheet 'Jobs' is missing or required headers are missing.
    - Returns number of rows appended.
    """
    if not rows:
        return 0
    if not HAS_GSPREAD:
        raise RuntimeError("gspread not installed. `pip install gspread google-auth`")

    # 1) Open spreadsheet & the *exact* worksheet title (no fallback).
    gc = gspread.service_account(filename="service_account_jobbot.json")
    sh = gc.open_by_key(SHEET_ID_MAIN)
    try:
        ws = sh.worksheet("Jobs")  # <-- exact title; will raise if not found
    except gspread.WorksheetNotFound as e:
        raise RuntimeError("Worksheet 'Jobs' not found. Fix the tab name or code.") from e

    # 2) Read header row and validate expected columns exist.
    headers = ws.row_values(1)  # first row as list of header strings
    if not headers:
        raise RuntimeError("Header row is empty in 'Jobs' worksheet.")

    # Minimal required columns (change if your sheet differs).
    required = {"Adzuna ID", "Title", "Company", "Location", "URL", "Source"}
    missing = sorted(required - set(headers))
    if missing:
        raise RuntimeError(f"'Jobs' is missing required header(s): {', '.join(missing)}")

    header_index = {h: i for i, h in enumerate(headers)}  # 0-based

    # 3) Normalize incoming dicts to header order; auto-fill Added At if present.
    out = []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    has_added_at = "Added At" in header_index
    for r in rows:
        if has_added_at and "Added At" not in r:
            r = {**r, "Added At": now}
        out.append([r.get(h, "") for h in headers])

    # 4) Append at the bottom. This does NOT overwrite existing rows.
    #    value_input_option="RAW" keeps values as-is; use "USER_ENTERED" if you want Sheets to parse.
    ws.append_rows(out, value_input_option="RAW")
    return len(out)