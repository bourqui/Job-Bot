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

from datetime import date
from jobs.clients.adzuna import adzuna_search
from jobs.pipeline.normalize import normalize_adzuna
from jobs.pipeline.filter import filter_new
from jobs.io.sheets import read_search_terms, read_processed_adzuna_ids, append_jobs_rows

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
@app.command()
def new_from_adzuna(
    query: str,
    limit: int = 50,
    score: bool = typer.Option(False, "--score", help="Use OpenAI to score jobs (needs OPENAI_API_KEY)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print rows but do not write to Sheets"),
    debug_ids: bool = typer.Option(False, "--debug-ids", help="Print fetched and already-seen IDs"),
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

    # --- fetch & normalize ---
    raw = adzuna_search(app_id, app_key, query, results_per_page=limit)
    jobs = normalize_adzuna(raw)  # list[dict] with keys: id,title,company,location,url,salary_min,salary_max,source

    # --- filter already processed ---
    processed = read_processed_adzuna_ids()  # set[str] from your 'Jobs' sheet ("Adzuna ID" column)
    fresh = filter_new(jobs, processed)

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

    # --- optional LLM scoring ---
    eval_by_id = {}
    if score:
        if not HAS_EVAL:
            typer.echo("LLM scoring requested but evaluator not available; skipping.", err=True)
        else:
            evals = evaluate_jobs_simple(fresh)
            eval_by_id = {e["id"]: e for e in evals}

    # --- build rows (keys must match sheet headers) ---
    rows = []
    for j in fresh:
        e = eval_by_id.get(j.get("id"), {})
        rows.append({
            "Adzuna ID": j.get("id", ""),
            "Job title": j.get("title", ""),
            "Company": j.get("company", ""),
            "City": j.get("location", ""),
            "URL": j.get("url", ""),
            # include these only if your sheet has these columns in the header row:
            "Salary Min": j.get("salary_min", ""),
            "Salary Max": j.get("salary_max", ""),
            # no "Source" column anymore
            "AI score": e.get("fit_score", "") if score else "",
            "AI Notes": e.get("fit_notes", "") if score else "",
            
            "Salary Estimated": j.get("salary_estimated", ""),
            "Posting created": j.get("created", ""),
            "Date pulled": today

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

if __name__ == "__main__":
    app()