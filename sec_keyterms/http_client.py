import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from sec_keyterms.config import USER_AGENT, NSE_BASE_URL


class RateLimitedSECClient:
    """
    Session-aware HTTP client with cookie handshakes for Indian exchange portals.
    Maintains the original class name to preserve project imports.
    """

    def __init__(self, max_rate_per_sec: float = 5.0):
        self.min_interval = 1.0 / max_rate_per_sec
        self.last_request_time = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": NSE_BASE_URL
        })

        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._init_session_cookies()

    def _init_session_cookies(self) -> None:
        """Acquires fresh session cookies by visiting the homepage."""
        try:
            self.session.get(NSE_BASE_URL, timeout=10)
        except requests.RequestException:
            pass

    def _throttle(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def get(self, url: str, timeout: int = 15) -> requests.Response:
        self._throttle()
        response = self.session.get(url, timeout=timeout)
        if response.status_code == 401 or response.status_code == 403:
            self._init_session_cookies()
            response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response