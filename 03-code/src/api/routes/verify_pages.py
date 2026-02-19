"""
API Routes - Verify Pages

Endpoints for displaying raw pages side-by-side with raw knowledge units.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.utils.logging_config import logger
import base64

router = APIRouter()


class RawPageData(BaseModel):
    """Raw page data model."""
    page_number: int
    image_base64: str
    image_format: str
    width: int
    height: int
    knowledge_units: List[dict]


@router.get("/verify-pages/{book_id}")
async def get_verify_pages(
    book_id: int,
    page_number: Optional[int] = Query(None, description="Specific page number (1-based). If not provided, returns first page.")
):
    """
    Get raw page image and associated knowledge units for verification.

    Args:
        book_id: Book ID
        page_number: Page number to display (1-based indexing)

    Returns:
        dict: Page data with image and knowledge units

    Raises:
        HTTPException: If book or page not found

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/verify-pages/1?page_number=5')
    """
    db = SessionLocal()

    try:
        # Get book metadata
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix
        total_pages = book.total_pages

        # V2 books don't have V1 raw_knowledge_units tables
        extraction_method = getattr(book, 'extraction_method', 'v1') or 'v1'
        if extraction_method == 'v2':
            return {
                "message": "V2 books use cloud extraction. Use the V2 Knowledge Review page instead.",
                "extraction_method": "v2",
                "book_id": book_id,
                "redirect": f"/v2-knowledge-review?book_id={book_id}"
            }

        # Default to page 1 if not specified
        if page_number is None:
            page_number = 1

        # Validate page number
        if page_number < 1 or page_number > total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid page number. Book has {total_pages} pages."
            )

        # Get raw page data
        page_query = text(f"""
            SELECT id, page_number, original_image_data, original_format,
                   original_width, original_height
            FROM raw_{table_prefix}_pages
            WHERE page_number = :page_number
        """)
        page_result = db.execute(page_query, {"page_number": page_number}).first()

        if not page_result:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page_number} not found in raw pages table"
            )

        raw_page_id, page_num, image_data, image_format, width, height = page_result

        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else None

        # Get knowledge units for this page
        ku_query = text(f"""
            SELECT id, ocr_engine, full_page_text, confidence_score,
                   text_length, language, ocr_run_timestamp
            FROM raw_{table_prefix}_knowledge_units
            WHERE page_number = :page_number
            ORDER BY ocr_run_timestamp DESC
        """)
        ku_results = db.execute(ku_query, {"page_number": page_number}).fetchall()

        knowledge_units = []
        for ku in ku_results:
            knowledge_units.append({
                "id": ku[0],
                "ocr_engine": ku[1],
                "full_page_text": ku[2],
                "confidence_score": float(ku[3]) if ku[3] else None,
                "text_length": ku[4],
                "language": ku[5],
                "ocr_run_timestamp": ku[6].isoformat() if ku[6] else None
            })

        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "page_number": page_num,
            "total_pages": total_pages,
            "image_base64": image_base64,
            "image_format": image_format,
            "width": width,
            "height": height,
            "knowledge_units": knowledge_units
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verify pages for book {book_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get verify pages: {str(e)}")
    finally:
        db.close()


@router.get("/verify-pages/{book_id}/list")
async def list_verify_pages(book_id: int):
    """
    List all pages available for verification for a book.

    Args:
        book_id: Book ID

    Returns:
        dict: List of page numbers with raw data

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/verify-pages/1/list')
    """
    db = SessionLocal()

    try:
        # Get book metadata
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix

        # Get all pages with raw data
        pages_query = text(f"""
            SELECT page_number, original_format, original_width, original_height
            FROM raw_{table_prefix}_pages
            ORDER BY page_number
        """)
        pages_results = db.execute(pages_query).fetchall()

        pages = []
        for page in pages_results:
            pages.append({
                "page_number": page[0],
                "image_format": page[1],
                "width": page[2],
                "height": page[3]
            })

        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "total_pages": len(pages),
            "pages": pages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing verify pages for book {book_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list verify pages: {str(e)}")
    finally:
        db.close()
