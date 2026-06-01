"""
Manual re-index script.
Run from project root: python scripts/reindex.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.rag_service import build_index
from core.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    build_index(force=True)
    print("Re-indexing complete.")

