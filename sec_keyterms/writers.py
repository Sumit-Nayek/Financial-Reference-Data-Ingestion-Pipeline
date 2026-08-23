# sec_keyterms/writers.py
import json
import csv
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any
from sec_keyterms.config import PROCESSED_DATA_DIR
from sec_keyterms.database import (
    init_db,
    SessionLocal,
    Security,
    FixedIncomeTerm,
    QuarantineRecord,
    PipelineAudit,
)


class ReferenceDataWriter:
    """Manages persistence to SQLite Security Master database and flat file backups."""

    def __init__(self, output_dir: Path = PROCESSED_DATA_DIR):
        self.output_dir = output_dir
        init_db()

    def persist_to_database(
        self,
        valid_records: List[Dict[str, Any]],
        quarantine_records: List[Dict[str, Any]],
        execution_date: date,
        batch_id: str,
    ) -> None:
        """Saves records to SQLite with in-batch upsert handling and logs run metrics."""
        session = SessionLocal()
        try:
            for rec in valid_records:
                isin = rec["isin"]
                
                # Check both the session identity map and the database
                existing_sec = session.get(Security, isin)

                if not existing_sec:
                    sec = Security(
                        isin=isin,
                        bse_scrip_code=rec.get("bse_scrip_code"),
                        source_symbol=rec.get("source_symbol"),
                        issuer_name=rec["issuer_name"],
                        currency=rec.get("currency", "INR"),
                    )
                    term = FixedIncomeTerm(
                        isin=isin,
                        coupon_rate=rec["coupon_rate"],
                        maturity_date=rec["maturity_date"],
                        credit_rating=rec.get("credit_rating"),
                        source_url=rec.get("source_url"),
                    )
                    sec.terms = term
                    session.add(sec)
                else:
                    # Update existing record in place
                    existing_sec.bse_scrip_code = rec.get("bse_scrip_code")
                    existing_sec.issuer_name = rec["issuer_name"]
                    if existing_sec.terms:
                        existing_sec.terms.coupon_rate = rec["coupon_rate"]
                        existing_sec.terms.maturity_date = rec["maturity_date"]
                        existing_sec.terms.credit_rating = rec.get("credit_rating")
                        existing_sec.terms.source_url = rec.get("source_url")
                    else:
                        existing_sec.terms = FixedIncomeTerm(
                            isin=isin,
                            coupon_rate=rec["coupon_rate"],
                            maturity_date=rec["maturity_date"],
                            credit_rating=rec.get("credit_rating"),
                            source_url=rec.get("source_url"),
                        )
                
                # Flush changes to the session to track the entity for subsequent records
                session.flush()

            # Insert Quarantine records
            for err in quarantine_records:
                q_rec = QuarantineRecord(
                    isin=err.get("isin"),
                    issuer_name=err.get("issuer_name"),
                    raw_payload=json.dumps(err.get("raw_payload", {})),
                    error_reason=err.get("error_reason", "Validation Error"),
                )
                session.add(q_rec)

            # Log Audit Entry
            audit = PipelineAudit(
                batch_id=batch_id,
                execution_date=execution_date,
                records_ingested=len(valid_records),
                records_quarantined=len(quarantine_records),
                status="SUCCESS",
            )
            session.add(audit)
            session.commit()

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def write_golden_copy(self, records: List[Dict[str, Any]], filename: str = "golden_master.json") -> Path:
        target_path = self.output_dir / filename
        temp_path = self.output_dir / f"{filename}.tmp"

        payload = {
            "_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_records": len(records),
                "market_region": "IN",
                "schema_version": "1.0.0",
            },
            "data": records,
        }

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        temp_path.replace(target_path)
        return target_path