"""
Sequential OCR Extraction Extension for Phase 4 Enhancement

This module contains additional endpoints for the Verify Pages UI enhancement.
These endpoints will be added to the main ocr.py routes file.
"""

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, List
from src.utils.logging_config import logger


# ============================================================================
# Sequential OCR Extraction Endpoints (Phase 4 Enhancement)
# ============================================================================

class RectangleCoordinates(BaseModel):
    """Rectangle coordinates for sequential OCR extraction"""
    x: int
    y: int
    width: int
    height: int


class ExtractSequentialRequest(BaseModel):
    """Request model for sequential OCR extraction from rectangles"""
    book_id: int
    page_number: int
    rectangles: List[RectangleCoordinates]  # Up to 3 rectangles


class ExtractSequentialResponse(BaseModel):
    """Response model for sequential OCR extraction"""
    success: bool
    ocr_results: List[dict]  # List of {text: str, confidence: float, index: int}
    message: str


async def extract_sequential_ocr(request: ExtractSequentialRequest):
    """
    Extract OCR text from up to 3 user-drawn rectangles sequentially.

    This endpoint is used in the Verify Pages UI (Phase 4 enhancement) to extract
    OCR text from diagram regions selected by the user. The extracted text is used
    to populate the 3 sequential OCR text areas.

    Process:
    1. Load the raw page image from database
    2. For each rectangle:
       - Crop the image to rectangle bounds
       - Run Surya OCR on the cropped region
       - Return extracted text and confidence
    3. Return all OCR results in order

    Args:
        request: Contains book_id, page_number, and list of rectangles

    Returns:
        ExtractSequentialResponse with OCR results for each rectangle
    """
    logger.info(f"Extracting sequential OCR for book_id={request.book_id}, page={request.page_number}, rectangles={len(request.rectangles)}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        from PIL import Image
        import io
        from src.services.ocr_sequential import run_surya_on_single_image

        # Validate rectangles count
        if len(request.rectangles) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 rectangles allowed")

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get raw page image
            page_query = text(f"""
                SELECT original_image_data
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_number
            """)
            page_result = db.execute(page_query, {"page_number": request.page_number}).first()

            if not page_result or not page_result[0]:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} image not found")

            page_image_bytes = bytes(page_result[0])

            # Load image
            page_image = Image.open(io.BytesIO(page_image_bytes))

            # Extract OCR for each rectangle
            ocr_results = []
            for idx, rect in enumerate(request.rectangles):
                logger.info(f"Processing rectangle {idx + 1}: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")

                # Crop image to rectangle
                cropped_image = page_image.crop((
                    rect.x,
                    rect.y,
                    rect.x + rect.width,
                    rect.y + rect.height
                ))

                # Convert to bytes
                buffer = io.BytesIO()
                cropped_image.save(buffer, format='PNG')
                cropped_bytes = buffer.getvalue()

                # Run Surya OCR
                ocr_result = run_surya_on_single_image(cropped_bytes)

                if ocr_result.get('success'):
                    ocr_results.append({
                        "index": idx + 1,
                        "text": ocr_result.get('text', ''),
                        "confidence": ocr_result.get('confidence', 0.0),
                        "rectangle": {
                            "x": rect.x,
                            "y": rect.y,
                            "width": rect.width,
                            "height": rect.height
                        }
                    })
                    logger.info(f"Rectangle {idx + 1}: Extracted {len(ocr_result.get('text', ''))} chars, confidence={ocr_result.get('confidence', 0.0):.2f}")
                else:
                    # OCR failed for this rectangle
                    error_msg = ocr_result.get('error', 'Unknown error')
                    logger.warning(f"Rectangle {idx + 1}: OCR failed - {error_msg}")
                    ocr_results.append({
                        "index": idx + 1,
                        "text": "",
                        "confidence": 0.0,
                        "rectangle": {
                            "x": rect.x,
                            "y": rect.y,
                            "width": rect.width,
                            "height": rect.height
                        },
                        "error": error_msg
                    })

            return ExtractSequentialResponse(
                success=True,
                ocr_results=ocr_results,
                message=f"Extracted OCR from {len(ocr_results)} rectangles"
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract sequential OCR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SaveSequentialTextsRequest(BaseModel):
    """Request model for saving sequential texts to diagram"""
    book_id: int
    diagram_id: int
    ocr_text_1: Optional[str] = None
    ocr_text_2: Optional[str] = None
    ocr_text_3: Optional[str] = None
    manual_text_1: Optional[str] = None
    manual_text_2: Optional[str] = None
    manual_text_3: Optional[str] = None


async def save_sequential_texts(request: SaveSequentialTextsRequest):
    """
    Save all 6 sequential texts (3 OCR + 3 manual) to diagram record.

    This endpoint is used in the Verify Pages UI (Phase 4 enhancement) to persist
    the extracted OCR texts and manually typed texts to the diagram_images table.

    The texts are stored in:
    - ocr_text_1, ocr_text_2, ocr_text_3: OCR-extracted texts from rectangles
    - manual_text_1, manual_text_2, manual_text_3: User-typed texts

    Args:
        request: Contains diagram_id and 6 text fields

    Returns:
        Success response with updated diagram_id
    """
    logger.info(f"Saving sequential texts for diagram {request.diagram_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Update diagram with all 6 texts
            update_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET ocr_text_1 = :ocr_text_1,
                    ocr_text_2 = :ocr_text_2,
                    ocr_text_3 = :ocr_text_3,
                    manual_text_1 = :manual_text_1,
                    manual_text_2 = :manual_text_2,
                    manual_text_3 = :manual_text_3,
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            result = db.execute(update_sql, {
                "ocr_text_1": request.ocr_text_1,
                "ocr_text_2": request.ocr_text_2,
                "ocr_text_3": request.ocr_text_3,
                "manual_text_1": request.manual_text_1,
                "manual_text_2": request.manual_text_2,
                "manual_text_3": request.manual_text_3,
                "diagram_id": request.diagram_id
            })

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Diagram not found")

            db.commit()

            return {
                "success": True,
                "message": "Sequential texts saved successfully",
                "diagram_id": request.diagram_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save sequential texts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# To add these endpoints to ocr.py, append the following at the end of the file:
#
# @router.post("/ocr/extract-sequential", response_model=ExtractSequentialResponse)
# async def extract_sequential_ocr_endpoint(request: ExtractSequentialRequest):
#     from .ocr_sequential_extension import extract_sequential_ocr
#     return await extract_sequential_ocr(request)
#
# @router.post("/sequential-texts/save")
# async def save_sequential_texts_endpoint(request: SaveSequentialTextsRequest):
#     from .ocr_sequential_extension import save_sequential_texts
#     return await save_sequential_texts(request)
