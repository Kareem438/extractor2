"""
CHUNK-035: API Routes - Knowledge Units

Query, update, and export knowledge units.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from src.database.services.knowledge_unit_service import KnowledgeUnitService
from src.utils.logging_config import logger

router = APIRouter()


@router.get("/books/{book_id}/knowledge-units")
async def list_knowledge_units(
    book_id: int,
    page_number: Optional[int] = None,
    verified: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List knowledge units for a book with pagination and filters."""
    service = KnowledgeUnitService()

    # Convert offset to page number (service uses page-based pagination)
    page = (offset // limit) + 1

    # Get knowledge units with filters
    result = service.get_knowledge_units(
        book_id=book_id,
        page=page,
        limit=limit,
        verified=verified,
        page_number=page_number
    )

    return {
        "book_id": book_id,
        "units": result.get('records', []),  # Frontend expects 'units'
        "total": result.get('total', 0),
        "limit": limit,
        "offset": offset,
        "has_more": result.get('has_more', False)
    }


@router.get("/books/{book_id}/knowledge-units/{unit_id}")
async def get_knowledge_unit(book_id: int, unit_id: int):
    """Get a specific knowledge unit by ID."""
    service = KnowledgeUnitService()

    # Get single record using the service's pagination method
    result = service.get_knowledge_units(book_id=book_id, page=1, limit=1000)

    # Find the specific unit
    unit = next((u for u in result.get('records', []) if u.get('id') == unit_id), None)

    if not unit:
        raise HTTPException(status_code=404, detail="Knowledge unit not found")

    return unit


@router.put("/books/{book_id}/knowledge-units/{unit_id}")
async def update_knowledge_unit(book_id: int, unit_id: int, updates: dict):
    """Update a knowledge unit (full update)."""
    service = KnowledgeUnitService()
    success = service.update_knowledge_unit(book_id, unit_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Knowledge unit not found")

    return {"message": "Knowledge unit updated successfully"}


@router.patch("/books/{book_id}/knowledge-units/{unit_id}")
async def patch_knowledge_unit(book_id: int, unit_id: int, updates: dict):
    """Update a knowledge unit (partial update)."""
    service = KnowledgeUnitService()
    success = service.update_knowledge_unit(book_id, unit_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Knowledge unit not found")

    return {"message": "Knowledge unit updated successfully"}


@router.post("/books/{book_id}/knowledge-units/merge")
async def merge_knowledge_units(book_id: int, merge_request: dict):
    """
    Merge two knowledge units.

    Combines source_id into target_id, concatenating their text content.
    The source record is marked as disabled and tracking is updated.

    Args:
        book_id: Book ID
        merge_request: {
            "source_id": int,  # ID of record to merge (will be disabled)
            "target_id": int   # ID of record to keep (will be updated)
        }

    Returns:
        dict: Success message with merged record ID

    Example:
        >>> POST /api/books/1/knowledge-units/merge
        >>> {"source_id": 101, "target_id": 100}
    """
    source_id = merge_request.get('source_id')
    target_id = merge_request.get('target_id')

    if not source_id or not target_id:
        raise HTTPException(
            status_code=400,
            detail="Both source_id and target_id are required"
        )

    service = KnowledgeUnitService()
    success = service.merge_knowledge_units(
        book_id=book_id,
        keep_id=target_id,
        delete_id=source_id
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="One or both knowledge units not found"
        )

    return {
        "message": "Knowledge units merged successfully",
        "merged_id": target_id,
        "disabled_id": source_id
    }


@router.get("/books/{book_id}/export")
async def export_knowledge_units(book_id: int, format: str = "json"):
    """Export knowledge units in various formats."""
    service = KnowledgeUnitService()

    if format not in ["json", "csv", "txt"]:
        raise HTTPException(status_code=400, detail="Invalid export format")

    # TODO: Implement export logic
    units = service.get_knowledge_units(book_id)

    return {
        "book_id": book_id,
        "format": format,
        "data": units
    }
