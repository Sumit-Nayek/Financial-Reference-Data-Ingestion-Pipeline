# sec_keyterms/http_client.py
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from sec_keyterms.config import SEC_USER_AGENT


class RateLimitedSECClient:
    """
    HTTP Client adhering to SEC EDGAR fair-access rules:
    - Rate limit: max 10 requests per second.
    - Custom User-Agent format: 'SampleName UserContact@domain.com'.
    - Automatic exponential backoff for 429, 500, 502, 503, 504 status codes.
    """

    def __init__(self, user_agent: str = SEC_USER_AGENT, max_rate_per_sec: float = 8.0):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.min_interval = 1.0 / max_rate_per_sec
        self.last_request_time = 0.0

        # Configure session with connection pooling and retries
        self.session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _throttle(self) -> None:
        """Enforces inter-request delay to prevent rate-limiting violations."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def get(self, url: str, timeout: int = 15) -> requests.Response:
        """Performs a throttled, retrying GET request."""
        self._throttle()
        response = self.session.get(url, headers=self.headers, timeout=timeout)
        response.raise_for_status()
        return response