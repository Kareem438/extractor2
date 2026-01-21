#!/usr/bin/env python3
"""
Direct test of Surya OCR function
"""
import sys
sys.path.insert(0, '/mnt/h/12-extractor/03-code')

from src.services.ocr_sequential import run_surya_sequential
from src.utils.logging_config import logger

logger.info("=" * 80)
logger.info("DIRECT TEST: Calling run_surya_sequential directly")
logger.info("=" * 80)

try:
    run_surya_sequential(book_id=1, max_pages=2)
    logger.info("✅ Function completed successfully")
except Exception as e:
    logger.error(f"❌ Function failed: {e}", exc_info=True)

logger.info("=" * 80)
logger.info("TEST COMPLETE")
logger.info("=" * 80)
