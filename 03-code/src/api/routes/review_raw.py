"""
API routes for Review Raw Data page.
Provides endpoints to fetch page images and associated clips (paragraphs/diagrams).
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.database.connection import engine
from src.utils.logging_config import logger
import base64

router = APIRouter(prefix="/api/review-raw", tags=["review-raw"])


@router.get("/{book_id}/page/{page_number}")
async def get_page_image(book_id: int, page_number: int):
    """
    Get a single page image for display.
    Returns the page image as base64 along with metadata.
    """
    try:
        # Get book metadata
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get page image from raw_pages
            page_sql = text(f"""
                SELECT
                    id,
                    page_number,
                    original_image_data,
                    original_format,
                    original_width,
                    original_height,
                    original_size_bytes
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_number
            """)

            page_result = conn.execute(page_sql, {"page_number": page_number}).first()

            if not page_result:
                raise HTTPException(status_code=404, detail=f"Page {page_number} not found")

            # Convert image to base64
            image_base64 = base64.b64encode(page_result[2]).decode('utf-8') if page_result[2] else None

            return {
                "id": page_result[0],
                "page_number": page_result[1],
                "image_base64": image_base64,
                "image_format": page_result[3],
                "image_width": page_result[4],
                "image_height": page_result[5],
                "image_size_bytes": page_result[6]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching page {page_number} for book {book_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{book_id}/clips")
async def get_clips_for_pages(book_id: int, page_start: int, page_end: int):
    """
    Get all paragraph and diagram clips for a range of pages.
    Returns clips with their images as base64.
    """
    try:
        # Get book metadata
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get paragraphs
            paragraphs_sql = text(f"""
                SELECT
                    id,
                    page_number,
                    selection_x,
                    selection_y,
                    selection_width,
                    selection_height,
                    image_data,
                    image_format,
                    extracted_text,
                    ocr_confidence,
                    selected_level_number,
                    selected_level_text,
                    created_at
                FROM raw_{table_prefix}_paragraph_images
                WHERE page_number >= :page_start AND page_number <= :page_end
                ORDER BY page_number, display_order, id
            """)

            paragraphs_result = conn.execute(paragraphs_sql, {
                "page_start": page_start,
                "page_end": page_end
            }).fetchall()

            paragraphs = []
            for row in paragraphs_result:
                image_base64 = base64.b64encode(row[6]).decode('utf-8') if row[6] else None
                paragraphs.append({
                    "id": row[0],
                    "page_number": row[1],
                    "selection_x": row[2],
                    "selection_y": row[3],
                    "selection_width": row[4],
                    "selection_height": row[5],
                    "image_base64": image_base64,
                    "image_format": row[7],
                    "extracted_text": row[8],
                    "ocr_confidence": float(row[9]) if row[9] else None,
                    "selected_level_number": row[10],
                    "selected_level_text": row[11],
                    "created_at": row[12].isoformat() if row[12] else None
                })

            # Get diagrams
            diagrams_sql = text(f"""
                SELECT
                    id,
                    page_number,
                    selection_x,
                    selection_y,
                    selection_width,
                    selection_height,
                    image_data,
                    image_format,
                    extracted_text,
                    description,
                    diagram_type,
                    ai_confidence,
                    selected_level_number,
                    selected_level_text,
                    created_at
                FROM raw_{table_prefix}_diagram_images
                WHERE page_number >= :page_start AND page_number <= :page_end
                ORDER BY page_number, display_order, id
            """)

            diagrams_result = conn.execute(diagrams_sql, {
                "page_start": page_start,
                "page_end": page_end
            }).fetchall()

            diagrams = []
            for row in diagrams_result:
                image_base64 = base64.b64encode(row[6]).decode('utf-8') if row[6] else None
                diagrams.append({
                    "id": row[0],
                    "page_number": row[1],
                    "selection_x": row[2],
                    "selection_y": row[3],
                    "selection_width": row[4],
                    "selection_height": row[5],
                    "image_base64": image_base64,
                    "image_format": row[7],
                    "extracted_text": row[8],
                    "description": row[9],
                    "diagram_type": row[10],
                    "ocr_confidence": float(row[11]) if row[11] else None,
                    "selected_level_number": row[12],
                    "selected_level_text": row[13],
                    "created_at": row[14].isoformat() if row[14] else None
                })

            return {
                "paragraphs": paragraphs,
                "diagrams": diagrams,
                "page_start": page_start,
                "page_end": page_end
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clips for book {book_id}, pages {page_start}-{page_end}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
