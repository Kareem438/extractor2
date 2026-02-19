"""
API routes for managing user-selected image clips (paragraphs and diagrams)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from src.database.connection import engine
from src.utils.sanitization import get_table_prefix_from_book_id
import base64
from datetime import datetime

router = APIRouter()


class SaveImageClipRequest(BaseModel):
    """Request to save an image clip"""
    book_id: int
    page_number: int
    clip_type: str  # 'paragraph' or 'diagram'

    # Selection coordinates
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int

    # Image data (base64 encoded)
    image_data_base64: str
    image_format: str = 'png'

    # Optional metadata
    user_notes: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    created_by: Optional[str] = 'user'
    level: Optional[str] = 'Level 1'  # Default to Level 1

    # Optional display order (for merged clips)
    display_order: Optional[int] = None

    # Selected level from radio buttons (1-5)
    selected_level_number: Optional[int] = None
    selected_level_text: Optional[str] = None

    # OCR extracted text (from auto-OCR)
    extracted_text: Optional[str] = None


class ImageClipResponse(BaseModel):
    """Response with image clip data"""
    id: int
    page_number: int
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int
    image_data_base64: str
    image_format: str
    image_width: int
    image_height: int
    user_notes: Optional[str]
    description: Optional[str]
    category: Optional[str]
    approval_status: str
    created_at: datetime


@router.post("/api/save-image-clip")
async def save_image_clip(request: SaveImageClipRequest):
    """
    Save a user-selected image clip to either paragraph_images or diagram_images table
    """
    try:
        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Determine target table
        if request.clip_type == 'paragraph':
            table_name = f"raw_{table_prefix}_paragraph_images"
        else:
            table_name = f"raw_{table_prefix}_diagram_images"

        # Decode base64 image data
        try:
            # Remove data URL prefix if present (e.g., "data:image/png;base64,")
            image_data_base64 = request.image_data_base64
            if ',' in image_data_base64:
                image_data_base64 = image_data_base64.split(',', 1)[1]

            image_bytes = base64.b64decode(image_data_base64)
            image_size_bytes = len(image_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")

        # Get raw_page_id for this page
        raw_pages_table = f"raw_{table_prefix}_pages"
        get_page_id_sql = text(f"""
            SELECT id FROM {raw_pages_table}
            WHERE page_number = :page_number
            LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(get_page_id_sql, {"page_number": request.page_number})
            row = result.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Page {request.page_number} not found in raw pages table"
                )

            raw_page_id = row[0]

        # Calculate image dimensions from selection size (these are the natural dimensions)
        image_width = request.selection_width
        image_height = request.selection_height

        # Determine display_order: use provided value or calculate max + 1
        if request.display_order is not None:
            # Use the provided display_order (for merged clips)
            display_order_value = request.display_order
        else:
            # Get the next display_order value (max + 1) for new clips
            get_max_order_sql = text(f"""
                SELECT COALESCE(MAX(display_order), 0) + 1
                FROM {table_name}
            """)

            with engine.connect() as conn:
                result = conn.execute(get_max_order_sql)
                display_order_value = result.scalar()

        # Insert into appropriate table
        insert_sql = text(f"""
            INSERT INTO {table_name} (
                raw_page_id,
                page_number,
                selection_x,
                selection_y,
                selection_width,
                selection_height,
                image_data,
                image_format,
                image_width,
                image_height,
                image_size_bytes,
                user_notes,
                description,
                category,
                created_by,
                display_order,
                is_enabled,
                approval_status,
                level,
                selected_level_number,
                selected_level_text,
                extracted_text
            ) VALUES (
                :raw_page_id,
                :page_number,
                :selection_x,
                :selection_y,
                :selection_width,
                :selection_height,
                :image_data,
                :image_format,
                :image_width,
                :image_height,
                :image_size_bytes,
                :user_notes,
                :description,
                :category,
                :created_by,
                :display_order,
                TRUE,
                'new',
                :level,
                :selected_level_number,
                :selected_level_text,
                :extracted_text
            )
            RETURNING id
        """)

        with engine.connect() as conn:
            result = conn.execute(insert_sql, {
                "raw_page_id": raw_page_id,
                "page_number": request.page_number,
                "selection_x": request.selection_x,
                "selection_y": request.selection_y,
                "selection_width": request.selection_width,
                "selection_height": request.selection_height,
                "image_data": image_bytes,
                "image_format": request.image_format,
                "image_width": image_width,
                "image_height": image_height,
                "image_size_bytes": image_size_bytes,
                "user_notes": request.user_notes,
                "level": request.level,
                "description": request.description,
                "category": request.category,
                "created_by": request.created_by,
                "display_order": display_order_value,
                "selected_level_number": request.selected_level_number,
                "selected_level_text": request.selected_level_text,
                "extracted_text": request.extracted_text
            })
            conn.commit()

            clip_id = result.fetchone()[0]

        return {
            "success": True,
            "clip_id": clip_id,
            "clip_type": request.clip_type,
            "message": f"Image clip saved successfully to {table_name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image clip: {str(e)}")


