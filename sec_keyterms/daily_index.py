# sec_keyterms/daily_index.py
from datetime import date
from typing import List, Dict, Optional
import pandas as pd
from sec_keyterms.http_client import RateLimitedSECClient

SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/"


class SECDailyIndex:
    """Fetches and parses SEC EDGAR daily master index files."""

    def __init__(self, client: Optional[RateLimitedSECClient] = None):
        self.client = client or RateLimitedSECClient()

    def build_index_url(self, target_date: date) -> str:
        """Constructs the canonical SEC master index URL for a given date."""
        year = target_date.year
        quarter = (target_date.month - 1) // 3 + 1
        date_str = target_date.strftime("%Y%m%d")
        return f"{SEC_ARCHIVES_BASE}edgar/daily-index/{year}/QTR{quarter}/master.{date_str}.idx"

    def fetch_and_filter(
        self, target_date: date, form_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Fetches the master index for target_date and filters for specified form types (e.g. ['424B2']).
        """
        target_forms = form_types or ["424B2"]
        index_url = self.build_index_url(target_date)

        response = self.client.get(index_url)
        raw_text = response.text

        # Master index files contain metadata headers ending with a dashed separator
        lines = raw_text.splitlines()
        data_start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("---"):
                data_start_idx = i + 1
                break

        if data_start_idx == 0 and lines:
            data_start_idx = 0

        # Parse pipe-separated entries: CIK|Company Name|Form Type|Date Filed|File Name
        records: List[Dict[str, str]] = []
        for line in lines[data_start_idx:]:
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) == 5:
                cik, company, form, date_filed, file_path = parts
                if form.strip() in target_forms:
                    records.append({
                        "cik": cik.strip(),
                        "company_name": company.strip(),
                        "form_type": form.strip(),
                        "date_filed": date_filed.strip(),
                        "file_url": f"{SEC_ARCHIVES_BASE}{file_path.strip()}",
                    })

        df = pd.DataFrame(records)
        return df