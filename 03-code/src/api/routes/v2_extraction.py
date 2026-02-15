"""
V2 Extraction API Routes

Endpoints for V2 cloud-based knowledge extraction:
- Start/pause/resume/cancel extraction
- Status and cost tracking
- Dry run for testing
- Prompt management
- Pre-requisite checks
- Few-shot example management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from src.services.v2_extraction_service import V2ExtractionService
from src.services.few_shot_service import FewShotService
from src.utils.logging_config import logger

router = APIRouter()
extraction_service = V2ExtractionService()
few_shot_service = FewShotService()


# =========================================================================
# Request Models
# =========================================================================

class StartExtractionRequest(BaseModel):
    provider_name: str
    min_delay: float = 5.0


class DryRunRequest(BaseModel):
    provider_name: str
    page_number: int


class SavePromptsRequest(BaseModel):
    system_prompt: str
    extraction_prompt: str


class AddFewShotRequest(BaseModel):
    page_number: int
    annotation_data: Optional[Dict[str, Any]] = None
    cache_name: Optional[str] = None


class UpdateAnnotationsRequest(BaseModel):
    annotation_data: Dict[str, Any]


class MarkSentRequest(BaseModel):
    provider: str
    model: str


# =========================================================================
# Extraction Control
# =========================================================================

@router.get("/v2/books/{book_id}/extraction/prerequisites")
async def check_prerequisites(book_id: int):
    """Check if all prerequisites are met for starting extraction."""
    result = extraction_service.check_prerequisites(book_id)
    return result


@router.get("/v2/books/{book_id}/extraction/status")
async def get_extraction_status(book_id: int):
    """Get current extraction status and live metrics."""
    state = extraction_service.get_state(book_id)
    stats = extraction_service.get_extraction_stats(book_id)
    return {
        "state": state,
        "stats": stats
    }


@router.post("/v2/books/{book_id}/extraction/start")
async def start_extraction(book_id: int, request: StartExtractionRequest):
    """Start V2 extraction for a book."""
    result = await extraction_service.start_extraction(
        book_id, request.provider_name, request.min_delay
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/v2/books/{book_id}/extraction/pause")
async def pause_extraction(book_id: int):
    """Pause running extraction."""
    success = extraction_service.pause(book_id)
    if not success:
        raise HTTPException(status_code=400, detail="Extraction not running")
    return {"message": "Extraction paused"}


@router.post("/v2/books/{book_id}/extraction/resume")
async def resume_extraction(book_id: int):
    """Resume paused extraction."""
    success = extraction_service.resume(book_id)
    if not success:
        raise HTTPException(status_code=400, detail="Extraction not paused")
    return {"message": "Extraction resumed"}


@router.post("/v2/books/{book_id}/extraction/cancel")
async def cancel_extraction(book_id: int):
    """Cancel running or paused extraction."""
    success = extraction_service.cancel(book_id)
    if not success:
        raise HTTPException(status_code=400, detail="No active extraction to cancel")
    return {"message": "Extraction cancelled"}


# =========================================================================
# Dry Run
# =========================================================================

@router.post("/v2/books/{book_id}/extraction/dry-run")
async def dry_run(book_id: int, request: DryRunRequest):
    """Run extraction on a single page without saving (for testing)."""
    result = await extraction_service.dry_run(
        book_id, request.provider_name, request.page_number
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# =========================================================================
# Prompt Management
# =========================================================================

@router.get("/v2/books/{book_id}/extraction/prompts")
async def get_prompts(book_id: int):
    """Get system and extraction prompts for a book."""
    return extraction_service.get_prompts(book_id)


@router.put("/v2/books/{book_id}/extraction/prompts")
async def save_prompts(book_id: int, request: SavePromptsRequest):
    """Save custom prompts for a book."""
    success = extraction_service.save_prompts(
        book_id, request.system_prompt, request.extraction_prompt
    )
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Prompts saved"}


@router.post("/v2/books/{book_id}/extraction/prompts/reset")
async def reset_prompts(book_id: int):
    """Reset prompts to defaults."""
    service = V2ExtractionService()
    success = service.save_prompts(
        book_id,
        service._default_system_prompt(),
        service._default_extraction_prompt()
    )
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Prompts reset to defaults"}


# =========================================================================
# Few-Shot Examples
# =========================================================================

@router.get("/v2/books/{book_id}/few-shots")
async def get_few_shots(book_id: int):
    """Get all few-shot examples for a book."""
    examples = few_shot_service.get_examples(book_id)
    return {"examples": examples}


@router.post("/v2/books/{book_id}/few-shots")
async def add_few_shot(book_id: int, request: AddFewShotRequest):
    """Add a new few-shot example page."""
    try:
        result = few_shot_service.add_example(
            book_id, request.page_number,
            request.annotation_data, request.cache_name
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/v2/books/{book_id}/few-shots/{example_id}")
async def remove_few_shot(book_id: int, example_id: int):
    """Remove a few-shot example."""
    success = few_shot_service.remove_example(book_id, example_id)
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"message": "Example removed"}


@router.put("/v2/books/{book_id}/few-shots/{example_id}/annotations")
async def update_few_shot_annotations(book_id: int, example_id: int,
                                       request: UpdateAnnotationsRequest):
    """Update annotations for a few-shot example."""
    success = few_shot_service.update_annotations(
        book_id, example_id, request.annotation_data
    )
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"message": "Annotations updated"}


@router.post("/v2/books/{book_id}/few-shots/{example_id}/mark-sent")
async def mark_few_shot_sent(book_id: int, example_id: int,
                              request: MarkSentRequest):
    """Mark a few-shot example as sent to LLM."""
    success = few_shot_service.mark_as_sent(
        book_id, example_id, request.provider, request.model
    )
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"message": "Marked as sent"}


# =========================================================================
# Knowledge Pages (V2)
# =========================================================================

@router.get("/v2/books/{book_id}/knowledge-pages")
async def get_knowledge_pages(book_id: int, page: int = 1, per_page: int = 20):
    """Get V2 knowledge pages with pagination."""
    from src.database.connection import engine
    from sqlalchemy import text

    table_prefix = extraction_service._get_table_prefix(book_id)
    if not table_prefix:
        raise HTTPException(status_code=404, detail="Book not found")

    kp_table = f"v2_{table_prefix}_knowledge_pages"
    offset = (page - 1) * per_page

    with engine.connect() as conn:
        # Total count
        r = conn.execute(text(f"SELECT COUNT(*) FROM {kp_table}"))
        total = r.scalar()

        # Paginated results
        r = conn.execute(text(f"""
            SELECT id, l1_title_id, l2_title_id, l3_title_text,
                   start_page, end_page, summary,
                   difficulty_score, concept_type, bloom_taxonomy_level,
                   physics_domain, exam_relevance, extraction_confidence,
                   has_worked_example, has_problem_set, element_count,
                   verified, notes, record_status,
                   raw_xml, parsed_json,
                   llm_provider, model_name, window_pages,
                   created_at
            FROM {kp_table}
            ORDER BY start_page, id
            LIMIT :limit OFFSET :offset
        """), {"limit": per_page, "offset": offset})
        rows = r.fetchall()

    pages = []
    for row in rows:
        pages.append({
            "id": row[0], "l1_title_id": row[1], "l2_title_id": row[2],
            "l3_title_text": row[3], "start_page": row[4], "end_page": row[5],
            "summary": row[6], "difficulty_score": row[7],
            "concept_type": row[8], "bloom_taxonomy_level": row[9],
            "physics_domain": row[10], "exam_relevance": row[11],
            "extraction_confidence": row[12],
            "has_worked_example": row[13], "has_problem_set": row[14],
            "element_count": row[15], "verified": row[16],
            "notes": row[17], "record_status": row[18],
            "raw_xml": row[19], "parsed_json": row[20],
            "llm_provider": row[21], "model_name": row[22],
            "window_pages": row[23],
            "created_at": str(row[24]) if row[24] else None
        })

    return {
        "knowledge_pages": pages,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
    }

class UpdateKnowledgePageRequest(BaseModel):
    verified: Optional[bool] = None
    notes: Optional[str] = None
    record_status: Optional[str] = None


@router.put("/v2/books/{book_id}/knowledge-pages/{kp_id}")
async def update_knowledge_page(book_id: int, kp_id: int, request: UpdateKnowledgePageRequest):
    """Update a V2 knowledge page (verify, notes, status)."""
    from src.database.connection import engine
    from sqlalchemy import text

    table_prefix = extraction_service._get_table_prefix(book_id)
    if not table_prefix:
        raise HTTPException(status_code=404, detail="Book not found")

    kp_table = f"v2_{table_prefix}_knowledge_pages"

    # Build dynamic SET clause
    updates = []
    params = {"kp_id": kp_id}
    if request.verified is not None:
        updates.append("verified = :verified")
        params["verified"] = request.verified
    if request.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = request.notes
    if request.record_status is not None:
        updates.append("record_status = :record_status")
        params["record_status"] = request.record_status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(updates)
    with engine.connect() as conn:
        result = conn.execute(
            text(f"UPDATE {kp_table} SET {set_clause} WHERE id = :kp_id"),
            params
        )
        conn.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Knowledge page not found")

    return {"message": "Knowledge page updated", "id": kp_id}

