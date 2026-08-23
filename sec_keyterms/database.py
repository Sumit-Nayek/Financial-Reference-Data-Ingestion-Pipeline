# sec_keyterms/database.py
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Date,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sec_keyterms.config import PROCESSED_DATA_DIR

DB_PATH = PROCESSED_DATA_DIR / "security_master.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PipelineAudit(Base):
    __tablename__ = "pipeline_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False)
    execution_date = Column(Date, nullable=False)
    records_ingested = Column(Integer, default=0)
    records_quarantined = Column(Integer, default=0)
    status = Column(String(20), default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)


class Security(Base):
    __tablename__ = "securities"

    isin = Column(String(12), primary_key=True, index=True)
    bse_scrip_code = Column(String(6), nullable=True, index=True)
    source_symbol = Column(String(30), nullable=True)
    issuer_name = Column(String(255), nullable=False)
    currency = Column(String(3), default="INR")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    terms = relationship("FixedIncomeTerm", back_populates="security", uselist=False, cascade="all, delete-orphan")


class FixedIncomeTerm(Base):
    __tablename__ = "fixed_income_terms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isin = Column(String(12), ForeignKey("securities.isin"), unique=True, nullable=False)
    coupon_rate = Column(Float, nullable=False)
    maturity_date = Column(String(20), nullable=False)
    credit_rating = Column(String(50), nullable=True)
    source_url = Column(Text, nullable=True)

    security = relationship("Security", back_populates="terms")


class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isin = Column(String(20), nullable=True)
    issuer_name = Column(String(255), nullable=True)
    raw_payload = Column(Text, nullable=True)
    error_reason = Column(Text, nullable=False)
    failed_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initializes all database tables."""
    Base.metadata.create_all(bind=engine)