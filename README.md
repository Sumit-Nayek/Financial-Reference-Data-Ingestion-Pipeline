# Indian Debt Reference Data Ingestion & Validation Pipeline
![The Represention of the workflow](image.png)

An enterprise-grade, modular Python ETL pipeline engineered to ingest, extract, validate, and benchmark corporate debt reference data (NCDs, Bonds, Commercial Papers) and regulatory disclosures across Indian capital markets (NSE/BSE/NSDL).

---
## Key Features

- **Exchange Calendar Awareness (`business_day.py`):** Automatically rolls back batch runs across Indian market holidays and weekends using `pandas-market-calendars` (NSE/BSE).
- **Session-Aware Ingestion (`http_client.py`):** Handles connection pooling, automatic cookie initialization, rate-limiting, and exponential backoff.
- **Hybrid Extraction Engine (`extractor.py` & `llm_client.py`):** Uses fast DOM/regex extraction for tabular prospectuses with seamless LLM fallback for ambiguous disclosures.
- **Symbology & Schema Enforcement (`validators.py`):** Validates 12-character Indian ISIN prefixes (`INE`, `INF`, `IN0`), BSE 6-digit scrip codes, and logical financial boundaries.
- **Atomic Persistence & Lineage (`writers.py`):** Atomically commits valid records to `golden_master.json` with metadata provenance while routing bad records to `quarantine_exceptions.csv`.
- **Benchmarking Suite (`benchmark_report.py`):** Measures throughput, memory overhead, and latency per document, logging metrics to `docs/Baseline_Report.md`.

---
