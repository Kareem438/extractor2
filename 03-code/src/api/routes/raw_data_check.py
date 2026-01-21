"""
API Routes - Raw Data Check

Endpoints to check if raw pages and OCR results exist before processing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.utils.logging_config import logger
from typing import List, Optional

router = APIRouter()


class RawPageStatus(BaseModel):
    """Status of raw pages for a book"""
    book_id: int
    book_name: str
    total_pages: int
    raw_pages_saved: int
    raw_pages_missing: int
    pages_with_data: List[int]
    pages_without_data: List[int]


class OCREngineStatus(BaseModel):
    """Status of OCR for a specific engine"""
    engine: str
    pages_processed: int
    pages_missing: int
    pages_with_ocr: List[int]
    pages_without_ocr: List[int]


class RawDataCheckResponse(BaseModel):
    """Complete raw data status"""
    raw_page_status: RawPageStatus
    ocr_status: dict  # {engine: OCREngineStatus}


@router.get("/check-raw-data/{book_id}")
async def check_raw_data_status(book_id: int):
    """
    Check if raw pages exist and what OCR has been done.

    This endpoint checks:
    1. How many raw pages are saved in raw_book_..._pages
    2. For each OCR engine, which pages have been processed

    Args:
        book_id: Book ID to check

    Returns:
        Complete status of raw pages and OCR results
    """
    db = SessionLocal()

    try:
        # Get book metadata
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix
        total_pages = book.total_pages

        logger.info(f"Checking raw data status for book {book_id} ({book.book_name})")

        # 1. Check raw pages status
        raw_pages_query = text(f"""
            SELECT page_number
            FROM raw_{table_prefix}_pages
            ORDER BY page_number
        """)
        raw_pages_result = db.execute(raw_pages_query).fetchall()
        pages_with_data = [row[0] for row in raw_pages_result]
        pages_without_data = [p for p in range(1, total_pages + 1) if p not in pages_with_data]

        raw_page_status = {
            "book_id": book_id,
            "book_name": book.book_name,
            "total_pages": total_pages,
            "raw_pages_saved": len(pages_with_data),
            "raw_pages_missing": len(pages_without_data),
            "pages_with_data": pages_with_data,
            "pages_without_data": pages_without_data
        }

        # 2. Check OCR status for each engine
        ocr_engines = ['easyocr', 'surya', 'tesseract']
        ocr_status = {}

        for engine in ocr_engines:
            ocr_query = text(f"""
                SELECT DISTINCT page_number
                FROM raw_{table_prefix}_knowledge_units
                WHERE ocr_engine = :engine
                ORDER BY page_number
            """)
            ocr_result = db.execute(ocr_query, {"engine": engine}).fetchall()
            pages_with_ocr = [row[0] for row in ocr_result]
            pages_without_ocr = [p for p in range(1, total_pages + 1) if p not in pages_with_ocr]

            ocr_status[engine] = {
                "engine": engine,
                "pages_processed": len(pages_with_ocr),
                "pages_missing": len(pages_without_ocr),
                "pages_with_ocr": pages_with_ocr,
                "pages_without_ocr": pages_without_ocr
            }

        logger.info(f"Raw pages saved: {len(pages_with_data)}/{total_pages}")
        logger.info(f"EasyOCR processed: {ocr_status['easyocr']['pages_processed']}/{total_pages}")
        logger.info(f"Surya processed: {ocr_status['surya']['pages_processed']}/{total_pages}")
        logger.info(f"Tesseract processed: {ocr_status['tesseract']['pages_processed']}/{total_pages}")

        return {
            "raw_page_status": raw_page_status,
            "ocr_status": ocr_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking raw data status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check raw data: {str(e)}")
    finally:
        db.close()
