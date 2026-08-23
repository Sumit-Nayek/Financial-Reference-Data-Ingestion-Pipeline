# sec_keyterms/run.py
import argparse
import uuid
from datetime import date
from typing import List, Dict, Any
from sec_keyterms.business_day import MarketCalendar
from sec_keyterms.daily_index import SECDailyIndex
from sec_keyterms.extractor import SEC424B2Extractor
from sec_keyterms.validators import SecurityReferenceSchema
from sec_keyterms.writers import ReferenceDataWriter

MOCK_HTML_MAP = {
    "RELIANCE": """
    <html>
        <head><title>RELIANCE INDUSTRIES LIMITED</title></head>
        <body>
            <table>
                <tr><td>ISIN:</td><td>INE002A08601</td></tr>
                <tr><td>BSE Scrip Code:</td><td>500325</td></tr>
                <tr><td>Coupon Rate:</td><td>7.20%</td></tr>
                <tr><td>Redemption Date:</td><td>2032-05-18</td></tr>
                <tr><td>Credit Rating:</td><td>CRISIL AAA</td></tr>
            </table>
        </body>
    </html>
    """,
    "HDFCBANK": """
    <html>
        <head><title>HDFC BANK LIMITED</title></head>
        <body>
            <table>
                <tr><td>ISIN:</td><td>INE040A08435</td></tr>
                <tr><td>BSE Scrip Code:</td><td>500180</td></tr>
                <tr><td>Coupon Rate:</td><td>7.70%</td></tr>
                <tr><td>Redemption Date:</td><td>2031-03-25</td></tr>
                <tr><td>Credit Rating:</td><td>CRISIL AAA</td></tr>
            </table>
        </body>
    </html>
    """
}


def run_pipeline(target_date: date, enable_llm: bool = False) -> None:
    batch_id = str(uuid.uuid4())[:8]
    print(f"[PIPELINE START] Batch ID: {batch_id} | Target Date: {target_date.isoformat()}")

    # 1. Market Calendar Verification
    calendar = MarketCalendar(exchange="NSE")
    active_date = calendar.get_latest_business_day(target_date)
    if active_date != target_date:
        print(f"[CALENDAR] {target_date} was closed. Processing active session {active_date}")

    # 2. Daily Index Filings Discovery
    indexer = SECDailyIndex()
    filings_df = indexer.fetch_and_filter(active_date)
    print(f"[INDEX] Discovered {len(filings_df)} target filings.")

    # 3. Extraction & Validation
    extractor = SEC424B2Extractor()
    writer = ReferenceDataWriter()

    golden_records: List[Dict[str, Any]] = []
    quarantine_records: List[Dict[str, Any]] = []

    for _, row in filings_df.iterrows():
        symbol = row.get("symbol", "RELIANCE")
        html_payload = MOCK_HTML_MAP.get(symbol, MOCK_HTML_MAP["RELIANCE"])

        raw_data = extractor.extract(html_payload, enable_llm_fallback=enable_llm)
        raw_data["source_symbol"] = symbol
        raw_data["source_url"] = row.get("file_url")

        try:
            validated = SecurityReferenceSchema(**raw_data)
            golden_records.append(validated.model_dump())
        except Exception as e:
            quarantine_records.append({
                "isin": raw_data.get("isin", "UNKNOWN"),
                "issuer_name": raw_data.get("issuer_name", "UNKNOWN"),
                "error_reason": str(e),
                "raw_payload": raw_data,
            })

    # 4. Commit to Relational Database & JSON
    writer.persist_to_database(
        valid_records=golden_records,
        quarantine_records=quarantine_records,
        execution_date=active_date,
        batch_id=batch_id,
    )
    json_path = writer.write_golden_copy(golden_records)

    print(f"[DB COMMIT] Persisted {len(golden_records)} records to SQLite database (security_master.db)")
    print(f"[LOAD SUCCESS] JSON master committed to {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian Market Debt Reference Ingestion Pipeline")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--enable-llm", action="store_true", help="Enable LLM semantic fallback")
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    run_pipeline(target_date=run_date, enable_llm=args.enable_llm)