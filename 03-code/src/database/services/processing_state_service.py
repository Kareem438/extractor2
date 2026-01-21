"""
CHUNK-027: Database Service - Processing State

Service for managing processing state in single-row processing_state table.
Handles state updates, checkpoint saving, progress calculation, and time estimation.
"""

from datetime import datetime
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.logging_config import logger


class ProcessingStateService:
    """
    Service for managing processing state.

    Provides methods for updating processing state, saving checkpoints,
    and retrieving current state with progress calculations.
    """

    def update_state(self, book_id: int, updates: dict) -> bool:
        """
        Update processing state (single-row table).

        Automatically calculates progress_percentage if current_page is updated.
        Updates last_updated_at timestamp automatically.

        Args:
            book_id: Book ID for table lookup
            updates: Dict of fields to update with values:
                - status: 'not_started', 'processing', 'paused', 'completed', 'error'
                - current_page: Current page number being processed
                - total_pages: Total pages (if changed)
                - pages_processed: Number of pages completed
                - knowledge_units_extracted: Total KUs extracted
                - images_extracted: Total images extracted
                - ocr_retry_count: Total OCR retries
                - error_count: Total errors
                - avg_page_processing_time: Average seconds per page
                - estimated_time_remaining: Seconds remaining (calculated)
                - last_error_message: Error message
                - agent_states: JSONB dict of agent states
                - paused_at: Timestamp for pause
                - resumed_at: Timestamp for resume
                - pause_count: Number of pauses
                - processing_started_at: Start timestamp
                - processing_completed_at: Completion timestamp

        Returns:
            bool: True if updated successfully

        Example:
            >>> service = ProcessingStateService()
            >>> service.update_state(1, {
            ...     'status': 'processing',
            ...     'current_page': 45,
            ...     'pages_processed': 44,
            ...     'knowledge_units_extracted': 132
            ... })
        """
        table_name = get_table_name(book_id, 'processing_state')
        db = SessionLocal()

        try:
            # Get only the fields needed for calculations
            need_current_state = ('current_page' in updates or
                                 'avg_page_processing_time' in updates)

            total_pages = None
            current_page = None
            avg_time = None

            if need_current_state:
                sql_select = text(f"""
                    SELECT total_pages, current_page, avg_page_processing_time
                    FROM {table_name}
                    WHERE id = 1
                """)
                result = db.execute(sql_select)
                row = result.fetchone()
                if row:
                    total_pages = row.total_pages
                    current_page = row.current_page
                    avg_time = row.avg_page_processing_time

            # Override with updates if provided
            total_pages = updates.get('total_pages', total_pages or 1)

            # Calculate progress percentage if current_page is updated
            if 'current_page' in updates:
                progress = (updates['current_page'] / total_pages) * 100
                updates['progress_percentage'] = round(progress, 2)

            # Calculate estimated time remaining if avg_page_processing_time is available
            if 'avg_page_processing_time' in updates or 'current_page' in updates:
                current_page = updates.get('current_page', current_page or 0)
                avg_time = updates.get('avg_page_processing_time', avg_time)

                if avg_time and avg_time > 0:
                    remaining_pages = total_pages - current_page
                    updates['estimated_time_remaining'] = int(remaining_pages * avg_time)

            # Build SET clause dynamically
            if not updates:
                return True  # Nothing to update

            set_clause = ', '.join([f"{k} = :{k}" for k in updates.keys()])

            # Update single row (id=1)
            sql = text(f"""
                UPDATE {table_name}
                SET {set_clause}, last_updated_at = NOW()
                WHERE id = 1
            """)

            db.execute(sql, updates)
            db.commit()

            logger.info(f"Updated processing state for book {book_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update processing state: {e}")
            raise
        finally:
            db.close()

    def get_state(self, book_id: int) -> dict:
        """
        Get current processing state.

        Retrieves all state information from the single-row processing_state table.

        Args:
            book_id: Book ID for table lookup

        Returns:
            dict: Processing state with all fields:
                - status: Current status
                - current_page: Current page number
                - total_pages: Total pages
                - progress_percentage: Percentage complete
                - last_checkpoint_page: Last checkpoint page
                - checkpoint_frequency: Checkpoint frequency
                - last_checkpoint_at: Last checkpoint timestamp
                - agent_states: JSONB agent states
                - pages_processed: Pages completed
                - knowledge_units_extracted: Total KUs
                - images_extracted: Total images
                - ocr_retry_count: OCR retries
                - error_count: Error count
                - avg_page_processing_time: Average seconds per page
                - estimated_time_remaining: Seconds remaining
                - last_error_message: Last error
                - last_error_at: Last error timestamp
                - paused_at: Pause timestamp
                - resumed_at: Resume timestamp
                - pause_count: Number of pauses
                - processing_started_at: Start timestamp
                - processing_completed_at: Completion timestamp
                - last_updated_at: Last update timestamp

        Raises:
            ValueError: If processing state not found

        Example:
            >>> service = ProcessingStateService()
            >>> state = service.get_state(1)
            >>> print(f"Progress: {state['progress_percentage']}%")
        """
        table_name = get_table_name(book_id, 'processing_state')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT
                    id, total_pages, current_page, easyocr_complete, surya_ocr_complete,
                    tesseract_complete, images_processed, evaluation_complete, splitter_complete,
                    marker_complete, current_agent, status, last_updated, started_at, completed_at,
                    pages_scanned, easyocr_pages_processed, surya_pages_processed,
                    tesseract_pages_processed, pages_split_verified
                FROM {table_name}
                WHERE id = 1
            """)

            result = db.execute(sql)
            row = result.fetchone()

            if not row:
                raise ValueError(f"Processing state not found for book {book_id}")

            # Calculate progress percentage based on current_page and total_pages
            progress_percentage = 0.0
            if row.total_pages and row.total_pages > 0:
                progress_percentage = (row.current_page / row.total_pages) * 100.0

            # Convert row to dict - using actual columns that exist
            state = {
                'status': row.status or 'pending',
                'current_page': row.current_page or 0,
                'total_pages': row.total_pages or 0,
                'progress_percentage': progress_percentage,
                'pages_processed': row.current_page or 0,
                'knowledge_units_extracted': 0,  # Not tracked in current schema
                'images_extracted': 1 if row.images_processed else 0,
                'easyocr_complete': row.easyocr_complete or False,
                'surya_ocr_complete': row.surya_ocr_complete or False,
                'tesseract_complete': row.tesseract_complete or False,
                'evaluation_complete': row.evaluation_complete or False,
                'splitter_complete': row.splitter_complete or False,
                'marker_complete': row.marker_complete or False,
                'current_agent': row.current_agent,
                'started_at': row.started_at,
                'completed_at': row.completed_at,
                'last_updated': row.last_updated,
                'pages_scanned': row.pages_scanned or 0,
                'easyocr_pages_processed': row.easyocr_pages_processed or 0,
                'surya_pages_processed': row.surya_pages_processed or 0,
                'tesseract_pages_processed': row.tesseract_pages_processed or 0,
                'pages_split_verified': row.pages_split_verified or 0
            }

            return state

        finally:
            db.close()

    def save_checkpoint(self, book_id: int, page_number: int) -> bool:
        """
        Save checkpoint at specified page.

        Updates last_checkpoint_page and last_checkpoint_at timestamp.

        Args:
            book_id: Book ID for table lookup
            page_number: Page number to save as checkpoint

        Returns:
            bool: True if checkpoint saved successfully

        Example:
            >>> service = ProcessingStateService()
            >>> service.save_checkpoint(1, page_number=50)
        """
        return self.update_state(book_id, {
            'last_checkpoint_page': page_number,
            'last_checkpoint_at': datetime.now()
        })

    def increment_counters(self, book_id: int, counter_updates: dict) -> bool:
        """
        Increment counter fields atomically.

        Useful for incrementing counters like pages_processed, knowledge_units_extracted,
        images_extracted, error_count, etc.

        Args:
            book_id: Book ID for table lookup
            counter_updates: Dict of counter increments:
                - pages_processed: Increment by N
                - knowledge_units_extracted: Increment by N
                - images_extracted: Increment by N
                - ocr_retry_count: Increment by N
                - error_count: Increment by N

        Returns:
            bool: True if incremented successfully

        Example:
            >>> service = ProcessingStateService()
            >>> service.increment_counters(1, {
            ...     'pages_processed': 1,
            ...     'knowledge_units_extracted': 3,
            ...     'images_extracted': 2
            ... })
        """
        table_name = get_table_name(book_id, 'processing_state')
        db = SessionLocal()

        try:
            # Build SET clause for increments
            set_clause = ', '.join([f"{k} = {k} + :{k}" for k in counter_updates.keys()])

            sql = text(f"""
                UPDATE {table_name}
                SET {set_clause}, last_updated_at = NOW()
                WHERE id = 1
            """)

            db.execute(sql, counter_updates)
            db.commit()

            logger.debug(f"Incremented counters for book {book_id}: {counter_updates}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to increment counters: {e}")
            raise
        finally:
            db.close()
