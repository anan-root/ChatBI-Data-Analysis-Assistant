import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

MONTH_COLUMNS = [f"{month}月销量" for month in range(1, 13)]
IMPORT_JOBS_DIR = BASE_DIR / "import_jobs"
CLEANED_DATA_DIR = IMPORT_JOBS_DIR / "cleaned"
METADATA_DIR = IMPORT_JOBS_DIR / "metadata"
EXPORT_DIR = BASE_DIR / "exports"
AUDIT_DIR = BASE_DIR / "audit_logs"

for directory in [CLEANED_DATA_DIR, METADATA_DIR, EXPORT_DIR, AUDIT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def postgres_metadata_enabled():
    return os.getenv("CHATBI_USE_POSTGRES_METADATA", "false").strip().lower() in {"1", "true", "yes", "on"}


def postgres_audit_enabled():
    return os.getenv("CHATBI_USE_POSTGRES_AUDIT", "false").strip().lower() in {"1", "true", "yes", "on"}
