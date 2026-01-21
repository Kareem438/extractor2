"""
Storage Migration Service

Manages storage location configuration and file migration.
"""

import os
import shutil
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.utils.logging_config import logger


@dataclass
class StorageLocationInfo:
    """Storage location information."""
    location_id: int
    path: str
    is_active: bool
    created_at: datetime
    notes: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of storage migration operation."""
    success: bool
    files_migrated: int
    files_failed: int
    old_location: str
    new_location: str
    message: str
    errors: List[str]


class StorageMigrationService:
    """
    Service for managing storage locations and file migration.

    Provides methods for:
    - Setting new storage location
    - Migrating files between locations
    - Getting storage location history
    """

    def __init__(self):
        """Initialize the service."""
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure storage_locations table exists."""
        db = SessionLocal()
        try:
            create_table_sql = text("""
                CREATE TABLE IF NOT EXISTS storage_locations (
                    location_id SERIAL PRIMARY KEY,
                    path VARCHAR(500) NOT NULL UNIQUE,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    notes TEXT
                )
            """)
            db.execute(create_table_sql)
            db.commit()
            logger.info("Storage locations table ready")
        except Exception as e:
            logger.error(f"Error creating storage_locations table: {e}")
            db.rollback()
        finally:
            db.close()

    def get_active_location(self) -> Optional[StorageLocationInfo]:
        """
        Get the currently active storage location.

        Returns:
            StorageLocationInfo if found, None otherwise
        """
        db = SessionLocal()
        try:
            query = text("""
                SELECT location_id, path, is_active, created_at, notes
                FROM storage_locations
                WHERE is_active = TRUE
                LIMIT 1
            """)
            result = db.execute(query)
            row = result.fetchone()

            if row:
                return StorageLocationInfo(
                    location_id=row[0],
                    path=row[1],
                    is_active=row[2],
                    created_at=row[3],
                    notes=row[4]
                )
            return None
        except Exception as e:
            logger.error(f"Error getting active location: {e}")
            return None
        finally:
            db.close()

    def get_location_history(self) -> List[StorageLocationInfo]:
        """
        Get all storage locations history.

        Returns:
            List of StorageLocationInfo objects, ordered by created_at DESC
        """
        db = SessionLocal()
        try:
            query = text("""
                SELECT location_id, path, is_active, created_at, notes
                FROM storage_locations
                ORDER BY created_at DESC
            """)
            result = db.execute(query)
            rows = result.fetchall()

            locations = []
            for row in rows:
                locations.append(StorageLocationInfo(
                    location_id=row[0],
                    path=row[1],
                    is_active=row[2],
                    created_at=row[3],
                    notes=row[4]
                ))
            return locations
        except Exception as e:
            logger.error(f"Error getting location history: {e}")
            return []
        finally:
            db.close()

    def set_storage_location(self, new_path: str, migrate_files: bool = True) -> MigrationResult:
        """
        Set new storage location and optionally migrate files.

        Args:
            new_path: New storage location path
            migrate_files: Whether to migrate existing files (default: True)

        Returns:
            MigrationResult with migration details
        """
        db = SessionLocal()
        errors = []
        files_migrated = 0
        files_failed = 0

        try:
            # Normalize path
            new_path = os.path.abspath(new_path)

            # Get current active location
            old_location = self.get_active_location()
            old_path = old_location.path if old_location else None

            # Check if new path is same as current
            if old_path and os.path.abspath(old_path) == new_path:
                return MigrationResult(
                    success=False,
                    files_migrated=0,
                    files_failed=0,
                    old_location=old_path,
                    new_location=new_path,
                    message="New location is the same as current location",
                    errors=["Path unchanged"]
                )

            # Create new directory if it doesn't exist
            try:
                os.makedirs(new_path, exist_ok=True, mode=0o755)
                logger.info(f"Created storage directory: {new_path}")
            except Exception as e:
                error_msg = f"Failed to create directory: {e}"
                logger.error(error_msg)
                return MigrationResult(
                    success=False,
                    files_migrated=0,
                    files_failed=0,
                    old_location=old_path or "none",
                    new_location=new_path,
                    message="Failed to create new storage directory",
                    errors=[error_msg]
                )

            # Migrate files if requested and old location exists
            if migrate_files and old_path and os.path.exists(old_path):
                logger.info(f"Migrating files from {old_path} to {new_path}")

                # Get all books with file paths
                books_query = text("""
                    SELECT book_id, file_path, book_name
                    FROM books_metadata
                    WHERE file_path IS NOT NULL
                """)
                books = db.execute(books_query).fetchall()

                for book_id, file_path, book_name in books:
                    if not file_path or not os.path.exists(file_path):
                        continue

                    try:
                        # Get filename from old path
                        filename = os.path.basename(file_path)
                        new_file_path = os.path.join(new_path, filename)

                        # Copy file to new location
                        shutil.copy2(file_path, new_file_path)

                        # Update database with new path
                        update_query = text("""
                            UPDATE books_metadata
                            SET file_path = :new_path
                            WHERE book_id = :book_id
                        """)
                        db.execute(update_query, {"new_path": new_file_path, "book_id": book_id})

                        files_migrated += 1
                        logger.info(f"Migrated: {book_name} -> {new_file_path}")

                    except Exception as e:
                        files_failed += 1
                        error_msg = f"Failed to migrate {book_name}: {e}"
                        errors.append(error_msg)
                        logger.error(error_msg)

                db.commit()

            # Deactivate old location(s)
            deactivate_query = text("""
                UPDATE storage_locations
                SET is_active = FALSE
                WHERE is_active = TRUE
            """)
            db.execute(deactivate_query)

            # Check if location already exists
            check_query = text("""
                SELECT location_id FROM storage_locations
                WHERE path = :path
            """)
            existing = db.execute(check_query, {"path": new_path}).fetchone()

            if existing:
                # Reactivate existing location
                activate_query = text("""
                    UPDATE storage_locations
                    SET is_active = TRUE
                    WHERE location_id = :location_id
                """)
                db.execute(activate_query, {"location_id": existing[0]})
            else:
                # Insert new location
                insert_query = text("""
                    INSERT INTO storage_locations (path, is_active, notes)
                    VALUES (:path, TRUE, :notes)
                """)
                notes = f"Migrated {files_migrated} files" if files_migrated > 0 else "New location"
                db.execute(insert_query, {"path": new_path, "notes": notes})

            db.commit()

            message = f"Storage location updated to {new_path}"
            if files_migrated > 0:
                message += f". Migrated {files_migrated} files"
            if files_failed > 0:
                message += f". Failed to migrate {files_failed} files"

            return MigrationResult(
                success=True,
                files_migrated=files_migrated,
                files_failed=files_failed,
                old_location=old_path or "none",
                new_location=new_path,
                message=message,
                errors=errors
            )

        except Exception as e:
            db.rollback()
            error_msg = f"Error setting storage location: {e}"
            logger.error(error_msg, exc_info=True)
            return MigrationResult(
                success=False,
                files_migrated=files_migrated,
                files_failed=files_failed,
                old_location=old_path or "none",
                new_location=new_path,
                message="Failed to set storage location",
                errors=[error_msg]
            )
        finally:
            db.close()

    def initialize_default_location(self):
        """
        Initialize default storage location if none exists.
        Uses /tmp/book_uploads as default.
        """
        active = self.get_active_location()
        if not active:
            default_path = "/tmp/book_uploads"
            logger.info(f"No active location found. Setting default: {default_path}")
            result = self.set_storage_location(default_path, migrate_files=False)
            if result.success:
                logger.info("Default storage location initialized")
            else:
                logger.error(f"Failed to initialize default location: {result.message}")
