"""
CHUNK-033: API Routes - Processing Control

Start/pause/resume processing endpoints.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.database.services.processing_state_service import ProcessingStateService
from src.api.background_processor import process_book_background
from src.utils.logging_config import logger

router = APIRouter()


class StartProcessingRequest(BaseModel):
    """Request model for starting processing."""
    book_id: int


class ProcessingResponse(BaseModel):
    """Response model for processing operations."""
    book_id: int
    processing_status: str
    message: str


@router.post("/start-processing")
async def start_processing(
    request: StartProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start processing a book in background.

    Args:
        request: Request containing book_id
        background_tasks: FastAPI background tasks

    Returns:
        dict: Processing status and message

    Raises:
        HTTPException: If book not found or already processing

    Example:
        >>> # Via HTTP POST
        >>> response = await fetch('/api/start-processing', {
        ...     method: 'POST',
        ...     body: JSON.stringify({book_id: 1})
        ... })
    """
    book_id = request.book_id
    db = SessionLocal()

    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Check if already processing
        if book.processing_status == 'processing':
            raise HTTPException(status_code=409, detail="Book is already being processed")

        # Get file path from metadata
        pdf_path = book.file_path
        if not pdf_path:
            raise HTTPException(status_code=400, detail="No file path found for book")

        # Update status to processing
        book.processing_status = 'processing'
        db.commit()

        logger.info(f"Starting background processing for book {book_id}")

        # Start background task
        background_tasks.add_task(process_book_background, book_id, pdf_path)

        return {
            "book_id": book_id,
            "processing_status": "processing",
            "message": "Processing started in background"
        }

    finally:
        db.close()


@router.post("/pause/{book_id}")
async def pause_processing(book_id: int):
    """
    Pause processing for a book.

    The background processor checks the processing state before each page
    and will pause when it sees the 'paused' status.

    Args:
        book_id: Book ID to pause

    Returns:
        dict: Success message

    Raises:
        HTTPException: If book not found

    Example:
        >>> # Via HTTP POST
        >>> response = await fetch('/api/pause/1', {method: 'POST'})
    """
    db = SessionLocal()

    try:
        # Verify book exists
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Update processing state to paused
        state_service = ProcessingStateService()
        state_service.update_state(book_id, {'status': 'paused'})

        logger.info(f"Pause requested for book {book_id}")

        return {
            "book_id": book_id,
            "message": "Processing will pause after current page"
        }

    finally:
        db.close()


@router.post("/resume/{book_id}")
async def resume_processing(book_id: int, background_tasks: BackgroundTasks):
    """
    Resume paused processing for a book.

    Args:
        book_id: Book ID to resume
        background_tasks: FastAPI background tasks

    Returns:
        dict: Processing status and message

    Raises:
        HTTPException: If book not found or not paused

    Example:
        >>> # Via HTTP POST
        >>> response = await fetch('/api/resume/1', {method: 'POST'})
    """
    db = SessionLocal()

    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Check if paused
        if book.processing_status not in ['paused', 'error']:
            raise HTTPException(
                status_code=409,
                detail=f"Book is not paused (current status: {book.processing_status})"
            )

        # Get file path
        pdf_path = book.file_path
        if not pdf_path:
            raise HTTPException(status_code=400, detail="No file path found for book")

        # Update status to processing
        book.processing_status = 'processing'
        db.commit()

        # Update processing state to resume
        state_service = ProcessingStateService()
        state_service.update_state(book_id, {'status': 'processing'})

        logger.info(f"Resuming processing for book {book_id}")

        # Start background task (will resume from checkpoint)
        background_tasks.add_task(process_book_background, book_id, pdf_path)

        return {
            "book_id": book_id,
            "processing_status": "processing",
            "message": "Processing resumed in background"
        }

    finally:
        db.close()


@router.get("/processing-status/{book_id}")
async def get_processing_status(book_id: int):
    """
    Get current processing status for a book.

    Args:
        book_id: Book ID

    Returns:
        dict: Processing state details

    Raises:
        HTTPException: If book not found

    Example:
        >>> # Via HTTP GET
        >>> response = await fetch('/api/processing-status/1')
    """
    db = SessionLocal()

    try:
        # Get book
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get processing state
        state_service = ProcessingStateService()
        state = state_service.get_state(book_id)

        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "processing_status": book.processing_status,
            "state": state
        }

    finally:
        db.close()
