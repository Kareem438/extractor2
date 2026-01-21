"""
Search API Routes

Provides endpoints for semantic search using ChromaDB.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from src.services.chroma_service import get_chroma_service
from src.utils.logging_config import logger

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    n_results: int = 10
    book_id: Optional[int] = None


class SearchResult(BaseModel):
    """Search result model."""
    doc_id: str
    text: str
    metadata: dict
    distance: Optional[float] = None


class SyncRequest(BaseModel):
    """Sync request model."""
    book_id: int


@router.post("/semantic", response_model=List[SearchResult])
async def search_semantic(request: SearchRequest):
    """
    Perform semantic search across knowledge units.

    Args:
        request: Search request with query text and options

    Returns:
        List of matching knowledge units
    """
    try:
        chroma = get_chroma_service()
        results = chroma.search_similar(
            query_text=request.query,
            n_results=request.n_results,
            book_id=request.book_id
        )

        return [
            SearchResult(
                doc_id=r['doc_id'],
                text=r['text'],
                metadata=r['metadata'],
                distance=r.get('distance')
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_book_to_chroma(request: SyncRequest):
    """
    Synchronize a book's knowledge units to ChromaDB.

    Args:
        request: Sync request with book ID

    Returns:
        Sync statistics
    """
    try:
        from sqlalchemy import text
        from src.database.connection import SessionLocal

        # Get book metadata
        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail=f"Book {request.book_id} not found")

            table_prefix = result[0]
        finally:
            db.close()

        # Sync to ChromaDB
        chroma = get_chroma_service()
        stats = await chroma.sync_book_to_chroma(request.book_id, table_prefix)

        return {
            "status": "success",
            "book_id": request.book_id,
            "statistics": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ChromaDB sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_chroma_stats():
    """
    Get ChromaDB collection statistics.

    Returns:
        Collection statistics
    """
    try:
        chroma = get_chroma_service()
        stats = chroma.get_collection_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get ChromaDB stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/book/{book_id}")
async def delete_book_from_chroma(book_id: int):
    """
    Delete all vectors for a specific book from ChromaDB.

    Args:
        book_id: Book ID to delete

    Returns:
        Deletion status
    """
    try:
        chroma = get_chroma_service()
        success = chroma.delete_book_units(book_id)

        if success:
            return {
                "status": "success",
                "book_id": book_id,
                "message": f"Deleted all units for book {book_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete book units")

    except Exception as e:
        logger.error(f"Failed to delete book from ChromaDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))
