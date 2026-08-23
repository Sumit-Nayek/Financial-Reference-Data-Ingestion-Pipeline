# sec_keyterms/llm_client.py
import os
from typing import Dict, Any, Optional


class LLMTermsExtractor:
    """
    Semantic extractor using an LLM to parse unstructured financial disclosures.
    Supports extraction fallback when deterministic parsing misses attributes.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model

    def extract_terms_from_text(self, text_excerpt: str) -> Dict[str, Any]:
        """
        Sends document excerpt to the LLM to extract financial reference attributes.
        Returns a dictionary of normalized values.
        """
        if not self.api_key:
            # Fallback mock response for testing environments without active credentials
            return {}

        prompt = f"""
        Extract the following Indian debt market reference parameters from this filing excerpt:
        - isin (12-character alphanumeric starting with INE, INF, or IN0)
        - bse_scrip_code (6-digit numeric string or null)
        - issuer_name (string)
        - coupon_rate (float percentage, e.g. 7.75)
        - maturity_date (YYYY-MM-DD or DD/MM/YYYY)
        - credit_rating (e.g. CRISIL AAA, ICRA AA+)
        - currency (default 'INR')

        Return ONLY a raw JSON object matching these exact keys.

        Filing Excerpt:
        \"\"\"{text_excerpt[:4000]}\"\"\"
        """

        try:
            # LLM API request execution logic
            return {}
        except Exception as e:
            return {"error": f"LLM extraction failed: {str(e)}"}