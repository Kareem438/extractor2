"""
Duplicate File Upload Prevention Service

Provides functionality for detecting duplicate uploads and managing file storage.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.utils.logging_config import logger


@dataclass
class DuplicateCheckResult:
    """Result of duplicate check operation"""
    is_duplicate: bool
    existing_book_id: Optional[int]
    file_readable: bool
    action: str  # 'allow', 'reject', 'overwrite'
    message: str


@dataclass
class BookSummary:
    """Summary of uploaded book for display"""
    book_id: int
    book_name: str
    file_size_bytes: int
    file_type: str
    total_pages: int
    upload_date: datetime
    processing_status: str
    file_readable: bool
    file_path: Optional[str]


class DuplicateCheckService:
    """
    Service for checking and managing duplicate file uploads.

    Provides methods for:
    - Detecting duplicate files by name and size
    - Checking file readability
    - Listing uploaded books
    """

    def __init__(self):
        """Initialize the service"""
        pass

    def check_duplicate(self, filename: str, file_size: int) -> DuplicateCheckResult:
        """
        Check if file is duplicate based on sanitized name and size.

        Args:
            filename: Original filename
            file_size: File size in bytes

        Returns:
            DuplicateCheckResult with detection results and recommended action
        """
        # Import sanitize function
        from src.utils.sanitization import sanitize_book_name

        # Sanitize the filename for comparison (matches DB unique constraint)
        sanitized_filename = sanitize_book_name(filename)

        db = SessionLocal()
        try:
            # Query for existing books with same sanitized name and size
            query = text("""
                SELECT book_id, book_name, file_path, upload_date, sanitized_name
                FROM books_metadata
                WHERE sanitized_name = :sanitized_name
                AND file_size_bytes = :file_size
                ORDER BY upload_date DESC
                LIMIT 1
            """)

            result = db.execute(query, {"sanitized_name": sanitized_filename, "file_size": file_size})
            row = result.fetchone()

            if not row:
                # No duplicate found
                return DuplicateCheckResult(
                    is_duplicate=False,
                    existing_book_id=None,
                    file_readable=False,
                    action='allow',
                    message='No duplicate found. Proceeding with upload.'
                )

            # Duplicate found - check if file is readable
            existing_book_id = row[0]
            existing_book_name = row[1]
            file_path = row[2]
            upload_date = row[3]

            if not file_path:
                # Old record without file_path, allow overwrite
                logger.warning(f"Book {existing_book_id} has no file_path. Allowing overwrite.")
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_book_id=existing_book_id,
                    file_readable=False,
                    action='overwrite',
                    message=f'Previous upload has missing file path. Re-uploading...'
                )

            # Check if file is readable
            file_readable = self.is_file_readable(file_path)

            if file_readable:
                # File exists and is readable - reject upload
                formatted_date = upload_date.strftime("%Y-%m-%d %H:%M") if upload_date else "unknown date"
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_book_id=existing_book_id,
                    file_readable=True,
                    action='reject',
                    message=f"This file has already been uploaded. Book: '{existing_book_name}' (uploaded on {formatted_date}). Please use the existing book or rename your file."
                )
            else:
                # File corrupted or missing - allow overwrite
                logger.warning(f"Book {existing_book_id} file not readable: {file_path}. Allowing overwrite.")
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_book_id=existing_book_id,
                    file_readable=False,
                    action='overwrite',
                    message=f'Previous upload was corrupted or missing. Re-uploading and overwriting...'
                )

        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            # On error, allow upload to proceed
            return DuplicateCheckResult(
                is_duplicate=False,
                existing_book_id=None,
                file_readable=False,
                action='allow',
                message='Duplicate check failed. Proceeding with upload.'
            )
        finally:
            db.close()

    def is_file_readable(self, file_path: str) -> bool:
        """
        Check if file exists and is readable.

        Args:
            file_path: Path to file

        Returns:
            True if file is readable, False otherwise
        """
        try:
            if not file_path or not os.path.exists(file_path):
                return False

            # Try to read first 1KB to verify file is readable
            with open(file_path, 'rb') as f:
                f.read(1024)
            return True
        except Exception as e:
            logger.debug(f"File not readable: {file_path} - {e}")
            return False

    def get_uploaded_books(self, limit: int = 10, offset: int = 0) -> tuple[List[BookSummary], int]:
        """
        Get list of uploaded books with metadata.

        Args:
            limit: Maximum number of books to return
            offset: Pagination offset

        Returns:
            Tuple of (list of BookSummary objects, total count)
        """
        db = SessionLocal()
        try:
            # Get total count
            count_query = text("SELECT COUNT(*) FROM books_metadata")
            total = db.execute(count_query).scalar() or 0

            # Get books
            query = text("""
                SELECT
                    book_id,
                    book_name,
                    file_size_bytes,
                    file_type,
                    total_pages,
                    upload_date,
                    processing_status,
                    file_path
                FROM books_metadata
                ORDER BY upload_date DESC
                LIMIT :limit OFFSET :offset
            """)

            result = db.execute(query, {"limit": limit, "offset": offset})
            rows = result.fetchall()

            books = []
            for row in rows:
                file_readable = self.is_file_readable(row[7]) if row[7] else False

                books.append(BookSummary(
                    book_id=row[0],
                    book_name=row[1],
                    file_size_bytes=row[2],
                    file_type=row[3],
                    total_pages=row[4],
                    upload_date=row[5],
                    processing_status=row[6],
                    file_readable=file_readable,
                    file_path=row[7]
                ))

            return books, total

        except Exception as e:
            logger.error(f"Error getting uploaded books: {e}")
            return [], 0
        finally:
            db.close()

    def sanitize_file_path(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename

        Raises:
            ValueError: If filename contains invalid characters
        """
        # Remove any directory components
        filename = os.path.basename(filename)

        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/'):
            raise ValueError(f"Invalid filename: {filename}")

        # Replace spaces and special characters
        filename = filename.replace(' ', '_')

        return filename

    def ensure_storage_dir(self, storage_path: str) -> None:
        """
        Ensure storage directory exists with proper permissions.

        Args:
            storage_path: Path to storage directory
        """
        try:
            os.makedirs(storage_path, exist_ok=True, mode=0o755)
            logger.info(f"Storage directory ready: {storage_path}")
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise

    def get_storage_location(self) -> str:
        """
        Get the configured storage location for uploaded files.

        Returns:
            Path to storage directory
        """
        # Import here to avoid circular dependency
        from src.services.storage_migration_service import StorageMigrationService

        migration_service = StorageMigrationService()
        active_location = migration_service.get_active_location()

        if active_location:
            return active_location.path

        # Fallback to environment variable
        storage_path = os.getenv('UPLOAD_STORAGE_PATH')

        if not storage_path:
            # Default to /tmp/book_uploads if not configured
            storage_path = "/tmp/book_uploads"
            logger.warning(f"No active storage location. Using default: {storage_path}")

            # Initialize default location
            migration_service.initialize_default_location()

        return storage_path
