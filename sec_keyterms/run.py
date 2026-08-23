# sec_keyterms/run.py
import argparse
from datetime import date, datetime
from typing import List, Dict, Any
from sec_keyterms.business_day import MarketCalendar
from sec_keyterms.daily_index import SECDailyIndex
from sec_keyterms.extractor import SEC424B2Extractor
from sec_keyterms.validators import SecurityReferenceSchema
from sec_keyterms.writers import ReferenceDataWriter


def run_pipeline(target_date: date, enable_llm: bool = False) -> None:
    print(f"[PIPELINE START] Initializing reference ingestion for {target_date.isoformat()}")

    # 1. Evaluate market session
    calendar = MarketCalendar(exchange="NSE")
    active_date = calendar.get_latest_business_day(target_date)
    if active_date != target_date:
        print(f"[CALENDAR] {target_date} was a market holiday/weekend. Rolling back to {active_date}")

    # 2. Fetch daily index filings
    indexer = SECDailyIndex()
    filings_df = indexer.fetch_and_filter(active_date)
    print(f"[INDEX] Discovered {len(filings_df)} target corporate filings.")

    # 3. Extraction & Validation loop
    extractor = SEC424B2Extractor()
    writer = ReferenceDataWriter()

    golden_records: List[Dict[str, Any]] = []
    quarantine_records: List[Dict[str, Any]] = []

    # Mock sample document payload for demonstration
    sample_filing_html = """
    <html>
        <head><title>RELIANCE INDUSTRIES LIMITED</title></head>
        <body>
            <table>
                <tr><td>Issuer:</td><td>Reliance Industries Limited</td></tr>
                <tr><td>ISIN:</td><td>INE002A08601</td></tr>
                <tr><td>BSE Scrip Code:</td><td>500325</td></tr>
                <tr><td>Coupon Rate:</td><td>7.20%</td></tr>
                <tr><td>Redemption Date:</td><td>2032-05-18</td></tr>
                <tr><td>Credit Rating:</td><td>CRISIL AAA</td></tr>
            </table>
        </body>
    </html>
    """

    for _, row in filings_df.iterrows():
        raw_data = extractor.extract(sample_filing_html, enable_llm_fallback=enable_llm)
        raw_data["source_symbol"] = row.get("symbol")
        raw_data["source_url"] = row.get("file_url")

        try:
            # Validate schema
            validated = SecurityReferenceSchema(**raw_data)
            golden_records.append(validated.model_dump())
        except Exception as e:
            quarantine_records.append({
                "isin": raw_data.get("isin", "UNKNOWN"),
                "issuer_name": raw_data.get("issuer_name", "UNKNOWN"),
                "error_reason": str(e),
                "failed_at": datetime.now().isoformat()
            })

    # 4. Commit atomic persistence
    golden_path = writer.write_golden_copy(golden_records)
    print(f"[LOAD SUCCESS] Committed {len(golden_records)} records to {golden_path}")

    if quarantine_records:
        quarantine_path = writer.write_quarantine(quarantine_records)
        print(f"[QUARANTINE ALERT] Diverted {len(quarantine_records)} invalid records to {quarantine_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indian Market Debt Reference Ingestion Pipeline")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--enable-llm", action="store_true", help="Enable LLM semantic fallback")
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    run_pipeline(target_date=run_date, enable_llm=args.enable_llm)