@router.get("/api/recent-image-clips/{book_id}")
async def get_recent_image_clips(book_id: int, page_number: Optional[int] = None, limit: int = 5):
    """
    Get recent image clips from both paragraph and diagram tables

    Args:
        book_id: The book ID
        page_number: Optional - filter by page number
        limit: Number of recent clips to return per table (default 5)
    """
    try:
        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(book_id)

        paragraph_table = f"raw_{table_prefix}_paragraph_images"
        diagram_table = f"raw_{table_prefix}_diagram_images"

        # Build WHERE clause for page filter (always filter by is_enabled)
        where_clause = "WHERE is_enabled = TRUE"
        params = {"limit": limit}
        if page_number is not None:
            where_clause += " AND page_number = :page_number"
            params["page_number"] = page_number

        # Get recent paragraph clips (newest first)
        paragraph_sql = text(f"""
            SELECT
                id,
                page_number,
                selection_x,
                selection_y,
                selection_width,
                selection_height,
                image_data,
                image_format,
                image_width,
                image_height,
                user_notes,
                description,
                category,
                approval_status,
                created_at,
                display_order,
                is_enabled,
                level
            FROM {paragraph_table}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        # Get recent diagram clips (newest first)
        diagram_sql = text(f"""
            SELECT
                id,
                page_number,
                selection_x,
                selection_y,
                selection_width,
                selection_height,
                image_data,
                image_format,
                image_width,
                image_height,
                user_notes,
                description,
                category,
                approval_status,
                created_at,
                display_order,
                is_enabled,
                level
            FROM {diagram_table}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        with engine.connect() as conn:
            # Fetch paragraph clips
            paragraph_result = conn.execute(paragraph_sql, params)
            paragraph_rows = paragraph_result.fetchall()

            # Fetch diagram clips
            diagram_result = conn.execute(diagram_sql, params)
            diagram_rows = diagram_result.fetchall()

        # Convert to response format
        def row_to_dict(row):
            return {
                "id": row[0],
                "page_number": row[1],
                "selection_x": row[2],
                "selection_y": row[3],
                "selection_width": row[4],
                "selection_height": row[5],
                "image_data_base64": base64.b64encode(row[6]).decode('utf-8'),
                "image_format": row[7],
                "image_width": row[8],
                "image_height": row[9],
                "user_notes": row[10],
                "description": row[11],
                "category": row[12],
                "approval_status": row[13],
                "created_at": row[14].isoformat() if row[14] else None,
                "display_order": row[15],
                "is_enabled": row[16],
                "level": row[17]
            }

        paragraph_clips = [row_to_dict(row) for row in paragraph_rows]
        diagram_clips = [row_to_dict(row) for row in diagram_rows]

        return {
            "success": True,
            "book_id": book_id,
            "page_number": page_number,
            "paragraph_clips": paragraph_clips,
            "diagram_clips": diagram_clips
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch image clips: {str(e)}")


@router.patch("/api/disable-image-clip/{clip_type}/{clip_id}")
async def disable_image_clip(clip_type: str, clip_id: int):
    """
    Disable an image clip by setting is_enabled = FALSE
    (used when merging clips to keep them in DB but hide from view)

    Args:
        clip_type: 'paragraph' or 'diagram'
        clip_id: The ID of the clip to disable
    """
    try:
        # Validate clip type
        if clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get all books to find which one has this clip
        get_books_sql = text("SELECT book_id, table_prefix FROM books_metadata")

        with engine.connect() as conn:
            books_result = conn.execute(get_books_sql)
            books = books_result.fetchall()

        clip_found = False
        clip_book_id = None
        table_name = None

        # Search for the clip in each book's table
        for book_id_row, table_prefix in books:
            test_table_name = f"raw_{table_prefix}_{clip_type}_images"

            # Check if clip exists in this table
            check_sql = text(f"""
                SELECT book_id FROM books_metadata
                WHERE book_id = :book_id
                AND EXISTS (
                    SELECT 1 FROM {test_table_name} WHERE id = :clip_id
                )
            """)

            with engine.connect() as conn:
                result = conn.execute(check_sql, {"book_id": book_id_row, "clip_id": clip_id})
                row = result.fetchone()

                if row:
                    clip_found = True
                    clip_book_id = book_id_row
                    table_name = test_table_name
                    break

        if not clip_found:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

        # Disable the clip
        disable_sql = text(f"""
            UPDATE {table_name}
            SET is_enabled = FALSE,
                updated_at = NOW()
            WHERE id = :clip_id
            RETURNING id
        """)

        with engine.connect() as conn:
            result = conn.execute(disable_sql, {"clip_id": clip_id})
            conn.commit()
            disabled_row = result.fetchone()

            if not disabled_row:
                raise HTTPException(status_code=404, detail=f"Failed to disable clip {clip_id}")

        return {
            "success": True,
            "message": f"Clip {clip_id} disabled successfully",
            "clip_id": clip_id,
            "clip_type": clip_type,
            "book_id": clip_book_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable image clip: {str(e)}")


@router.delete("/api/delete-image-clip/{clip_type}/{clip_id}")
async def delete_image_clip(clip_type: str, clip_id: int, book_id: int = None):
    """
    Delete an image clip from either paragraph_images or diagram_images table

    Args:
        clip_type: 'paragraph' or 'diagram'
        clip_id: The ID of the clip to delete
        book_id: Optional - if provided, validates the clip belongs to this book
    """
    try:
        # Validate clip type
        if clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # First, get the clip to find out which book it belongs to
        # We need to determine the table name, but we don't know the book yet
        # So we'll query books_metadata to get all possible table prefixes

        # Get all books to find which one has this clip
        from sqlalchemy import text
        from src.database.connection import engine

        get_books_sql = text("SELECT book_id, table_prefix FROM books_metadata")

        with engine.connect() as conn:
            books_result = conn.execute(get_books_sql)
            books = books_result.fetchall()

        clip_found = False
        clip_book_id = None
        table_name = None

        # Search for the clip in each book's table
        for book_id_row, table_prefix in books:
            test_table_name = f"raw_{table_prefix}_{clip_type}_images"

            # Check if clip exists in this table
            check_sql = text(f"""
                SELECT book_id FROM books_metadata
                WHERE book_id = :book_id
                AND EXISTS (
                    SELECT 1 FROM {test_table_name} WHERE id = :clip_id
                )
            """)

            with engine.connect() as conn:
                result = conn.execute(check_sql, {"book_id": book_id_row, "clip_id": clip_id})
                row = result.fetchone()

                if row:
                    clip_found = True
                    clip_book_id = book_id_row
                    table_name = test_table_name
                    break

        if not clip_found:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

        # Delete the clip
        delete_sql = text(f"""
            DELETE FROM {table_name}
            WHERE id = :clip_id
            RETURNING id
        """)

        with engine.connect() as conn:
            result = conn.execute(delete_sql, {"clip_id": clip_id})
            conn.commit()
            deleted_row = result.fetchone()

            if not deleted_row:
                raise HTTPException(status_code=404, detail=f"Failed to delete clip {clip_id}")

        return {
            "success": True,
            "message": f"Clip {clip_id} deleted successfully",
            "clip_id": clip_id,
            "clip_type": clip_type,
            "book_id": clip_book_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image clip: {str(e)}")


@router.get("/api/all-image-clips/{book_id}")
async def get_all_image_clips(book_id: int, clip_type: Optional[str] = None):
    """
    Get all image clips for a book (no limit)

    Args:
        book_id: The book ID
        clip_type: Optional - 'paragraph' or 'diagram' to filter by type
    """
    try:
        # V2 books don't have paragraph/diagram image tables
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"clips": [], "total": 0, "message": "V2 books use cloud extraction, no image clips"}

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(book_id)

        clips_data = []

        # Determine which tables to query
        if clip_type == 'paragraph':
            tables_to_query = [('paragraph', f"raw_{table_prefix}_paragraph_images")]
        elif clip_type == 'diagram':
            tables_to_query = [('diagram', f"raw_{table_prefix}_diagram_images")]
        else:
            # Query both tables
            tables_to_query = [
                ('paragraph', f"raw_{table_prefix}_paragraph_images"),
                ('diagram', f"raw_{table_prefix}_diagram_images")
            ]

        for clip_type_name, table_name in tables_to_query:
            # Use different confidence column name for paragraphs vs diagrams
            confidence_col = 'ocr_confidence' if clip_type_name == 'paragraph' else 'ai_confidence'

            # Get all enabled clips from this table, ordered by display_order
            sql = text(f"""
                SELECT
                    id,
                    page_number,
                    selection_x,
                    selection_y,
                    selection_width,
                    selection_height,
                    image_data,
                    image_format,
                    image_width,
                    image_height,
                    user_notes,
                    description,
                    category,
                    approval_status,
                    created_at,
                    display_order,
                    is_enabled,
                    level,
                    raw_page_id,
                    updated_at,
                    linked_knowledge_unit_id,
                    image_size_bytes,
                    created_by,
                    selected_level_number,
                    selected_level_text,
                    extracted_text,
                    {confidence_col} as confidence,
                    tags,
                    level_1_title,
                    level_2_title,
                    level_3_title,
                    level_4_title
                FROM {table_name}
                WHERE is_enabled = TRUE
                ORDER BY display_order ASC, created_at DESC
            """)

            with engine.connect() as conn:
                result = conn.execute(sql)
                rows = result.fetchall()

            # Convert to response format
            for row in rows:
                clips_data.append({
                    "id": row[0],
                    "page_number": row[1],
                    "selection_x": row[2],
                    "selection_y": row[3],
                    "selection_width": row[4],
                    "selection_height": row[5],
                    "image_data_base64": base64.b64encode(row[6]).decode('utf-8'),
                    "image_format": row[7],
                    "image_width": row[8],
                    "image_height": row[9],
                    "user_notes": row[10],
                    "description": row[11],
                    "category": row[12],
                    "approval_status": row[13],
                    "created_at": row[14].isoformat() if row[14] else None,
                    "display_order": row[15],
                    "is_enabled": row[16],
                    "level": row[17],
                    "clip_type": clip_type_name,
                    "raw_page_id": row[18],
                    "updated_at": row[19].isoformat() if row[19] else None,
                    "linked_knowledge_unit_id": row[20],
                    "image_size_bytes": row[21],
                    "created_by": row[22],
                    "selected_level_number": row[23],
                    "selected_level_text": row[24],
                    "extracted_text": row[25],
                    "ocr_confidence": row[26],  # unified as 'confidence' in query
                    "tags": row[27],
                    "level_1_title": row[28],
                    "level_2_title": row[29],
                    "level_3_title": row[30],
                    "level_4_title": row[31]
                })

        return {
            "success": True,
            "book_id": book_id,
            "clip_type": clip_type,
            "total_clips": len(clips_data),
            "clips": clips_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch image clips: {str(e)}")


class UpdateClipStatusRequest(BaseModel):
    """Request to update clip approval status"""
    book_id: int
    clip_type: str  # 'paragraph' or 'diagram'
    clip_id: int
    approval_status: str  # e.g., 'pending', 'approved', 'rejected', 'reviewed'


@router.patch("/api/update-clip-status")
async def update_clip_status(request: UpdateClipStatusRequest):
    """
    Update the approval status of an image clip

    Args:
        request: UpdateClipStatusRequest with book_id, clip_type, clip_id, and new status
    """
    try:
        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine target table
        table_name = f"raw_{table_prefix}_{request.clip_type}_images"

        # Update the status
        update_sql = text(f"""
            UPDATE {table_name}
            SET approval_status = :approval_status,
                updated_at = NOW()
            WHERE id = :clip_id
            RETURNING id, approval_status
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, {
                "approval_status": request.approval_status,
                "clip_id": request.clip_id
            })
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clip {request.clip_id} not found in {table_name}"
                )

        return {
            "success": True,
            "message": f"Clip status updated successfully",
            "clip_id": request.clip_id,
            "clip_type": request.clip_type,
            "approval_status": request.approval_status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update clip status: {str(e)}")


class UpdateDisplayOrderRequest(BaseModel):
    """Request to update display order of an image clip"""
    book_id: int
    clip_type: str  # 'paragraph' or 'diagram'
    clip_id: int
    display_order: int


@router.patch("/api/update-clip-display-order")
async def update_clip_display_order(request: UpdateDisplayOrderRequest):
    """
    Update the display order of an image clip

    Args:
        request: UpdateDisplayOrderRequest with book_id, clip_type, clip_id, and new display_order
    """
    try:
        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine target table
        table_name = f"raw_{table_prefix}_{request.clip_type}_images"

        # Update the display order
        update_sql = text(f"""
            UPDATE {table_name}
            SET display_order = :display_order,
                updated_at = NOW()
            WHERE id = :clip_id
            RETURNING id, display_order
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, {
                "display_order": request.display_order,
                "clip_id": request.clip_id
            })
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clip {request.clip_id} not found in {table_name}"
                )

        return {
            "success": True,
            "message": f"Clip display order updated successfully",
            "clip_id": request.clip_id,
            "clip_type": request.clip_type,
            "display_order": request.display_order
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update display order: {str(e)}")


class UpdateLevelRequest(BaseModel):
    """Request to update level of an image clip"""
    book_id: int
    clip_type: str  # 'paragraph' or 'diagram'
    clip_id: int
    level: str


@router.patch("/api/update-clip-level")
async def update_clip_level(request: UpdateLevelRequest):
    """
    Update the level of an image clip

    Args:
        request: UpdateLevelRequest with book_id, clip_type, clip_id, and new level
    """
    try:
        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine target table
        table_name = f"raw_{table_prefix}_{request.clip_type}_images"

        # Update the level
        update_sql = text(f"""
            UPDATE {table_name}
            SET level = :level,
                updated_at = NOW()
            WHERE id = :clip_id
            RETURNING id, level
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, {
                "level": request.level,
                "clip_id": request.clip_id
            })
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clip {request.clip_id} not found in {table_name}"
                )

        return {
            "success": True,
            "message": f"Clip level updated successfully",
            "clip_id": request.clip_id,
            "clip_type": request.clip_type,
            "level": request.level
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update level: {str(e)}")


class UpdateEnabledRequest(BaseModel):
    """Request to update is_enabled of an image clip"""
    book_id: int
    clip_type: str  # 'paragraph' or 'diagram'
    clip_id: int
    is_enabled: bool


@router.patch("/api/update-clip-enabled")
async def update_clip_enabled(request: UpdateEnabledRequest):
    """
    Update the is_enabled status of an image clip

    Args:
        request: UpdateEnabledRequest with book_id, clip_type, clip_id, and new is_enabled status
    """
    try:
        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine target table
        table_name = f"raw_{table_prefix}_{request.clip_type}_images"

        # Update the is_enabled flag
        update_sql = text(f"""
            UPDATE {table_name}
            SET is_enabled = :is_enabled,
                updated_at = NOW()
            WHERE id = :clip_id
            RETURNING id, is_enabled
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, {
                "is_enabled": request.is_enabled,
                "clip_id": request.clip_id
            })
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clip {request.clip_id} not found in {table_name}"
                )

        return {
            "success": True,
            "message": f"Clip enabled status updated successfully",
            "clip_id": request.clip_id,
            "clip_type": request.clip_type,
            "is_enabled": request.is_enabled
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update enabled status: {str(e)}")


class UpdateClipDetailsRequest(BaseModel):
    """Request to update multiple editable fields of an image clip"""
    book_id: int
    clip_id: int
    clip_type: str  # 'paragraph' or 'diagram'

    # Editable fields (all optional)
    approval_status: Optional[str] = None
    display_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    level: Optional[str] = None
    category: Optional[str] = None
    created_by: Optional[str] = None
    selected_level_number: Optional[int] = None
    selected_level_text: Optional[str] = None
    description: Optional[str] = None
    user_notes: Optional[str] = None
    extracted_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    tags: Optional[str] = None
    level_1_title: Optional[str] = None
    level_2_title: Optional[str] = None
    level_3_title: Optional[str] = None
    level_4_title: Optional[str] = None


@router.patch("/api/update-clip-details")
async def update_clip_details(request: UpdateClipDetailsRequest):
    """
    Update multiple editable fields of an image clip at once.
    Only fields that are provided (not None) will be updated.

    Args:
        request: UpdateClipDetailsRequest with book_id, clip_id, clip_type, and editable fields
    """
    try:
        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine target table
        table_name = f"raw_{table_prefix}_{request.clip_type}_images"

        # Build dynamic SET clause based on provided fields
        update_fields = []
        params = {"clip_id": request.clip_id}

        editable_fields = {
            'approval_status': request.approval_status,
            'display_order': request.display_order,
            'is_enabled': request.is_enabled,
            'level': request.level,
            'category': request.category,
            'created_by': request.created_by,
            'selected_level_number': request.selected_level_number,
            'selected_level_text': request.selected_level_text,
            'description': request.description,
            'user_notes': request.user_notes,
            'extracted_text': request.extracted_text,
            'ocr_confidence': request.ocr_confidence,
            'tags': request.tags,
            'level_1_title': request.level_1_title,
            'level_2_title': request.level_2_title,
            'level_3_title': request.level_3_title,
            'level_4_title': request.level_4_title
        }

        for field_name, field_value in editable_fields.items():
            if field_value is not None:
                update_fields.append(f"{field_name} = :{field_name}")
                params[field_name] = field_value

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # Always update the updated_at timestamp
        update_fields.append("updated_at = NOW()")

        # Build and execute the update query
        set_clause = ", ".join(update_fields)
        update_sql = text(f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE id = :clip_id
            RETURNING id
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, params)
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clip {request.clip_id} not found in {table_name}"
                )

        return {
            "success": True,
            "message": "Clip details updated successfully",
            "clip_id": request.clip_id,
            "clip_type": request.clip_type,
            "updated_fields": list(editable_fields.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update clip details: {str(e)}")


class UpdatePageLevelTitlesRequest(BaseModel):
    """Request to update level titles for all items on a page"""
    book_id: int
    page_number: int
    level_1_title: Optional[str] = None
    level_2_title: Optional[str] = None
    level_3_title: Optional[str] = None
    level_4_title: Optional[str] = None


class UpdateSingleAttributeRequest(BaseModel):
    """Request to update a single attribute value"""
    book_id: int
    clip_id: int
    clip_type: str  # 'paragraph' or 'diagram'
    attr_number: int  # 1-80
    attr_value: Optional[str] = None


@router.patch("/api/update-page-level-titles")
async def update_page_level_titles(request: UpdatePageLevelTitlesRequest):
    """
    Update level titles for ALL paragraphs and diagrams on a specific page

    This is used by the "Load Titles" feature to apply titles to all items on the page
    """
    try:
        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        paragraph_table = f"raw_{table_prefix}_paragraph_images"
        diagram_table = f"raw_{table_prefix}_diagram_images"

        # Build UPDATE query
        update_sql_template = """
            UPDATE {table_name}
            SET
                level_1_title = :level_1_title,
                level_2_title = :level_2_title,
                level_3_title = :level_3_title,
                level_4_title = :level_4_title,
                updated_at = CURRENT_TIMESTAMP
            WHERE page_number = :page_number
        """

        params = {
            "level_1_title": request.level_1_title,
            "level_2_title": request.level_2_title,
            "level_3_title": request.level_3_title,
            "level_4_title": request.level_4_title,
            "page_number": request.page_number
        }

        total_updated = 0

        with engine.connect() as conn:
            # Update paragraphs
            paragraph_update_sql = text(update_sql_template.format(table_name=paragraph_table))
            paragraph_result = conn.execute(paragraph_update_sql, params)
            paragraph_count = paragraph_result.rowcount

            # Update diagrams
            diagram_update_sql = text(update_sql_template.format(table_name=diagram_table))
            diagram_result = conn.execute(diagram_update_sql, params)
            diagram_count = diagram_result.rowcount

            conn.commit()
            total_updated = paragraph_count + diagram_count

        return {
            "success": True,
            "message": f"Updated level titles for {total_updated} items on page {request.page_number}",
            "book_id": request.book_id,
            "page_number": request.page_number,
            "paragraphs_updated": paragraph_count,
            "diagrams_updated": diagram_count,
            "total_updated": total_updated
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update page level titles: {str(e)}")


@router.patch("/api/update-single-attribute")
async def update_single_attribute(request: UpdateSingleAttributeRequest):
    """
    Update a single attribute value (attr1_value through attr80_value) for a clip.

    The attribute is stored in the linked knowledge_unit if one exists,
    otherwise the operation will fail.

    Args:
        request: UpdateSingleAttributeRequest with book_id, clip_id, clip_type, attr_number, and attr_value
    """
    try:
        # Validate attr_number
        if request.attr_number < 1 or request.attr_number > 80:
            raise HTTPException(status_code=400, detail="attr_number must be between 1 and 80")

        # Validate clip type
        if request.clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(request.book_id)

        # Determine source table
        clip_table = f"raw_{table_prefix}_{request.clip_type}_images"
        ku_table = f"{table_prefix}_knowledge_units"

        # Get the linked_knowledge_unit_id for this clip
        get_ku_id_sql = text(f"""
            SELECT linked_knowledge_unit_id
            FROM {clip_table}
            WHERE id = :clip_id
        """)

        with engine.connect() as conn:
            result = conn.execute(get_ku_id_sql, {"clip_id": request.clip_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"Clip {request.clip_id} not found")

            ku_id = row[0]

            if not ku_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Clip {request.clip_id} has no linked knowledge unit. Cannot update attributes."
                )

        # Update the attribute in knowledge_units table
        attr_column = f"attr{request.attr_number}_value"
        update_sql = text(f"""
            UPDATE {ku_table}
            SET {attr_column} = :attr_value
            WHERE unit_id = :ku_id
            RETURNING unit_id
        """)

        with engine.connect() as conn:
            result = conn.execute(update_sql, {
                "attr_value": request.attr_value,
                "ku_id": ku_id
            })
            conn.commit()

            updated_row = result.fetchone()

            if not updated_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Knowledge unit {ku_id} not found"
                )

        return {
            "success": True,
            "message": f"Attribute {request.attr_number} updated successfully",
            "clip_id": request.clip_id,
            "knowledge_unit_id": ku_id,
            "attr_number": request.attr_number
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update attribute: {str(e)}")


@router.get("/api/clip-with-attributes/{book_id}/{clip_type}/{clip_id}")
async def get_clip_with_attributes(book_id: int, clip_type: str, clip_id: int):
    """
    Get a clip with all its attribute values from the linked knowledge unit.
    Also returns attribute names from the attribute_keys table.

    Args:
        book_id: The book ID
        clip_type: 'paragraph' or 'diagram'
        clip_id: The clip ID
    """
    try:
        # Validate clip type
        if clip_type not in ['paragraph', 'diagram']:
            raise HTTPException(status_code=400, detail="clip_type must be 'paragraph' or 'diagram'")

        # Get table prefix for this book
        table_prefix = get_table_prefix_from_book_id(book_id)

        clip_table = f"raw_{table_prefix}_{clip_type}_images"
        ku_table = f"{table_prefix}_knowledge_units"
        attr_keys_table = f"{table_prefix}_attribute_keys"

        # Get the linked_knowledge_unit_id for this clip
        get_ku_id_sql = text(f"""
            SELECT linked_knowledge_unit_id
            FROM {clip_table}
            WHERE id = :clip_id
        """)

        with engine.connect() as conn:
            result = conn.execute(get_ku_id_sql, {"clip_id": clip_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

            ku_id = row[0]

        # Build attribute column list
        attr_columns = ", ".join([f"attr{i}_value" for i in range(1, 81)])

        # Get all attribute values from knowledge unit
        attributes = {}
        if ku_id:
            get_attrs_sql = text(f"""
                SELECT {attr_columns}
                FROM {ku_table}
                WHERE unit_id = :ku_id
            """)

            with engine.connect() as conn:
                result = conn.execute(get_attrs_sql, {"ku_id": ku_id})
                row = result.fetchone()

                if row:
                    for i in range(1, 81):
                        attributes[f"attr{i}_value"] = row[i-1]

        # Get attribute names
        get_names_sql = text(f"""
            SELECT attr_number, key_name, is_system_reserved
            FROM {attr_keys_table}
            ORDER BY attr_number
        """)

        attribute_names = {}
        with engine.connect() as conn:
            result = conn.execute(get_names_sql)
            rows = result.fetchall()

            for row in rows:
                attribute_names[row[0]] = {
                    "key_name": row[1],
                    "is_system_reserved": row[2]
                }

        return {
            "success": True,
            "clip_id": clip_id,
            "clip_type": clip_type,
            "knowledge_unit_id": ku_id,
            "attributes": attributes,
            "attribute_names": attribute_names
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get clip attributes: {str(e)}")
