# sec_keyterms/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base filesystem paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure data directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Financial & Regulatory Settings
DEFAULT_EXCHANGE = os.getenv("EXCHANGE_CALENDAR", "NYSE")
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT", 
    "DataEngineeringPortfolio candidate@domain.com"
)