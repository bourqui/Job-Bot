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

from jobs.clients.adzuna import adzuna_search
from jobs.pipeline.normalize import normalize_adzuna
from jobs.pipeline.filter import filter_new
from jobs.io.sheets import read_search_terms, read_processed_adzuna_ids

# Typer app instance for CLI commands
app = typer.Typer(help="Job fetcher")

@app.command()
def new_from_adzuna(query: str, limit: int = 50):
    """
    Fetch Adzuna → normalize → filter out already-processed IDs → print JSON.
    
    This is the main workflow: get fresh job postings that haven't been processed yet.
    """
    # Get Adzuna API credentials from environment variables
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        raise SystemExit("Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars.")

    # Step 1: Fetch raw job data from Adzuna API
    raw = adzuna_search(app_id, app_key, query, results_per_page=limit)
    
    # Step 2: Convert Adzuna's raw JSON into our standardized JobRaw models
    jobs = normalize_adzuna(raw)
    
    # Step 3: Get list of job IDs we've already processed (from Google Sheets)
    processed = read_processed_adzuna_ids()
    
    # Step 4: Filter out jobs we've already seen, keep only fresh ones
    fresh = filter_new(jobs, processed)

    # Step 5: Output results as pretty JSON (temporary - will write to CSV/DB later)
    print(json.dumps(fresh, indent=2))

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

if __name__ == "__main__":
    app()