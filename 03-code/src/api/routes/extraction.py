"""
Extraction API Routes

Handles knowledge unit extraction from Layout Review regions:
- Page selection and status
- Paragraph OCR extraction (Surya)
- Diagram/table/equation/list image extraction
- Claude batch and direct decoding
- Summary by L3 title
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import json
import asyncio

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class PageSelection(BaseModel):
    selected_pages: List[int]


class ExtractionRequest(BaseModel):
    page_numbers: List[int]


class PreviewDecodeRequest(BaseModel):
    diagram_id: int
    prompt: str


class PromptsUpdate(BaseModel):
    diagram: Optional[str] = None
    table: Optional[str] = None
    equation: Optional[str] = None
    list_bulleted: Optional[str] = None
    list_numbered: Optional[str] = None
    list_lettered: Optional[str] = None


# =============================================================================
# Default Prompts
# =============================================================================

DEFAULT_PROMPTS = {
    "diagram": "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
    "table": "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
    "equation": "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
    "list_bulleted": "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
    "list_numbered": "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
    "list_lettered": "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items.",
    "question": "Analyze this question image. Extract the full question text, identify any sub-questions or parts, and note any diagrams or figures referenced.",
    "answer": "Analyze this answer image. Extract the complete answer or solution, including any steps, explanations, formulas, or diagrams shown."
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_book_table_prefix(db, book_id: int) -> str:
    """Get the table prefix for a book."""
    result = db.execute(
        text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Book not found")

    return result[0]


def get_auto_slicer_config(db, book_id: int) -> dict:
    """Get auto-slicer config for a book."""
    result = db.execute(
        text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result or not result[0]:
        return {}

    return result[0] if isinstance(result[0], dict) else json.loads(result[0])


def get_layout_detection_config(db, book_id: int) -> dict:
    """Get layout detection config for a book (contains ready_for_extraction status)."""
    result = db.execute(
        text("SELECT layout_detection_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result or not result[0]:
        return {}

    return result[0] if isinstance(result[0], dict) else json.loads(result[0])


def save_auto_slicer_config(db, book_id: int, config: dict):
    """Save auto-slicer config for a book."""
    db.execute(
        text("UPDATE books_metadata SET auto_slicer_config = :config WHERE book_id = :book_id"),
        {"book_id": book_id, "config": json.dumps(config)}
    )
    db.commit()


# =============================================================================
# Page Selection Endpoints
# =============================================================================

@router.get("/extraction/{book_id}/ready-pages")
async def get_ready_pages(book_id: int):
    """Get pages that are ready for extraction from Layout Review."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        # Use layout_detection_config which is where ready_for_extraction is saved
        layout_config = get_layout_detection_config(db, book_id)

        # Get pages marked as ready for extraction (stored as dict with string keys)
        ready_for_extraction = layout_config.get('ready_for_extraction', {})
        # Convert dict to list of page numbers where value is True
        ready_pages = [int(page) for page, is_ready in ready_for_extraction.items() if is_ready]

        if not ready_pages:
            return {"pages": []}

        # Get region counts per page from layout_detections table
        regions_table = f"raw_{prefix}_layout_detections"

        # Check if table exists
        table_check = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": regions_table}
        ).scalar()

        if not table_check:
            return {"pages": []}

        # Get counts per page
        pages_data = []
        # Get auto_slicer_config for extracted_pages status
        auto_config = get_auto_slicer_config(db, book_id)
        extracted_pages = auto_config.get('extracted_pages', [])
        
        for page_num in sorted(ready_pages):
            # Get region counts by class
            counts = db.execute(
                text(f"""
                    SELECT
                        class_name,
                        COUNT(*) as count
                    FROM {regions_table}
                    WHERE page_number = :page_num
                    GROUP BY class_name
                """),
                {"page_num": page_num}
            ).fetchall()

            count_dict = {row[0]: row[1] for row in counts}

            # Check if already extracted
            status = 'extracted' if page_num in extracted_pages else 'ready'

            pages_data.append({
                "page_number": page_num,
                "status": status,
                "paragraph_count": count_dict.get('paragraph', 0),
                "diagram_count": count_dict.get('diagram', 0),
                "table_count": count_dict.get('table', 0),
                "equation_count": count_dict.get('equation', 0),
                "list_count": (
                    count_dict.get('list_bulleted', 0) +
                    count_dict.get('list_numbered', 0) +
                    count_dict.get('list_lettered', 0)
                )
            })

        return {"pages": pages_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ready pages for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/extraction/{book_id}/page-selection")
async def get_page_selection(book_id: int):
    """Get saved page selection for extraction."""
    db = SessionLocal()
    try:
        config = get_auto_slicer_config(db, book_id)
        return {"selected_pages": config.get('extraction_page_selection', [])}
    except Exception as e:
        logger.error(f"Error getting page selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/extraction/{book_id}/page-selection")
async def save_page_selection(book_id: int, selection: PageSelection):
    """Save page selection for extraction."""
    db = SessionLocal()
    try:
        config = get_auto_slicer_config(db, book_id)
        config['extraction_page_selection'] = selection.selected_pages
        save_auto_slicer_config(db, book_id, config)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error saving page selection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Extraction Endpoints
# =============================================================================

@router.post("/extraction/{book_id}/extract")
async def start_extraction_endpoint(book_id: int, request: ExtractionRequest):
    """Start extraction process for selected pages."""
    from src.services.extraction_service import start_extraction as do_extraction

    try:
        if not request.page_numbers:
            raise HTTPException(status_code=400, detail="No pages selected")

        logger.info(f"Starting extraction for book {book_id}, pages: {request.page_numbers}")

        result = do_extraction(book_id, request.page_numbers)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction/{book_id}/extraction-status")
async def get_extraction_status_endpoint(book_id: int):
    """Get current extraction status."""
    from src.services.extraction_service import get_extraction_status

    try:
        return get_extraction_status(book_id)
    except Exception as e:
        logger.error(f"Error getting extraction status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extraction/{book_id}/cancel")
async def cancel_extraction_endpoint(book_id: int):
    """Cancel a running extraction job."""
    from src.services.extraction_service import cancel_extraction

    try:
        result = cancel_extraction(book_id)
        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Summary Endpoints
# =============================================================================

@router.get("/extraction/{book_id}/summary")
async def get_extraction_summary(book_id: int):
    """Get extraction summary grouped by L3 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)

        # Check if raw tables exist
        paragraphs_table = f"raw_{prefix}_paragraph_images"
        diagrams_table = f"raw_{prefix}_diagram_images"

        # Check if diagrams table exists (use diagrams for L3 grouping)
        diag_exists = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": diagrams_table}
        ).scalar()

        if not diag_exists:
            return {"summary": []}

        # Get summary by L3 title from diagrams (diagrams have proper L3 title column)
        summary_query = f"""
            SELECT
                COALESCE(level_3_title, '(No L3 Title)') as l3_title,
                MIN(page_number) as min_page,
                MAX(page_number) as max_page,
                0 as paragraph_count
            FROM {diagrams_table}
            GROUP BY level_3_title
            ORDER BY MIN(page_number)
        """

        results = db.execute(text(summary_query)).fetchall()

        summary = []
        for row in results:
            l3_title = row[0]
            min_page = row[1]
            max_page = row[2]
            para_count = row[3]

            # Get diagram counts for this L3 title
            diagram_counts = {"diagram": 0, "table": 0, "equation": 0, "list": 0}
            diagram_decoded = {"diagram": 0, "table": 0, "equation": 0, "list": 0}

            diagrams_exists = db.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = :table_name
                    )
                """),
                {"table_name": diagrams_table}
            ).scalar()

            if diagrams_exists:
                diag_query = f"""
                    SELECT
                        diagram_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN analyzed_at IS NOT NULL THEN 1 ELSE 0 END) as decoded_count
                    FROM {diagrams_table}
                    WHERE COALESCE(level_3_title, '(No L3 Title)') = :l3_title
                    GROUP BY diagram_type
                """
                diag_results = db.execute(text(diag_query), {"l3_title": l3_title}).fetchall()

                for diag_row in diag_results:
                    dtype = diag_row[0]
                    total = diag_row[1]
                    decoded = diag_row[2]

                    if dtype in ['list_bulleted', 'list_numbered', 'list_lettered']:
                        diagram_counts['list'] += total
                        diagram_decoded['list'] += decoded
                    elif dtype in diagram_counts:
                        diagram_counts[dtype] = total
                        diagram_decoded[dtype] = decoded

            summary.append({
                "l3_title": l3_title,
                "page_range": f"{min_page}-{max_page}" if min_page != max_page else str(min_page),
                "paragraphs": para_count,
                "diagrams_total": diagram_counts['diagram'],
                "diagrams_decoded": diagram_decoded['diagram'],
                "tables_total": diagram_counts['table'],
                "tables_decoded": diagram_decoded['table'],
                "equations_total": diagram_counts['equation'],
                "equations_decoded": diagram_decoded['equation'],
                "lists_total": diagram_counts['list'],
                "lists_decoded": diagram_decoded['list']
            })

        return {"summary": summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Prompt Management Endpoints
# =============================================================================

@router.get("/extraction/{book_id}/prompts")
async def get_prompts(book_id: int):
    """Get extraction prompts for the book."""
    db = SessionLocal()
    try:
        config = get_auto_slicer_config(db, book_id)
        prompts = config.get('extraction_prompts', {})

        # Merge with defaults
        result = {**DEFAULT_PROMPTS}
        result.update(prompts)

        return result

    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/extraction/{book_id}/prompts")
async def update_prompts(book_id: int, prompts: PromptsUpdate):
    """Update extraction prompts for the book."""
    db = SessionLocal()
    try:
        config = get_auto_slicer_config(db, book_id)

        if 'extraction_prompts' not in config:
            config['extraction_prompts'] = {}

        # Update only provided prompts
        prompts_dict = prompts.dict(exclude_none=True)
        config['extraction_prompts'].update(prompts_dict)

        save_auto_slicer_config(db, book_id, config)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error updating prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Decode Endpoints
# =============================================================================

class BatchDecodeRequest(BaseModel):
    diagram_ids: Optional[List[int]] = None


class DirectDecodeRequest(BaseModel):
    diagram_ids: Optional[List[int]] = None


@router.post("/extraction/{book_id}/decode-batch")
async def start_batch_decode(book_id: int, request: Optional[BatchDecodeRequest] = None):
    """Start Claude batch decoding for all unprocessed diagrams."""
    from src.services.claude_batch_service import submit_batch

    try:
        logger.info(f"Starting batch decode for book {book_id}")

        diagram_ids = request.diagram_ids if request else None
        result = submit_batch(book_id, diagram_ids)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch decode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extraction/{book_id}/decode-direct")
async def start_direct_decode_endpoint(book_id: int, request: Optional[DirectDecodeRequest] = None):
    """Start Claude direct decoding for all unprocessed diagrams."""
    from src.services.claude_batch_service import start_direct_decode

    try:
        logger.info(f"Starting direct decode for book {book_id}")

        diagram_ids = request.diagram_ids if request else None
        result = start_direct_decode(book_id, diagram_ids)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting direct decode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction/{book_id}/batch-status")
async def get_batch_status_endpoint(book_id: int, batch_id: Optional[str] = None):
    """Get status of a batch decode job."""
    from src.services.claude_batch_service import check_batch_status

    try:
        result = check_batch_status(book_id, batch_id)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extraction/{book_id}/batch-results")
async def retrieve_batch_results_endpoint(book_id: int, batch_id: Optional[str] = None):
    """Retrieve and process batch results, updating database."""
    from src.services.claude_batch_service import retrieve_batch_results

    try:
        result = retrieve_batch_results(book_id, batch_id)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Preview Endpoints
# =============================================================================

@router.get("/extraction/{book_id}/diagrams-for-preview")
async def get_diagrams_for_preview(book_id: int, type: Optional[str] = None):
    """Get diagrams available for preview/testing."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        # Check if table exists
        table_exists = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": diagrams_table}
        ).scalar()

        if not table_exists:
            return {"diagrams": []}

        # Build query
        query = f"""
            SELECT id, page_number, diagram_type, level_3_title,
                   CASE WHEN analyzed_at IS NOT NULL THEN TRUE ELSE FALSE END as decoded
            FROM {diagrams_table}
        """

        params = {}
        if type and type != 'all':
            if type == 'list':
                query += " AND diagram_type LIKE 'list_%'"
            else:
                query += " AND diagram_type = :type"
                params['type'] = type

        query += " ORDER BY page_number, id"

        results = db.execute(text(query), params).fetchall()

        diagrams = [{
            "id": row[0],
            "page_number": row[1],
            "diagram_type": row[2],
            "l3_title": row[3],
            "decoded": row[4]
        } for row in results]

        return {"diagrams": diagrams}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diagrams for preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/extraction/{book_id}/diagram-image/{diagram_id}")
async def get_diagram_image(book_id: int, diagram_id: int):
    """Get diagram image by ID."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        result = db.execute(
            text(f"SELECT image_data FROM {diagrams_table} WHERE id = :id"),
            {"id": diagram_id}
        ).fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Diagram not found")

        image_data = result[0]
        if isinstance(image_data, memoryview):
            image_data = bytes(image_data)

        return Response(content=image_data, media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diagram image: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/extraction/{book_id}/preview-decode")
async def preview_decode_endpoint(book_id: int, request: PreviewDecodeRequest):
    """Test decode a single diagram with a prompt."""
    from src.services.claude_batch_service import preview_decode

    try:
        logger.info(f"Preview decode for diagram {request.diagram_id}")

        result = preview_decode(book_id, request.diagram_id, request.prompt)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "diagram_id": request.diagram_id,
            "response": result.get('decoded_content', ''),
            "usage": result.get('usage', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preview decode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SaveDecodeRequest(BaseModel):
    diagram_id: int
    content: str


class StartExtractionRequest(BaseModel):
    api_mode: str = "batch"  # "batch" or "direct"
    page_numbers: List[int]


class EditDiagramRequest(BaseModel):
    extracted_text: str


class RedecodeRequest(BaseModel):
    prompt: str


# =============================================================================
# Dashboard Endpoints (Phase 3D)
# =============================================================================

@router.get("/extraction/{book_id}/dashboard")
async def get_dashboard_data(book_id: int):
    """Get all data needed for the extraction dashboard."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        auto_config = get_auto_slicer_config(db, book_id)
        layout_config = get_layout_detection_config(db, book_id)

        # Get ready pages from layout_detection_config (stored as dict with string keys)
        ready_for_extraction = layout_config.get('ready_for_extraction', {})
        ready_page_numbers = [int(page) for page, is_ready in ready_for_extraction.items() if is_ready]
        # Get extracted pages from auto_slicer_config
        extracted_pages = auto_config.get('extracted_pages', [])

        ready_pages = []
        regions_table = f"raw_{prefix}_layout_detections"
        diagrams_table = f"raw_{prefix}_diagram_images"
        paragraphs_table = f"raw_{prefix}_paragraph_images"

        # Check if layout_detections table exists
        regions_exists = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": regions_table}
        ).scalar()

        for page_num in sorted(ready_page_numbers):
            page_data = {
                "page_number": page_num,
                "ocr_complete": page_num in extracted_pages,
                "decode_complete": False,
                "regions": []
            }

            if regions_exists:
                # Get regions for thumbnail rendering
                regions = db.execute(
                    text(f"""
                        SELECT id, class_name, x, y, width, height
                        FROM {regions_table}
                        WHERE page_number = :page_num
                    """),
                    {"page_num": page_num}
                ).fetchall()

                page_data["regions"] = [{
                    "id": r[0],
                    "class_name": r[1],
                    "x": r[2],
                    "y": r[3],
                    "width": r[4],
                    "height": r[5]
                } for r in regions]

            ready_pages.append(page_data)

        # Get progress data
        paragraphs_count = 0
        paragraphs_ocr_complete = 0
        diagrams_count = 0
        diagrams_decoded = 0

        # Check if raw tables exist
        para_exists = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": paragraphs_table}
        ).scalar()

        diag_exists = db.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                )
            """),
            {"table_name": diagrams_table}
        ).scalar()

        if para_exists:
            para_stats = db.execute(
                text(f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN extracted_text IS NOT NULL AND extracted_text != '' THEN 1 ELSE 0 END) as ocr_complete
                    FROM {paragraphs_table}
                """)
            ).fetchone()
            paragraphs_count = para_stats[0] or 0
            paragraphs_ocr_complete = para_stats[1] or 0

        if diag_exists:
            diag_stats = db.execute(
                text(f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN extracted_text IS NOT NULL AND extracted_text != '' THEN 1 ELSE 0 END) as decoded
                    FROM {diagrams_table}
                """)
            ).fetchone()
            diagrams_count = diag_stats[0] or 0
            diagrams_decoded = diag_stats[1] or 0

        progress = {
            "paragraphs_ocr": {
                "completed": paragraphs_ocr_complete,
                "total": paragraphs_count
            },
            "diagrams_decode": {
                "completed": diagrams_decoded,
                "total": diagrams_count
            }
        }

        # Get summary by L3 title
        summary = []
        if diag_exists:
            summary_query = f"""
                SELECT
                    COALESCE(level_3_title, '(No L3 Title)') as l3_title,
                    SUM(CASE WHEN diagram_type = 'paragraph' THEN 1 ELSE 0 END) as paragraphs,
                    SUM(CASE WHEN diagram_type = 'diagram' THEN 1 ELSE 0 END) as diagrams,
                    SUM(CASE WHEN diagram_type = 'table' THEN 1 ELSE 0 END) as tables,
                    SUM(CASE WHEN diagram_type = 'equation' THEN 1 ELSE 0 END) as equations,
                    SUM(CASE WHEN diagram_type LIKE 'list_%' THEN 1 ELSE 0 END) as lists,
                    SUM(CASE WHEN diagram_type = 'question' THEN 1 ELSE 0 END) as questions,
                    SUM(CASE WHEN diagram_type = 'answer' THEN 1 ELSE 0 END) as answers
                FROM {diagrams_table}
                GROUP BY level_3_title
                ORDER BY MIN(page_number)
            """
            results = db.execute(text(summary_query)).fetchall()

            for row in results:
                summary.append({
                    "l3_title": row[0],
                    "paragraphs": row[1] or 0,
                    "diagrams": row[2] or 0,
                    "tables": row[3] or 0,
                    "equations": row[4] or 0,
                    "lists": row[5] or 0,
                    "questions": row[6] or 0,
                    "answers": row[7] or 0
                })

        # Add paragraph counts from paragraphs table
        if para_exists and summary:
            for item in summary:
                para_count = db.execute(
                    text(f"""
                        SELECT COUNT(*)
                        FROM {paragraphs_table}
                        WHERE COALESCE(level_3_title, '(No L3 Title)') = :l3_title
                    """),
                    {"l3_title": item["l3_title"]}
                ).scalar() or 0
                item["paragraphs"] = para_count

        # Get diagrams list
        diagrams = []
        if diag_exists:
            diag_query = f"""
                SELECT
                    id, page_number, diagram_type, level_3_title,
                    CASE
                        WHEN extracted_text IS NOT NULL AND extracted_text != '' THEN 'decoded'
                        ELSE 'pending'
                    END as status,
                    extracted_text
                FROM {diagrams_table}
                ORDER BY page_number, id
            """
            results = db.execute(text(diag_query)).fetchall()

            for row in results:
                diagrams.append({
                    "id": row[0],
                    "page_number": row[1],
                    "class_name": row[2],
                    "l3_title": row[3],
                    "status": row[4],
                    "extracted_text": row[5]
                })

        # Get prompts
        prompts = config.get('extraction_prompts', {})
        merged_prompts = {**DEFAULT_PROMPTS}
        merged_prompts.update(prompts)

        return {
            "ready_pages": ready_pages,
            "progress": progress,
            "summary": summary,
            "diagrams": diagrams,
            "prompts": merged_prompts
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/extraction/{book_id}/start")
async def start_extraction_with_mode(book_id: int, request: StartExtractionRequest):
    """Start extraction with specified API mode (batch or direct)."""
    from src.services.extraction_service import start_extraction as do_extraction

    try:
        if not request.page_numbers:
            raise HTTPException(status_code=400, detail="No pages selected")

        logger.info(f"Starting extraction for book {book_id}, pages: {request.page_numbers}, mode: {request.api_mode}")

        # First run OCR extraction
        result = do_extraction(book_id, request.page_numbers)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        # Then start decode based on mode
        if request.api_mode == "batch":
            from src.services.claude_batch_service import submit_batch
            decode_result = submit_batch(book_id, None)
        else:
            from src.services.claude_batch_service import start_direct_decode
            decode_result = start_direct_decode(book_id, None)

        result['decode_status'] = decode_result

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction/{book_id}/diagram/{diagram_id}/view")
async def get_diagram_details(book_id: int, diagram_id: int):
    """Get full details for a diagram including parent paragraph."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        result = db.execute(
            text(f"""
                SELECT
                    id, page_number, diagram_type, level_3_title,
                    extracted_text, linked_knowledge_unit_id
                FROM {diagrams_table}
                WHERE id = :id
            """),
            {"id": diagram_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Diagram not found")

        # Get parent paragraph text if linked
        parent_text = None
        if result[5]:  # linked_knowledge_unit_id
            paragraphs_table = f"raw_{prefix}_paragraph_images"
            para_result = db.execute(
                text(f"""
                    SELECT extracted_text
                    FROM {paragraphs_table}
                    WHERE id = :id
                """),
                {"id": result[5]}
            ).fetchone()
            if para_result:
                parent_text = para_result[0]

        return {
            "id": result[0],
            "page_number": result[1],
            "class_name": result[2],
            "l3_title": result[3],
            "extracted_text": result[4],
            "parent_paragraph": parent_text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diagram details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/extraction/{book_id}/diagram/{diagram_id}/edit")
async def edit_diagram_text(book_id: int, diagram_id: int, request: EditDiagramRequest):
    """Update the extracted_text for a diagram."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        db.execute(
            text(f"""
                UPDATE {diagrams_table}
                SET extracted_text = :text, analyzed_at = NOW()
                WHERE id = :id
            """),
            {"id": diagram_id, "text": request.extracted_text}
        )
        db.commit()

        return {"status": "ok", "diagram_id": diagram_id}

    except Exception as e:
        logger.error(f"Error editing diagram: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/extraction/{book_id}/diagram/{diagram_id}/redecode")
