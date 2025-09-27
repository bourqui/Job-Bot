# src/jobs/cli.py
"""
Command-line interface for the job bot.

This module provides CLI commands to:
- Fetch new jobs from Adzuna and filter out already-processed ones
- Preview search terms from Google Sheets
- Debug Google Sheets connection and worksheet access
"""

from dotenv import load_dotenv
load_dotenv(override=True)  # automatically looks for a .env file in the project root

import json
import os
import typer
import datetime as dt

from rapidfuzz import process, fuzz
from datetime import date
from jobs.clients.adzuna import adzuna_search
from jobs.pipeline.normalize import normalize_adzuna
from jobs.pipeline.filter import filter_new
from jobs.io.sheets import (
    read_search_terms,
    read_processed_adzuna_ids,
    append_jobs_rows,
    read_contacts,
)

today = dt.date.today().isoformat()  # e.g. "2025-09-26"

# Optional evaluator (safe import)
try:
    from jobs.eval.llm import evaluate_jobs_simple
    HAS_EVAL = True
except Exception:
    HAS_EVAL = False



# Typer app instance for CLI commands
app = typer.Typer(help="Job fetcher")

@app.command()
def new_from_adzuna(
    query: str,
    limit: int = 50,
    score: bool = typer.Option(False, "--score", help="Use OpenAI to score jobs (needs OPENAI_API_KEY)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print rows but do not write to Sheets"),
    debug_ids: bool = typer.Option(False, "--debug-ids", help="Print fetched and already-seen IDs"),
    debug_llm: bool = typer.Option(False, "--debug-llm", help="Print LLM eval outputs"),
    contact_threshold: int = typer.Option(90, "--contact-threshold", help="Fuzzy match threshold 0-100"),
    debug_contacts: bool = typer.Option(False, "--debug-contacts", help="Show contact matches"),
):
    """
    Fetch Adzuna → normalize → filter out already-processed IDs → (optional) score → append to 'Jobs' sheet.
    No 'Source' column is written.
    """
    # --- creds ---
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        raise SystemExit("Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars (in .env).")
    
    typer.echo(f"Fetching up to {limit} jobs from Adzuna for query: {query!r}...")

    # --- fetch & normalize ---
    raw = adzuna_search(app_id, app_key, query, results_per_page=limit)
    jobs = normalize_adzuna(raw)  # list[dict] with standardized job data

    typer.echo(f"Fetched {len(jobs)} jobs.")

    # Load contacts once
    contacts = []
    try:
        contacts = read_contacts()
    except Exception as e:
        typer.echo(f"Contacts not available ({e}); continuing without connections.", err=True)

    # --- filter already processed ---
    processed = read_processed_adzuna_ids()  # set[str] from your 'Jobs' sheet ("Adzuna ID" column)
    fresh = filter_new(jobs, processed)
    evals = []
    eval_by_id = {}
    typer.echo(f"{len(fresh)} new jobs after filtering out {len(processed)} already processed.")

    if debug_llm and fresh:
        first_id = str(fresh[0].get("id", ""))
        print("debug_llm sample:", json.dumps(eval_by_id.get(first_id, {}), indent=2))

    if debug_ids: # used to debug the ids/ show how many are already in the sheet
        fetched_ids = [str(j.get("id", "")) for j in jobs]
        fresh_ids = [str(j.get("id", "")) for j in fresh]
        already = sorted(set(fetched_ids) & processed)
        typer.echo(json.dumps({
            "processed_count": len(processed),
            "fetched_ids": fetched_ids,
            "fresh_ids": fresh_ids,
            "already_in_sheet": already[:50],  # cap for sanity
        }, indent=2))

    # optional LLM scoring
    if score and fresh:
        typer.echo(f"Scoring {len(fresh)} jobs with LLM...")
        try:
            evals = evaluate_jobs_simple(fresh)  # returns list of {"id", "fit_score", "fit_notes"}
            eval_by_id = {str(e["id"]): e for e in evals}
        except Exception as ex:
            typer.echo(f"LLM eval failed: {ex}", err=True)
            evals = []
            eval_by_id = {}

    # safe debug (now eval_by_id is always defined)
    if debug_llm:
        import json as _json
        print("fresh ids:", [str(j.get("id", "")) for j in fresh])
        print("eval_by_id keys:", list(eval_by_id.keys()))
        print("evals sample:", _json.dumps(evals[:2], indent=2))
        print("fresh count:", len(fresh))
        print("evals count:", len(evals))
        print("eval_by_id keys:", list(eval_by_id.keys())[:10])

    # --- optional LLM scoring ---
    eval_by_id = {}
    if score:
        if not HAS_EVAL:
            typer.echo("LLM scoring requested but evaluator not available; skipping.", err=True)
        else:
            evals = evaluate_jobs_simple(fresh)
            eval_by_id = {e["id"]: e for e in evals}

    # --- build rows ---
    rows = []
    for j in fresh:
        e = eval_by_id.get(str(j.get("id", "")), {})

        # fuzzy match company -> contact
        contact_str = ""
        if contacts:
            match = find_best_contact(j.get("company", ""), contacts, score_cutoff=contact_threshold)
            if match:
                nm = str(match.get("Concatenated Name", "")).strip()
                pos = str(match.get("Position", "")).strip()
                co  = str(match.get("Company", "")).strip()
                url = str(match.get("URL", "")).strip()
                # Nice short string; include link if present
                contact_str = f"{nm} — {pos} at {co}"
                if url:
                    contact_str += f" ({url})"
                if debug_contacts:
                    typer.echo(f"[contacts] '{j.get('company','')}' -> '{co}' score={match.get('_match_score')} [{nm}]")

        rows.append({
            "Adzuna ID": j.get("id", ""),
            "Company": j.get("company", ""),
            "About company": e.get("company_summary", "") if score else "",
            "Job title": j.get("title", ""),
            "JD summary": e.get("job_summary", "") if score else "",
            "City": j.get("location", ""),
            "URL": j.get("url", ""),
            "Connection": contact_str,
            "Salary Min": j.get("salary_min", ""),
            "Salary Max": j.get("salary_max", ""),
            "AI score": e.get("fit_score", "") if score else "",
            "AI notes": e.get("fit_notes", "") if score else "",
            "Salary Estimated": j.get("salary_estimated", ""),
            "Posting created": j.get("created", ""),
            "Date pulled": today,
        })

    # --- write or preview ---
    if dry_run:
        typer.echo(json.dumps({
            "fetched": len(jobs),
            "fresh": len(fresh),
            "preview_rows": rows,
        }, indent=2))
        return

    appended = append_jobs_rows(rows)
    typer.echo(json.dumps({
        "fetched": len(jobs),
        "fresh": len(fresh),
        "appended": appended
    }, indent=2))

