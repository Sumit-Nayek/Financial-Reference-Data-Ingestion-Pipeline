import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from sec_keyterms.config import PROCESSED_DATA_DIR


class ReferenceDataWriter:
    """Manages atomic writing of Golden Copy records and Quarantine Exception logs."""

    def __init__(self, output_dir: Path = PROCESSED_DATA_DIR):
        self.output_dir = output_dir

    def write_golden_copy(self, records: List[Dict[str, Any]], filename: str = "golden_master.json") -> Path:
        target_path = self.output_dir / filename
        temp_path = self.output_dir / f"{filename}.tmp"

        payload = {
            "_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_records": len(records),
                "market_region": "IN",
                "schema_version": "1.0.0"
            },
            "data": records
        }

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        temp_path.replace(target_path)
        return target_path

    def write_quarantine(self, errors: List[Dict[str, Any]], filename: str = "quarantine_exceptions.csv") -> Path:
        target_path = self.output_dir / filename
        fieldnames = ["isin", "issuer_name", "error_reason", "failed_at"]

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for err in errors:
                writer.writerow(err)

        return target_path