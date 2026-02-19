"""
CHUNK-034: API Routes - Books Management

List, get, and delete books endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.services.duplicate_check_service import DuplicateCheckService
from src.services.storage_migration_service import StorageMigrationService
from src.utils.logging_config import logger

router = APIRouter()


class BookSummary(BaseModel):
    """Book summary model for list responses."""
    book_id: int
    book_name: str
    file_type: str
    total_pages: int
    processing_status: str
    upload_date: Optional[str] = None


class BookSummaryEnhanced(BaseModel):
    """Enhanced book summary with file readability and size."""
    book_id: int
    book_name: str
    file_type: str
    file_size_bytes: int
    total_pages: int
    processing_status: str
    upload_date: Optional[str] = None
    file_readable: bool
    file_path: Optional[str] = None


class StorageLocationResponse(BaseModel):
    """Storage location information."""
    storage_path: str
    is_temporary: bool
    warning: Optional[str] = None


class SetStorageLocationRequest(BaseModel):
    """Request to set new storage location."""
    path: str
    migrate_files: bool = True


class StorageLocationHistoryItem(BaseModel):
    """Storage location history item."""
    location_id: int
    path: str
    is_active: bool
    created_at: str
    notes: Optional[str] = None


class MigrationResultResponse(BaseModel):
    """Migration result response."""
    success: bool
    files_migrated: int
    files_failed: int
    old_location: str
    new_location: str
    message: str
    errors: List[str]


@router.get("/books")
async def list_books(
    status: Optional[str] = Query(None, description="Filter by processing status"),
    limit: int = Query(20, ge=1, le=100, description="Number of books to return"),
    offset: int = Query(0, ge=0, description="Number of books to skip")
):
    """
    List books with optional filters.

    Args:
        status: Filter by processing status (pending/processing/completed/paused/error)
        limit: Maximum number of books to return (1-100, default 20)
        offset: Number of books to skip (for pagination)

    Returns:
        dict: List of books and total count

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/books?status=completed&limit=10')
    """
    db = SessionLocal()

    try:
        # Build query
        query = db.query(BooksMetadata)

        # Apply filters
        if status:
            query = query.filter(BooksMetadata.processing_status == status)

        # Get total count
        total = query.count()

        # Apply pagination and get results
        books = query.order_by(BooksMetadata.upload_date.desc()) \
                    .offset(offset) \
                    .limit(limit) \
                    .all()

        # Convert to response format with file readability check and progress info
        duplicate_service = DuplicateCheckService()
        books_list = []

        for book in books:
            file_readable = False
            if book.file_path:
                file_readable = duplicate_service.is_file_readable(book.file_path)

            # Get progress information from processing_state table
            progress_info = {
                "pages_scanned": 0,
                "easyocr_pages_processed": 0,
                "surya_pages_processed": 0,
                "tesseract_pages_processed": 0,
                "pages_split_verified": 0
            }

            if book.table_prefix:
                try:
                    progress_query = text(f"""
                        SELECT pages_scanned, easyocr_pages_processed,
                               surya_pages_processed, tesseract_pages_processed,
                               pages_split_verified
                        FROM {book.table_prefix}_processing_state
                        WHERE id = 1
                    """)
                    progress_result = db.execute(progress_query).first()

                    if progress_result:
                        progress_info = {
                            "pages_scanned": progress_result[0] or 0,
                            "easyocr_pages_processed": progress_result[1] or 0,
                            "surya_pages_processed": progress_result[2] or 0,
                            "tesseract_pages_processed": progress_result[3] or 0,
                            "pages_split_verified": progress_result[4] or 0
                        }
                except Exception as e:
                    # Rollback the transaction and continue
                    db.rollback()
                    logger.warning(f"Failed to get progress for book {book.book_id}: {e}")

            books_list.append({
                "book_id": book.book_id,
                "book_name": book.book_name,
                "file_type": book.file_type,
                "file_size_bytes": book.file_size_bytes,
                "total_pages": book.total_pages,
                "processing_status": book.processing_status,
                "upload_date": book.upload_date.isoformat() if book.upload_date else None,
                "file_readable": file_readable,
                "file_path": book.file_path,
                "extraction_method": getattr(book, 'extraction_method', 'v2'),
                "progress": progress_info
            })

        return {
            "books": books_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        db.close()


@router.get("/books/{book_id}")
async def get_book(book_id: int):
    """
    Get detailed information about a specific book.

    Args:
        book_id: Book ID

    Returns:
        dict: Book details

    Raises:
        HTTPException: If book not found

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/books/1')
    """
    db = SessionLocal()

    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Return book details
        return {
            "book_id": book.book_id,
            "book_name": book.book_name,
            "sanitized_name": book.sanitized_name,
            "table_prefix": book.table_prefix,
            "file_type": book.file_type,
            "file_size_bytes": book.file_size_bytes,
            "total_pages": book.total_pages,
            "processing_status": book.processing_status,
            "upload_date": book.upload_date.isoformat() if book.upload_date else None,
            "file_path": book.file_path,
            "extraction_method": getattr(book, 'extraction_method', 'v2')
        }

    finally:
        db.close()


# NOTE: DELETE /books/{book_id} endpoint has been moved to delete_book.py
# The new implementation includes two-step confirmation with code validation
# and properly drops all book-specific tables + ChromaDB embeddings


@router.get("/books/{book_id}/stats")
async def get_book_stats(book_id: int):
    """
    Get statistics for a book.

    Args:
        book_id: Book ID

    Returns:
        dict: Book statistics

    Raises:
        HTTPException: If book not found

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/books/1/stats')
    """
    db = SessionLocal()

    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get processing state for statistics
        from src.database.services.processing_state_service import ProcessingStateService
        state_service = ProcessingStateService()
        state = state_service.get_state(book_id)

        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "total_pages": book.total_pages,
            "processing_status": book.processing_status,
            "pages_processed": state.get('pages_processed', 0),
            "knowledge_units_extracted": state.get('knowledge_units_extracted', 0),
            "images_extracted": state.get('images_extracted', 0),
            "progress_percentage": state.get('progress_percentage', 0.0)
        }

    finally:
        db.close()


@router.get("/storage-location")
async def get_storage_location():
    """
    Get the storage location for uploaded files.

    Returns:
        dict: Storage location with warning if temporary

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/storage-location')
    """
    duplicate_service = DuplicateCheckService()
    storage_path = duplicate_service.get_storage_location()

    # Check if using temporary storage
    is_temporary = storage_path.startswith('/tmp')
    warning = None

    if is_temporary:
        warning = "Warning: Files are stored in /tmp which is cleared on reboot. Configure UPLOAD_STORAGE_PATH environment variable for permanent storage."

    return {
        "storage_path": storage_path,
        "is_temporary": is_temporary,
        "warning": warning
    }


@router.post("/storage-location")
async def set_storage_location(request: SetStorageLocationRequest):
    """
    Set new storage location and migrate files.

    Args:
        request: SetStorageLocationRequest with path and migrate_files flag

    Returns:
        MigrationResultResponse with migration details

    Example:
        >>> # Via HTTP POST
        >>> response = await fetch('/api/storage-location', {
        >>>     method: 'POST',
        >>>     headers: {'Content-Type': 'application/json'},
        >>>     body: JSON.stringify({path: '/var/lib/uploads', migrate_files: true})
        >>> })
    """
    try:
        migration_service = StorageMigrationService()
        result = migration_service.set_storage_location(
            new_path=request.path,
            migrate_files=request.migrate_files
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        return {
            "success": result.success,
            "files_migrated": result.files_migrated,
            "files_failed": result.files_failed,
            "old_location": result.old_location,
            "new_location": result.new_location,
            "message": result.message,
            "errors": result.errors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting storage location: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set storage location: {str(e)}")


@router.get("/storage-locations/history")
async def get_storage_location_history():
    """
    Get storage location history.

    Returns:
        list: List of storage locations ordered by created_at DESC

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/storage-locations/history')
    """
    try:
        migration_service = StorageMigrationService()
        locations = migration_service.get_location_history()

        return {
            "locations": [
                {
                    "location_id": loc.location_id,
                    "path": loc.path,
                    "is_active": loc.is_active,
                    "created_at": loc.created_at.isoformat() if loc.created_at else None,
                    "notes": loc.notes
                }
                for loc in locations
            ]
        }

    except Exception as e:
        logger.error(f"Error getting storage location history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get storage location history: {str(e)}")


# ============================================================================
# Attribute Keys Endpoints (2026-01-07)
# ============================================================================

class AttributeKeyResponse(BaseModel):
    """Attribute key model."""
    attr_number: int
    key_name: Optional[str]
    is_system_reserved: bool
    is_editable: bool


class AttributeKeyUpdate(BaseModel):
    """Update model for attribute key."""
    attr_number: int
    key_name: Optional[str]


class UpdateAttributeKeysRequest(BaseModel):
    """Request model for updating attribute keys."""
    updates: List[AttributeKeyUpdate]


@router.get("/books/{book_id}/attribute-keys")
async def get_attribute_keys(book_id: int):
    """
    Get all attribute key configurations for a book.

    Returns all 80 attributes (8 system-reserved + 72 user-defined).
    System-reserved attributes (1-8) cannot be edited.
    User-defined attributes (9-80) can have custom names.

    Args:
        book_id: Book ID

    Returns:
        Dictionary with book_id and list of attributes
    """
    db = SessionLocal()
    try:
        # Get book to validate it exists and get table_prefix
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix
        extraction_method = getattr(book, 'extraction_method', 'v1') or 'v1'

        # V2 books use v2_ prefixed attribute_keys table
        if extraction_method == 'v2':
            attr_table = f"v2_{table_prefix}_attribute_keys"
        else:
            attr_table = f"{table_prefix}_attribute_keys"

        # Query attribute_keys table
        sql = text(f"""
            SELECT attr_number, key_name, is_system_reserved, is_editable
            FROM {attr_table}
            ORDER BY attr_number
        """)

        result = db.execute(sql)

        attributes = [
            {
                "attr_number": row.attr_number,
                "key_name": row.key_name,
                "is_system_reserved": row.is_system_reserved,
                "is_editable": row.is_editable
            }
            for row in result
        ]

        return {
            "book_id": book_id,
            "attributes": attributes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attribute keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/books/{book_id}/attribute-keys")
async def update_attribute_keys(
    book_id: int,
    request: UpdateAttributeKeysRequest
):
    """
    Update attribute key names for user-defined attributes (9-80).

    System-reserved attributes (1-8) cannot be modified.

    Args:
        book_id: Book ID
        request: Update request with list of attribute updates

    Returns:
        Success message with count of updated keys
    """
    db = SessionLocal()
    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix
        extraction_method = getattr(book, 'extraction_method', 'v1') or 'v1'

        # V2 books use v2_ prefixed attribute_keys table
        if extraction_method == 'v2':
            attr_table = f"v2_{table_prefix}_attribute_keys"
        else:
            attr_table = f"{table_prefix}_attribute_keys"

        # Validate all updates before applying any
        for update in request.updates:
            # Check attribute number is in valid range
            if not (1 <= update.attr_number <= 80):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid attr_number {update.attr_number}. Must be 1-80."
                )

            # Check not trying to modify system-reserved attributes
            if update.attr_number <= 8:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot modify system-reserved attribute {update.attr_number}"
                )

        # Apply updates
        updated_count = 0
        for update in request.updates:
            sql = text(f"""
                UPDATE {attr_table}
                SET key_name = :key_name,
                    updated_at = NOW()
                WHERE attr_number = :attr_number
            """)

            result = db.execute(sql, {
                "attr_number": update.attr_number,
                "key_name": update.key_name
            })

            if result.rowcount > 0:
                updated_count += 1

        db.commit()

        logger.info(f"Updated {updated_count} attribute keys for book {book_id}")

        return {
            "success": True,
            "message": f"Updated {updated_count} attribute keys",
            "book_id": book_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update attribute keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============================================================================
# Book Settings Endpoints (2026-01-07)
# ============================================================================

@router.get("/books/{book_id}/settings")
async def get_book_settings(book_id: int):
    """
    Get all settings for a book.

    Args:
        book_id: Book ID

    Returns:
        Dictionary with all book settings including new fields
    """
    from src.database.services.book_settings_service import BookSettingsService

    service = BookSettingsService()
    try:
        settings = service.get_settings(book_id)
        return settings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/books/{book_id}/settings")
async def update_book_settings(book_id: int, updates: dict = Body(...)):
    """
    Update book settings.

    Args:
        book_id: Book ID
        updates: Dictionary of settings to update

    Returns:
        Success message
    """
    from src.database.services.book_settings_service import BookSettingsService

    service = BookSettingsService()
    try:
        success = service.update_settings(book_id, updates)
        if success:
            return {"success": True, "message": "Settings updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update settings")
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