@app.command()
def terms_preview():
    """
    Quick check: show first 5 search terms from your sheet.
    
    Useful for verifying that Google Sheets integration is working
    and that search terms are being read correctly.
    """
    # Read search terms from Google Sheets
    terms = read_search_terms()
    # Show just the first 5 terms as a preview
    print(json.dumps(terms[:5], indent=2))

@app.command()
def sheets_debug():
    """
    List worksheet titles and IDs via gspread to verify private access.
    
    This helps debug Google Sheets connection issues by showing:
    - Whether authentication is working
    - What worksheets are available
    - Their internal IDs (useful for debugging)
    """
    import gspread
    from jobs.io.sheets import SHEET_ID_MAIN
    
    # Connect to Google Sheets using service account credentials
    gc = gspread.service_account(filename="service_account_jobbot.json")
    sh = gc.open_by_key(SHEET_ID_MAIN)
    
    # List all worksheets in the spreadsheet
    for ws in sh.worksheets():
        print(f"{ws.title}  gid={ws.id}")

@app.command()
def jobs_headers():
    """
    Debug: show the first row of the 'Jobs' worksheet so we can confirm headers.
    """
    import gspread
    from jobs.io.sheets import SHEET_ID_MAIN, GID_JOBS

    gc = gspread.service_account(filename="service_account_jobbot.json")
    sh = gc.open_by_key(SHEET_ID_MAIN)
    ws = next((ws for ws in sh.worksheets() if ws.id == GID_JOBS), None)
    if ws is None:
        raise ValueError(f"No worksheet with gid={GID_JOBS}")

    header_row = ws.row_values(1)  # row 1 as a list of strings
    print("Headers in Jobs tab:", header_row)

@app.command()
def llm_test():
    """
    LLM smoke test: run evaluator on a single fake job (no network, no Sheets).
    """
    from jobs.eval.llm import evaluate_jobs_simple
    fake_job = {
        "id": "test-123",
        "title": "Senior Data Engineer",
        "company": "Fictional Energy Co",
        "location": "San Francisco, CA",
        "url": "https://example.com/job/123",
        "salary_min": 150000,
        "salary_max": 180000,
        "salary_estimated": "0",
        "created": "2025-09-20",
        # optional: "description": "…" if you decide to pass it through normalize()
    }
    res = evaluate_jobs_simple([fake_job])
    print(res)

# simple normalizer to improve matching
def _clean_co(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # strip common company suffixes
    for suf in (" inc.", " inc", ", inc", " llc", ", llc", " ltd.", " ltd", " corp.", " corp", " corporation", " company", " co.", " co"):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    return s

def find_best_contact(job_company: str, contacts: list[dict], score_cutoff: int = 90) -> dict | None:
    """
    Return the best matching contact row or None.
    Matches job_company against contacts' company names using RapidFuzz.
    """
    cand = _clean_co(job_company)
    if not cand or not contacts:
        return None

    # Build parallel arrays to avoid putting dicts in RapidFuzz choices
    names: list[str] = []
    rows: list[dict] = []
    for c in contacts:
        co = _clean_co(str(c.get("Company", "")))
        if co:
            names.append(co)
            rows.append(c)

    if not names:
        return None

    best = process.extractOne(
        cand,
        names,                # only strings here
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff
    )
    if not best:
        return None

    matched_name, score, idx = best
    row = rows[idx]
    row["_match_score"] = score
    return row

if __name__ == "__main__":
    app()