import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from sec_keyterms.llm_client import LLMTermsExtractor


class SEC424B2Extractor:
    """
    Extractor tailored for Indian Listed Debentures (NCDs) and Corporate Actions.
    """

    # Indian Security Identifiers
    ISIN_PATTERN = re.compile(r"\b(INE[0-9A-Z]{9}[0-9]|INF[0-9A-Z]{9}[0-9]|IN0[0-9A-Z]{9}[0-9])\b")
    SCRIP_CODE_PATTERN = re.compile(r"\b(5\d{5})\b")  # BSE Scrip codes start with 5 (e.g., 500325)
    COUPON_PATTERN = re.compile(
        r"(?:coupon(?: rate)?|interest rate|interest)\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    MATURITY_PATTERN = re.compile(
        r"(?:redemption date|maturity date|due date)\s*[:=-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        re.IGNORECASE,
    )
    CREDIT_RATING_PATTERN = re.compile(
        r"\b(CRISIL|ICRA|CARE|IND-RA|BRICKWORK)\s+([A-Z]{1,3}(?:[+-])?)\b",
        re.IGNORECASE
    )

    def __init__(self, llm_extractor: Optional[LLMTermsExtractor] = None):
        self.llm_extractor = llm_extractor or LLMTermsExtractor()

    def _clean_text(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return " ".join(soup.get_text().split())

    def extract_from_html(self, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, "lxml")
        full_text = self._clean_text(soup)

        extracted: Dict[str, Any] = {
            "isin": None,
            "bse_scrip_code": None,
            "issuer_name": None,
            "coupon_rate": None,
            "maturity_date": None,
            "credit_rating": None,
            "currency": "INR",
        }

        isin_match = self.ISIN_PATTERN.search(full_text)
        if isin_match:
            extracted["isin"] = isin_match.group(1).upper()

        scrip_match = self.SCRIP_CODE_PATTERN.search(full_text)
        if scrip_match:
            extracted["bse_scrip_code"] = scrip_match.group(1)

        coupon_match = self.COUPON_PATTERN.search(full_text)
        if coupon_match:
            extracted["coupon_rate"] = float(coupon_match.group(1))

        maturity_match = self.MATURITY_PATTERN.search(full_text)
        if maturity_match:
            extracted["maturity_date"] = maturity_match.group(1)

        rating_match = self.CREDIT_RATING_PATTERN.search(full_text)
        if rating_match:
            extracted["credit_rating"] = f"{rating_match.group(1).upper()} {rating_match.group(2).upper()}"

        title_tag = soup.find("title") or soup.find("h1")
        if title_tag:
            extracted["issuer_name"] = title_tag.text.strip()

        return extracted

    def extract(self, html_content: str, enable_llm_fallback: bool = True) -> Dict[str, Any]:
        data = self.extract_from_html(html_content)
        required_fields = ["isin", "coupon_rate", "maturity_date"]
        missing_fields = [f for f in required_fields if data.get(f) is None]

        if missing_fields and enable_llm_fallback:
            soup = BeautifulSoup(html_content, "lxml")
            cleaned_text = self._clean_text(soup)
            llm_data = self.llm_extractor.extract_terms_from_text(cleaned_text[:5000])

            for field in missing_fields:
                if llm_data.get(field) is not None:
                    data[field] = llm_data[field]

        return data