async def redecode_diagram(book_id: int, diagram_id: int, request: RedecodeRequest):
    """Re-decode a diagram with a custom prompt."""
    from src.services.claude_batch_service import preview_decode

    try:
        logger.info(f"Re-decoding diagram {diagram_id} with custom prompt")

        result = preview_decode(book_id, diagram_id, request.prompt)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "diagram_id": diagram_id,
            "result": result.get('decoded_content', ''),
            "usage": result.get('usage', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-decoding diagram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extraction/{book_id}/save-decode")
async def save_decode_endpoint(book_id: int, request: SaveDecodeRequest):
    """Save a decode result after preview."""
    from src.services.claude_batch_service import save_decode_result

    try:
        result = save_decode_result(book_id, request.diagram_id, request.content)

        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving decode result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket for Extraction Progress
# =============================================================================

@router.websocket("/ws/extraction/{book_id}")
async def extraction_websocket(websocket: WebSocket, book_id: int):
    """WebSocket endpoint for extraction progress updates."""
    from src.services.extraction_service import register_websocket, unregister_websocket

    await websocket.accept()
    register_websocket(book_id, websocket)

    try:
        # Keep connection alive
        while True:
            # Wait for messages from client (heartbeat/ping)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back for keep-alive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text('{"type":"heartbeat"}')

    except WebSocketDisconnect:
        logger.info(f"Extraction WebSocket disconnected for book {book_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        unregister_websocket(book_id, websocket)
