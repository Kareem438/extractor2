"""
Delete Book API Routes

Provides endpoints for safely deleting books with two-step confirmation.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
import random
from src.database.connection import engine, SessionLocal
from src.utils.logging_config import logger

router = APIRouter()

# Store confirmation codes temporarily (in-memory, cleared on server restart)
confirmation_codes = {}


class DeleteBookRequest(BaseModel):
    """Request body for book deletion."""
    delete_chromadb: bool = True
    confirmation_code: str


@router.get("/books/{book_id}/deletion-preview")
async def get_deletion_preview(book_id: int):
    """
    Get deletion preview with counts and confirmation code.
    
    Returns information needed for the deletion confirmation dialog:
    - Book details (name, file path)
    - Counts of entities to be deleted
    - Whether deletion is allowed
    - A 4-digit confirmation code
    """
    db = SessionLocal()
    try:
        # Get book info
        book = db.execute(
            text("""
                SELECT book_id, book_name, file_path, table_prefix, processing_status 
                FROM books_metadata 
                WHERE book_id = :id
            """),
            {"id": book_id}
        ).fetchone()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Check if can delete
        can_delete = True
        blocking_reason = None
        active_tasks_count = 0
        
        # Check processing status
        if book.processing_status == 'processing':
            can_delete = False
            blocking_reason = "Book is currently being processed"
        
        # Check for active tasks in task_queue
        if can_delete:
            task_table = f"{book.table_prefix}_task_queue"
            try:
                active_tasks_count = db.execute(
                    text(f"SELECT COUNT(*) FROM {task_table} WHERE status IN ('pending', 'running')")
                ).scalar() or 0
                if active_tasks_count > 0:
                    can_delete = False
                    blocking_reason = f"Book has {active_tasks_count} active pipeline tasks"
            except Exception:
                pass  # Table might not exist, which is fine
        
        # Get counts of entities
        counts = get_book_counts(db, book.table_prefix, book_id)
        
        # Generate 4-digit confirmation code
        code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        confirmation_codes[book_id] = code
        
        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "file_path": book.file_path,
            "table_prefix": book.table_prefix,
            "can_delete": can_delete,
            "blocking_reason": blocking_reason,
            "active_tasks": active_tasks_count,
            "counts": counts,
            "confirmation_code": code
        }
    finally:
        db.close()


@router.delete("/books/{book_id}")
async def delete_book(book_id: int, request: DeleteBookRequest):
    """
    Delete a book and all associated data.
    
    Requires:
    - Valid confirmation code from deletion-preview
    - Book must not have active tasks
    
    Deletes:
    - All book-specific PostgreSQL tables (17+)
    - Row from books_metadata
    - Related rows from pdf_uploads and cross_book_access_log
    - ChromaDB embeddings (if delete_chromadb is True)
    
    Preserves:
    - Original PDF file on disk
    """
    # Verify confirmation code
    if book_id not in confirmation_codes:
        raise HTTPException(status_code=400, detail="No confirmation code found. Please request deletion preview first.")
    
    if confirmation_codes[book_id] != request.confirmation_code:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    
    db = SessionLocal()
    try:
        # Get book info
        book = db.execute(
            text("SELECT book_name, table_prefix, processing_status FROM books_metadata WHERE book_id = :id"),
            {"id": book_id}
        ).fetchone()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Double-check deletion is allowed
        if book.processing_status == 'processing':
            raise HTTPException(status_code=400, detail="Cannot delete book while processing")
        
        # Check for active tasks
        task_table = f"{book.table_prefix}_task_queue"
        try:
            active_tasks = db.execute(
                text(f"SELECT COUNT(*) FROM {task_table} WHERE status IN ('pending', 'running')")
            ).scalar() or 0
            if active_tasks > 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot delete book with {active_tasks} active tasks"
                )
        except HTTPException:
            raise
        except Exception:
            pass  # Table might not exist
        
        # Drop all book-specific tables
        tables_dropped = drop_book_tables(db, book.table_prefix)
        
        # Delete from global tables
        try:
            db.execute(text("DELETE FROM pdf_uploads WHERE book_id = :id"), {"id": book_id})
        except Exception:
            pass  # Table might not exist
        
        try:
            db.execute(
                text("DELETE FROM cross_book_access_log WHERE source_book_id = :id OR target_book_id = :id"), 
                {"id": book_id}
            )
        except Exception:
            pass  # Table might not exist
        
        # Delete from books_metadata
        db.execute(text("DELETE FROM books_metadata WHERE book_id = :id"), {"id": book_id})
        
        db.commit()
        
        # Delete ChromaDB embeddings
        embeddings_removed = 0
        if request.delete_chromadb:
            try:
                from src.services.chroma_service import get_chroma_service
                chroma = get_chroma_service()
                embeddings_removed = chroma.count_by_book_id(book_id)
                chroma.delete_by_book_id(book_id)
            except Exception as e:
                logger.warning(f"Failed to delete ChromaDB embeddings: {e}")
        
        # Clean up confirmation code
        del confirmation_codes[book_id]
        
        logger.info(f"Book '{book.book_name}' (ID: {book_id}) deleted successfully")
        
        return {
            "success": True,
            "message": f"Book '{book.book_name}' deleted successfully",
            "deleted": {
                "book_name": book.book_name,
                "tables_dropped": tables_dropped,
                "chromadb_deleted": request.delete_chromadb,
                "embeddings_removed": embeddings_removed
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


def get_book_counts(db, table_prefix: str, book_id: int) -> dict:
    """
    Get counts of various entities for a book.
    
    Args:
        db: Database session
        table_prefix: Book's table prefix
        book_id: Book ID
        
    Returns:
        Dictionary with entity counts
    """
    counts = {
        "pages": 0,
        "knowledge_units": 0,
        "images": 0,
        "paragraph_clips": 0,
        "diagram_clips": 0,
        "chromadb_embeddings": 0
    }
    
    # Count raw pages
    try:
        counts["pages"] = db.execute(
            text(f"SELECT COUNT(*) FROM raw_{table_prefix}_pages")
        ).scalar() or 0
    except Exception:
        pass
    
    # Count knowledge units
    try:
        counts["knowledge_units"] = db.execute(
            text(f"SELECT COUNT(*) FROM {table_prefix}_knowledge_units")
        ).scalar() or 0
    except Exception:
        pass
    
    # Count images
    try:
        counts["images"] = db.execute(
            text(f"SELECT COUNT(*) FROM {table_prefix}_images")
        ).scalar() or 0
    except Exception:
        pass
    
    # Count paragraph clips
    try:
        counts["paragraph_clips"] = db.execute(
            text(f"SELECT COUNT(*) FROM raw_{table_prefix}_paragraph_images")
        ).scalar() or 0
    except Exception:
        pass
    
    # Count diagram clips
    try:
        counts["diagram_clips"] = db.execute(
            text(f"SELECT COUNT(*) FROM raw_{table_prefix}_diagram_images")
        ).scalar() or 0
    except Exception:
        pass
    
    # Count ChromaDB embeddings
    try:
        from src.services.chroma_service import get_chroma_service
        chroma = get_chroma_service()
        counts["chromadb_embeddings"] = chroma.count_by_book_id(book_id)
    except Exception:
        pass
    
    return counts


def drop_book_tables(db, table_prefix: str) -> int:
    """
    Drop all tables for a book.
    
    Args:
        db: Database session
        table_prefix: Book's table prefix
        
    Returns:
        Number of tables dropped
    """
    # List of all possible book-specific tables
    tables = [
        # Raw data tables
        f"raw_{table_prefix}_pages",
        f"raw_{table_prefix}_knowledge_units",
        f"raw_{table_prefix}_paragraph_images",
        f"raw_{table_prefix}_diagram_images",
        # Processed data tables
        f"{table_prefix}_knowledge_units",
        f"{table_prefix}_pages",
        f"{table_prefix}_images",
        f"{table_prefix}_processing_state",
        f"{table_prefix}_settings",
        f"{table_prefix}_hierarchy",
        f"{table_prefix}_attribute_keys",
        # Worker system tables
        f"{table_prefix}_pipeline_config",
        f"{table_prefix}_task_queue",
        f"{table_prefix}_step_progress",
        # Title hierarchy tables
        f"{table_prefix}_level1_titles",
        f"{table_prefix}_level2_titles",
    ]
    
    dropped = 0
    for table in tables:
        try:
            db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            dropped += 1
            logger.debug(f"Dropped table: {table}")
        except Exception as e:
            logger.warning(f"Failed to drop table {table}: {e}")
    
    return dropped
