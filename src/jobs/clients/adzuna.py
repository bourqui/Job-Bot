# src/jobs/clients/adzuna.py

"""
Plain-function client for Adzuna's Jobs API (no classes, no decorators).

Design goals (ELI5):
- Keep *all* HTTP details here so the rest of your code never worries about URLs, timeouts, retries.
- Expose simple functions you can call from anywhere (e.g., your CLI).
- Return raw JSON (dict) from Adzuna; do normalization elsewhere.
"""

from __future__ import annotations
from typing import Dict, Generator, Iterable, Optional
import urllib.parse
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type


# ---- Internal helpers ---------------------------------------------------------

def _base_url(country: str, page: int) -> str:
    """
    Build the Adzuna search URL for a country + page number.
    Adzuna paginates with integer pages: /search/1, /search/2, ...
    """
    return f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def _default_headers() -> Dict[str, str]:
    """
    Minimal, explicit headers. (Some APIs behave better when a UA is set.)
    """
    return {"User-Agent": "job-bot/0.1 (+https://example.com)"}


@retry(
    # If the request fails, wait 1s, then 2s, 4s, … up to 16s; try at most 5 times.
    wait=wait_exponential(min=1, max=16),
    stop=stop_after_attempt(5),
    # Only retry for network/HTTP errors raised by httpx
    retry=retry_if_exception_type(httpx.HTTPError),
)
def _get_json(url: str, params: Dict[str, str]) -> Dict:
    """
    Do one HTTP GET with sensible timeouts + retry logic.
    We keep this tiny so it's easy to test and reason about.
    """
    # NOTE: httpx handles SSL and uses certifi's CA bundle (reliable cross-platform).
    # If Adzuna is down or flaky, tenacity will retry this call.
    with httpx.Client(timeout=20, headers=_default_headers()) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()  # raises httpx.HTTPStatusError for 4xx/5xx
        return resp.json()


# ---- Public API (call these from your CLI/pipeline) ---------------------------

def adzuna_search(
    app_id: str,
    app_key: str,
    query: str,
    *,
    country: str = "us",
    page: int = 1,
    results_per_page: int = 50,
    where: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict:
    """
    Fetch ONE page of search results from Adzuna and return the raw JSON (dict).

    Arguments (ELI5):
    - app_id/app_key: your Adzuna credentials.
    - query: what to search for, e.g. "data engineer".
    - country: ISO-ish two-letter code Adzuna expects ("us", "gb", etc.).
    - page: which results page to fetch (1-based).
    - results_per_page: how many results per page (Adzuna supports a cap).
    - where: optional location filter (e.g., "San Francisco, CA").
    - category: optional Adzuna category code (e.g., "it-jobs").

    Returns:
    - The full JSON response as a dict (keys like "count", "results", ...).
      You can pass this to your normalize function elsewhere.
    """
    url = _base_url(country=country, page=page)

    # Build query params Adzuna expects.
    # (urllib.parse is just to be explicit we're passing *text*, not bytes)
    params: Dict[str, str] = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "results_per_page": str(results_per_page),
    }
    if where:
        params["where"] = where
    if category:
        params["category"] = category

    # One network call; may be retried by tenacity if transient failure occurs.
    return _get_json(url, params)


def adzuna_iter_search(
    app_id: str,
    app_key: str,
    query: str,
    *,
    country: str = "us",
    start_page: int = 1,
    max_pages: int = 1,
    results_per_page: int = 50,
    where: Optional[str] = None,
    category: Optional[str] = None,
) -> Generator[Dict, None, None]:
    """
    Convenience generator to iterate multiple pages without classes.

    Yields:
    - Each page's raw JSON dict (so you can stream/process per page and stop early).

    Why a generator?
    - You can process page-by-page (e.g., filter out already-processed IDs)
      without loading everything into memory.
    """
    page = start_page
    pages_returned = 0

    while pages_returned < max_pages:
        data = adzuna_search(
            app_id=app_id,
            app_key=app_key,
            query=query,
            country=country,
            page=page,
            results_per_page=results_per_page,
            where=where,
            category=category,
        )

        yield data

        # Defensive stop: if API returns no results, don’t keep paging.
        results = data.get("results") or []
        if not results:
            break

        page += 1
        pages_returned += 1