from datetime import date, datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from sec_keyterms.database import (
    FixedIncomeTerm,
    PipelineAudit,
    QuarantineRecord,
    Security,
    init_db,
)
from sec_keyterms.extractor import SEC424B2Extractor
from sec_keyterms.validators import SecurityReferenceSchema
from sec_keyterms.writers import ReferenceDataWriter
import sec_keyterms.run as pipeline


SOURCE_URL = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"


@pytest.fixture
def database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    writer = ReferenceDataWriter(
        output_dir=tmp_path,
        session_factory=session_factory,
        database_engine=engine,
    )
    yield writer, session_factory
    engine.dispose()


def hdfc_record():
    raw_data = SEC424B2Extractor().extract_from_html(pipeline.MOCK_HTML_MAP["HDFCBANK"])
    raw_data["source_symbol"] = "HDFCBANK"
    raw_data["source_url"] = SOURCE_URL
    return SecurityReferenceSchema(**raw_data).model_dump()


def test_pipeline_is_idempotent_and_preserves_source_metadata(database, monkeypatch):
    writer, session_factory = database

    class MockCalendar:
        def __init__(self, exchange):
            pass

        def get_latest_business_day(self, target_date):
            return target_date

    class MockIndex:
        def fetch_and_filter(self, target_date):
            return pd.DataFrame([
                {"symbol": "HDFCBANK", "file_url": SOURCE_URL},
                {"symbol": "RELIANCE", "file_url": SOURCE_URL},
            ])

    monkeypatch.setattr(pipeline, "MarketCalendar", MockCalendar)
    monkeypatch.setattr(pipeline, "SECDailyIndex", MockIndex)
    monkeypatch.setattr(pipeline, "ReferenceDataWriter", lambda: writer)

    execution_date = date(2026, 10, 9)
    pipeline.run_pipeline(execution_date)
    with session_factory() as session:
        initial_timestamps = {
            security.isin: (security.created_at, security.updated_at)
            for security in session.scalars(select(Security))
        }

    pipeline.run_pipeline(execution_date)

    with session_factory() as session:
        securities = list(session.scalars(select(Security)))
        terms = list(session.scalars(select(FixedIncomeTerm)))
        audits = list(session.scalars(select(PipelineAudit).order_by(PipelineAudit.id)))

    assert len(securities) == 2
    assert {security.source_symbol for security in securities} == {"HDFCBANK", "RELIANCE"}
    assert {term.source_url for term in terms} == {SOURCE_URL}
    assert all(
        (security.created_at, security.updated_at) == initial_timestamps[security.isin]
        for security in securities
    )
    assert [(audit.records_ingested, audit.records_inserted, audit.records_updated,
             audit.records_skipped, audit.records_quarantined) for audit in audits] == [
        (2, 2, 0, 0, 0),
        (0, 0, 0, 2, 0),
    ]


def test_writer_audits_insert_skip_and_quarantine(database):
    writer, session_factory = database
    quarantine = {
        "isin": "UNKNOWN",
        "issuer_name": "Unknown",
        "error_reason": "Validation Error",
        "raw_payload": {"source_symbol": "UNKNOWN"},
    }

    writer.persist_to_database([hdfc_record()], [quarantine], date(2026, 10, 9), "first")
    writer.persist_to_database([hdfc_record()], [], date(2026, 10, 9), "second")

    with session_factory() as session:
        audits = list(session.scalars(select(PipelineAudit).order_by(PipelineAudit.id)))
        quarantined = list(session.scalars(select(QuarantineRecord)))

    assert [(audit.records_ingested, audit.records_inserted, audit.records_updated,
             audit.records_skipped, audit.records_quarantined) for audit in audits] == [
        (1, 1, 0, 0, 1),
        (0, 0, 0, 1, 0),
    ]
    assert len(quarantined) == 1


def test_writer_refreshes_updated_at_only_for_changes(database):
    writer, session_factory = database
    record = hdfc_record()
    writer.persist_to_database([record], [], date(2026, 10, 9), "first")
    prior_timestamp = datetime(2026, 8, 23)

    with session_factory() as session:
        security = session.get(Security, record["isin"])
        created_at = security.created_at
        security.updated_at = prior_timestamp
        session.commit()

    changed_record = {**record, "issuer_name": "HDFC Bank Limited"}
    writer.persist_to_database([changed_record], [], date(2026, 10, 9), "update")

    with session_factory() as session:
        security = session.get(Security, record["isin"])
        audits = list(session.scalars(select(PipelineAudit).order_by(PipelineAudit.id)))

    assert security.created_at == created_at
    assert security.updated_at > prior_timestamp
    assert audits[-1].records_ingested == 1
    assert audits[-1].records_updated == 1
    assert audits[-1].records_inserted == 0
    assert audits[-1].records_skipped == 0


def test_init_db_adds_audit_counts_to_legacy_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE pipeline_audit_logs (
                id INTEGER PRIMARY KEY,
                batch_id VARCHAR(64) NOT NULL,
                execution_date DATE NOT NULL,
                records_ingested INTEGER,
                records_quarantined INTEGER,
                status VARCHAR(20),
                created_at DATETIME
            )
        """))

    init_db(bind=engine)

    columns = {column["name"] for column in inspect(engine).get_columns("pipeline_audit_logs")}
    assert {"records_inserted", "records_updated", "records_skipped"} <= columns
    engine.dispose()