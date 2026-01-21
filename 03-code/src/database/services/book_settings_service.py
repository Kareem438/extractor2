"""
CHUNK-028: Database Service - Book Settings

Service for managing book settings in single-row settings table.
Handles retrieval and updates of processing settings, OCR settings, and image settings.
"""

from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.logging_config import logger


class BookSettingsService:
    """
    Service for managing book settings.

    Provides methods for retrieving and updating book-specific settings
    stored in a single-row settings table (id=1).
    """

    def get_settings(self, book_id: int) -> dict:
        """
        Get book settings from single-row table.

        Retrieves all settings for a book including processing settings,
        OCR settings, image settings, and performance settings.

        Args:
            book_id: Book ID for table lookup

        Returns:
            dict: Settings dictionary with all fields:
                - language: 'auto', 'english', 'arabic', 'both'
                - ocr_quality: 'fast', 'balanced', 'high'
                - extraction_sensitivity: 'conservative', 'balanced', 'aggressive'
                - diagram_prompt: Text (custom Claude Vision prompt for diagrams)
                - equation_prompt: Text (custom Claude Vision prompt for equations)
                - table_prompt: Text (custom Claude Vision prompt for tables)
                - ocr_attr1_id: Integer (OCR text area 1 attribute mapping)
                - ocr_attr2_id: Integer (OCR text area 2 attribute mapping)
                - ocr_attr3_id: Integer (OCR text area 3 attribute mapping)
                - manual_attr1_id: Integer (Manual text area 1 attribute mapping)
                - manual_attr2_id: Integer (Manual text area 2 attribute mapping)
                - manual_attr3_id: Integer (Manual text area 3 attribute mapping)
                - ocr_label1: String (Label for OCR text area 1)
                - ocr_label2: String (Label for OCR text area 2)
                - ocr_label3: String (Label for OCR text area 3)
                - manual_label1: String (Label for manual text area 1)
                - manual_label2: String (Label for manual text area 2)
                - manual_label3: String (Label for manual text area 3)

        Raises:
            ValueError: If settings not found

        Example:
            >>> service = BookSettingsService()
            >>> settings = service.get_settings(1)
            >>> print(f"Language: {settings['language_setting']}")
        """
        table_name = get_table_name(book_id, 'settings')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT
                    language, ocr_quality, extraction_sensitivity,
                    diagram_prompt, equation_prompt, table_prompt,
                    ocr_attr1_id, ocr_attr2_id, ocr_attr3_id,
                    manual_attr1_id, manual_attr2_id, manual_attr3_id,
                    ocr_label1, ocr_label2, ocr_label3,
                    manual_label1, manual_label2, manual_label3
                FROM {table_name}
                WHERE id = 1
            """)

            result = db.execute(sql)
            row = result.fetchone()

            if not row:
                raise ValueError(f"Settings not found for book {book_id}")

            # Convert row to dict
            settings = {
                'language': row.language,
                'ocr_quality': row.ocr_quality,
                'extraction_sensitivity': row.extraction_sensitivity,
                'diagram_prompt': row.diagram_prompt,
                'equation_prompt': row.equation_prompt,
                'table_prompt': row.table_prompt,
                'ocr_attr1_id': row.ocr_attr1_id,
                'ocr_attr2_id': row.ocr_attr2_id,
                'ocr_attr3_id': row.ocr_attr3_id,
                'manual_attr1_id': row.manual_attr1_id,
                'manual_attr2_id': row.manual_attr2_id,
                'manual_attr3_id': row.manual_attr3_id,
                'ocr_label1': row.ocr_label1,
                'ocr_label2': row.ocr_label2,
                'ocr_label3': row.ocr_label3,
                'manual_label1': row.manual_label1,
                'manual_label2': row.manual_label2,
                'manual_label3': row.manual_label3
            }

            return settings

        finally:
            db.close()

    def update_settings(self, book_id: int, updates: dict) -> bool:
        """
        Update book settings.

        Updates specified settings fields in the single-row settings table.

        Args:
            book_id: Book ID for table lookup
            updates: Dict of settings to update:
                - language: 'auto', 'english', 'arabic', 'both'
                - ocr_quality: 'fast', 'balanced', 'high'
                - extraction_sensitivity: 'conservative', 'balanced', 'aggressive'
                - diagram_prompt: Text (custom Claude Vision prompt for diagrams)
                - equation_prompt: Text (custom Claude Vision prompt for equations)
                - table_prompt: Text (custom Claude Vision prompt for tables)
                - ocr_attr1_id: Integer (OCR text area 1 attribute mapping)
                - ocr_attr2_id: Integer (OCR text area 2 attribute mapping)
                - ocr_attr3_id: Integer (OCR text area 3 attribute mapping)
                - manual_attr1_id: Integer (Manual text area 1 attribute mapping)
                - manual_attr2_id: Integer (Manual text area 2 attribute mapping)
                - manual_attr3_id: Integer (Manual text area 3 attribute mapping)
                - ocr_label1: String (Label for OCR text area 1)
                - ocr_label2: String (Label for OCR text area 2)
                - ocr_label3: String (Label for OCR text area 3)
                - manual_label1: String (Label for manual text area 1)
                - manual_label2: String (Label for manual text area 2)
                - manual_label3: String (Label for manual text area 3)

        Returns:
            bool: True if updated successfully

        Example:
            >>> service = BookSettingsService()
            >>> service.update_settings(1, {
            ...     'language': 'english',
            ...     'ocr_quality': 'high',
            ...     'diagram_prompt': 'Analyze this diagram...'
            ... })
        """
        if not updates:
            return True  # Nothing to update

        table_name = get_table_name(book_id, 'settings')
        db = SessionLocal()

        try:
            # Build SET clause dynamically
            set_clause = ', '.join([f"{k} = :{k}" for k in updates.keys()])

            # Update single row (id=1)
            sql = text(f"""
                UPDATE {table_name}
                SET {set_clause}
                WHERE id = 1
            """)

            db.execute(sql, updates)
            db.commit()

            logger.info(f"Updated settings for book {book_id}: {list(updates.keys())}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update settings: {e}")
            raise
        finally:
            db.close()

    def get_setting(self, book_id: int, setting_name: str):
        """
        Get a single setting value.

        Convenience method to retrieve just one setting without loading all.

        Args:
            book_id: Book ID for table lookup
            setting_name: Name of setting field to retrieve

        Returns:
            Setting value (type varies by field)

        Raises:
            ValueError: If setting not found

        Example:
            >>> service = BookSettingsService()
            >>> lang = service.get_setting(1, 'language_setting')
            >>> print(f"Language: {lang}")
        """
        table_name = get_table_name(book_id, 'settings')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT {setting_name}
                FROM {table_name}
                WHERE id = 1
            """)

            result = db.execute(sql)
            row = result.fetchone()

            if not row:
                raise ValueError(f"Settings not found for book {book_id}")

            return row[0]

        finally:
            db.close()
