"""
CHUNK-032: API Routes - Upload

File upload endpoint with metadata creation and table initialization.
"""

import os
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.database.services.book_settings_service import BookSettingsService
from src.database.services.processing_state_service import ProcessingStateService
from src.database.services.attribute_key_service import AttributeKeyService
from src.services.duplicate_check_service import DuplicateCheckService
from src.utils.sanitization import sanitize_book_name, generate_table_prefix
from src.utils.file_detection import detect_file_type
from src.utils.logging_config import logger
import fitz  # PyMuPDF
import json

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    book_name: str = Form(...),
    language_setting: str = Form("auto"),
    ocr_mode: str = Form("auto"),
    llm_model: str = Form("gpt-4o-mini"),
    min_chunk_size: int = Form(100),
    max_chunk_size: int = Form(500),
    overlap_size: int = Form(50),
    partial_processing_enabled: bool = Form(False),
    partial_processing_pages: int = Form(0),
    checkpoint_frequency: int = Form(10),
    attribute_keys: str = Form("{}"),  # JSON string
):
    """
    Upload file and create book metadata.

    Args:
        file: Uploaded file (PDF/image)
        book_name: Name for the book
        language_setting: Language setting (auto/english/arabic/mixed)
        ocr_mode: OCR mode (auto/tesseract/google_vision)
        llm_model: LLM model for chunking
        min_chunk_size: Minimum chunk size
        max_chunk_size: Maximum chunk size
        overlap_size: Chunk overlap size
        partial_processing_enabled: Enable partial processing
        partial_processing_pages: Number of pages for partial processing
        checkpoint_frequency: Checkpoint frequency (pages)
        attribute_keys: JSON string of custom attribute keys (attr2-attr30)

    Returns:
        dict: Book ID and success message

    Raises:
        HTTPException: If file is too large or invalid

    Example:
        >>> # Via HTTP POST
        >>> formData = new FormData()
        >>> formData.append('file', file)
        >>> formData.append('book_name', 'My Book')
        >>> response = await fetch('/api/upload', {method: 'POST', body: formData})
    """
    try:
        # Validate file size (500MB max)
        content = await file.read()
        file_size = len(content)

        if file_size > 500 * 1024 * 1024:  # 500MB
            raise HTTPException(status_code=413, detail="File too large (max 500MB)")

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Get storage location and ensure directory exists
        duplicate_service = DuplicateCheckService()
        upload_dir = duplicate_service.get_storage_location()
        duplicate_service.ensure_storage_dir(upload_dir)

        # Save file temporarily with unique name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = file.filename.replace(" ", "_")
        temp_path = os.path.join(upload_dir, f"{timestamp}_{safe_filename}")

        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(f"File uploaded: {temp_path} ({file_size} bytes)")

        # Detect file type
        file_type = detect_file_type(temp_path)
        logger.info(f"Detected file type: {file_type}")

        # Get page count (PDF-specific for now)
        total_pages = 1  # Default for images
        if file_type == 'PDF':
            try:
                doc = fitz.open(temp_path)
                total_pages = len(doc)
                doc.close()
                logger.info(f"PDF has {total_pages} pages")
            except Exception as e:
                logger.error(f"Error opening PDF: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")

        # Check for duplicates
        check_result = duplicate_service.check_duplicate(
            filename=file.filename,
            file_size=file_size
        )

        if check_result.action == 'reject':
            # File already exists and is readable - reject upload
            logger.warning(f"Duplicate upload rejected: {file.filename}")
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate_file",
                    "message": check_result.message,
                    "existing_book_id": check_result.existing_book_id
                }
            )

        # Get next book_id or use existing for overwrite
        db = SessionLocal()
        try:
            if check_result.action == 'overwrite':
                # Reuse existing book_id and overwrite corrupted file
                book_id = check_result.existing_book_id
                logger.info(f"Overwriting book {book_id} due to corrupted file: {check_result.message}")

                # Delete old file if it exists
                old_book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
                if old_book and old_book.file_path:
                    try:
                        if os.path.exists(old_book.file_path):
                            os.remove(old_book.file_path)
                            logger.info(f"Deleted corrupted file: {old_book.file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete old file: {e}")

                # Delete existing book record (will be recreated)
                db.delete(old_book)
                db.commit()
            else:
                # Normal new upload - get next book_id
                max_id = db.execute(text("SELECT MAX(book_id) FROM books_metadata")).scalar()
                book_id = (max_id or 0) + 1

            # Sanitize name and handle duplicates
            sanitized = sanitize_book_name(book_name)
            original_sanitized = sanitized

            # Check for duplicate sanitized names and append suffix if needed
            suffix = 2
            while True:
                exists = db.execute(
                    text("SELECT COUNT(*) FROM books_metadata WHERE sanitized_name = :sanitized"),
                    {"sanitized": sanitized}
                ).scalar()

                if exists == 0:
                    break

                sanitized = f"{original_sanitized}_{suffix}"
                suffix += 1
                logger.info(f"Duplicate name detected, trying: {sanitized}")

            table_prefix = generate_table_prefix(book_id, sanitized)

            if sanitized != original_sanitized:
                logger.info(f"Creating book {book_id}: {book_name} -> {sanitized} (auto-renamed from {original_sanitized})")
            else:
                logger.info(f"Creating book {book_id}: {book_name} -> {sanitized} (prefix: {table_prefix})")

            # Parse attribute keys
            try:
                attr_keys = json.loads(attribute_keys)
            except json.JSONDecodeError:
                attr_keys = {}

            # Create metadata record with file_path
            book = BooksMetadata(
                book_id=book_id,
                book_name=book_name,
                sanitized_name=sanitized,
                table_prefix=table_prefix,
                file_type=file_type,
                file_size_bytes=file_size,
                total_pages=total_pages,
                file_path=temp_path,
                processing_status='pending',
                upload_date=datetime.now()
            )
            db.add(book)
            db.commit()
            db.refresh(book)

            logger.info(f"Book metadata created: {book_id}")

            # Create book-specific tables
            from src.database.table_creator import create_book_tables
            create_book_tables(book_id, sanitized, total_pages)
            logger.info(f"Book tables created for book {book_id}")

            # Settings table already created with defaults by insert_default_settings()
            logger.info(f"Book settings initialized with defaults for book {book_id}")

            # Save attribute keys
            if attr_keys:
                attr_service = AttributeKeyService()
                attr_service.save_attribute_keys(book_id, attr_keys)
                logger.info(f"Attribute keys saved for book {book_id}: {len(attr_keys)} keys")

            # Processing state already initialized with defaults by insert_default_processing_state()
            logger.info(f"Processing state initialized for book {book_id}")

            return {
                "book_id": book_id,
                "book_name": book_name,
                "file_type": file_type,
                "total_pages": total_pages,
                "message": "Book uploaded successfully"
            }

        finally:
            db.close()

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
