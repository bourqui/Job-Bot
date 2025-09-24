# src/jobs/clients/adzuna.py
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

class AdzunaClient:
    """
    Minimal client to call Adzuna search. Keeps retries + timeouts sane.
    """
    def __init__(self, app_id: str, app_key: str, country: str = "us"):
        # Base endpoint for Adzuna job search (page 1)
        self.base = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        self.app_id = app_id
        self.app_key = app_key

    # Retry on transient HTTP client errors with exponential backoff (1s -> 2s -> ... up to 16s)
    @retry(wait=wait_exponential(min=1, max=16),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type(httpx.HTTPError))
    def search(self, query: str, results_per_page: int = 50) -> dict:
        # Conservative network timeout for the entire request
        with httpx.Client(timeout=20) as client:
            r = client.get(
                self.base,
                params={
                    # Required authentication
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    # Search query and pagination size
                    "what": query,
                    "results_per_page": results_per_page,
                },
            )
            # Raise for non-2xx responses so retries / callers can handle errors
            r.raise_for_status()
            return r.json()