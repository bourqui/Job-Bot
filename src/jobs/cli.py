# src/jobs/cli.py
import json
import os
import typer
from jobs.clients.adzuna import AdzunaClient
from jobs.pipeline.normalize import normalize_adzuna
from jobs.pipeline.filter import filter_new
from jobs.io.sheets import read_search_terms, read_processed_adzuna_ids

app = typer.Typer(help="Job fetcher")

@app.command()
def new_from_adzuna(query: str, limit: int = 50):
    """
    Fetch Adzuna → normalize → filter out already-processed IDs → print JSON.
    """
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        raise SystemExit("Set ADZUNA_APP_ID and ADZUNA_APP_KEY env vars.")

    client = AdzunaClient(app_id, app_key)
    raw = client.search(query=query, results_per_page=limit)
    jobs = normalize_adzuna(raw)
    processed = read_processed_adzuna_ids()
    fresh = filter_new(jobs, processed)

    # Pretty print for now; later we’ll write CSV/DB.
    print(json.dumps([j.model_dump() for j in fresh], indent=2))

@app.command()
def terms_preview():
    """
    Quick check: show first 5 search terms from your sheet.
    """
    terms = read_search_terms()
    print(json.dumps(terms[:5], indent=2))

@app.command()
def sheets-debug():
    """
    List worksheet titles and IDs via gspread to verify private access.
    """
    import gspread
    from jobs.io.sheets import SHEET_ID_MAIN
    gc = gspread.service_account(filename="service_account_jobbot.json")
    sh = gc.open_by_key(SHEET_ID_MAIN)
    for ws in sh.worksheets():
        print(f"{ws.title}  gid={ws.id}")

if __name__ == "__main__":
    app()