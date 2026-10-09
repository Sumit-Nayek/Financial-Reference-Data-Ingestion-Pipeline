# sec_keyterms/writers.py
import json
import csv
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any
from sec_keyterms.config import PROCESSED_DATA_DIR
from sec_keyterms.database import (
    engine,
    init_db,
    SessionLocal,
    Security,
    FixedIncomeTerm,
    QuarantineRecord,
    PipelineAudit,
)

# Instead of overwriting existing metadata with None:
existing.source_symbol = incoming.source_symbol
existing.source_url = incoming.source_url

# Preserve existing values when incoming metadata is absent:
if incoming.source_symbol is not None:
    existing.source_symbol = incoming.source_symbol

if incoming.source_url is not None:
    existing.source_url = incoming.source_url
class ReferenceDataWriter:
    """Manages persistence to SQLite Security Master database and flat file backups."""

    def __init__(
        self,
        output_dir: Path = PROCESSED_DATA_DIR,
        session_factory=SessionLocal,
        database_engine=engine,
    ):
        self.output_dir = output_dir
        self.session_factory = session_factory
        init_db(bind=database_engine)

    def persist_to_database(
        self,
        valid_records: List[Dict[str, Any]],
        quarantine_records: List[Dict[str, Any]],
        execution_date: date,
        batch_id: str,
    ) -> None:
        """Saves records to SQLite with in-batch upsert handling and logs run metrics."""
        session = self.session_factory()
        try:
            inserted_count = 0
            updated_count = 0
            skipped_count = 0

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
                    inserted_count += 1
                else:
                    changed = False
                    security_values = {
                        "bse_scrip_code": rec.get("bse_scrip_code"),
                        "source_symbol": rec.get("source_symbol"),
                        "issuer_name": rec["issuer_name"],
                        "currency": rec.get("currency", "INR"),
                    }
                    for field, value in security_values.items():
                        if getattr(existing_sec, field) != value:
                            setattr(existing_sec, field, value)
                            changed = True

                    if existing_sec.terms:
                        term_values = {
                            "coupon_rate": rec["coupon_rate"],
                            "maturity_date": rec["maturity_date"],
                            "credit_rating": rec.get("credit_rating"),
                            "source_url": rec.get("source_url"),
                        }
                        for field, value in term_values.items():
                            if getattr(existing_sec.terms, field) != value:
                                setattr(existing_sec.terms, field, value)
                                changed = True
                    else:
                        existing_sec.terms = FixedIncomeTerm(
                            isin=isin,
                            coupon_rate=rec["coupon_rate"],
                            maturity_date=rec["maturity_date"],
                            credit_rating=rec.get("credit_rating"),
                            source_url=rec.get("source_url"),
                        )
                        changed = True

                    if changed:
                        existing_sec.updated_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        skipped_count += 1
                
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
                records_ingested=inserted_count + updated_count,
                records_inserted=inserted_count,
                records_updated=updated_count,
                records_skipped=skipped_count,
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