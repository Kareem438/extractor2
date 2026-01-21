"""
CHUNK-029: Database Service - Attribute Keys

Service for managing attribute key names (40 attributes).
Handles retrieval and updates of attribute key names with protection for system-reserved attributes.
"""

from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.logging_config import logger


class AttributeKeyService:
    """
    Service for managing attribute keys.

    Provides methods for retrieving and updating attribute key names.
    Attributes 1-8 are system-reserved and cannot be edited.
    Attributes 9-80 are user-defined and can be edited.
    """

    def get_attribute_keys(self, book_id: int) -> dict:
        """
        Get all 80 attribute key names.

        Retrieves attribute keys from the attribute_keys table and returns
        them as a dictionary mapping attribute number to key name.

        Args:
            book_id: Book ID for table lookup

        Returns:
            dict: Dictionary mapping attr_number to key_name
                {1: 'related_image', 2: 'ocr_text_paddleocr', ..., 80: ''}

        Example:
            >>> service = AttributeKeyService()
            >>> keys = service.get_attribute_keys(1)
            >>> print(keys[1])  # 'related_image'
            >>> print(keys[9])  # 'Difficulty Level' (user-defined)
        """
        table_name = get_table_name(book_id, 'attribute_keys')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT attr_number, key_name
                FROM {table_name}
                ORDER BY attr_number
            """)

            result = db.execute(sql)
            rows = result.fetchall()

            # Convert to dict: {1: "related_image", 2: "ocr_text_paddleocr", ...}
            keys = {row.attr_number: row.key_name for row in rows}

            logger.debug(f"Retrieved {len(keys)} attribute keys for book {book_id}")
            return keys

        finally:
            db.close()

    def get_attribute_key_details(self, book_id: int) -> list[dict]:
        """
        Get all attribute key details including metadata.

        Retrieves full attribute key information including system-reserved status,
        editability, description, and placeholder examples.

        Args:
            book_id: Book ID for table lookup

        Returns:
            list[dict]: List of attribute key dicts with:
                - attr_number: Attribute number (1-80)
                - key_name: Key name
                - is_system_reserved: Boolean (TRUE for 1-8)
                - is_editable: Boolean (FALSE for 1-8)
                - description: Description
                - placeholder_example: Example value
                - created_at: Timestamp
                - updated_at: Timestamp

        Example:
            >>> service = AttributeKeyService()
            >>> details = service.get_attribute_key_details(1)
            >>> for attr in details:
            ...     if attr['is_system_reserved']:
            ...         print(f"{attr['attr_number']}: {attr['key_name']} (reserved)")
        """
        table_name = get_table_name(book_id, 'attribute_keys')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT
                    attr_number, key_name, is_system_reserved, is_editable,
                    description, placeholder_example, created_at, updated_at
                FROM {table_name}
                ORDER BY attr_number
            """)

            result = db.execute(sql)
            rows = result.fetchall()

            # Convert to list of dicts
            details = [
                {
                    'attr_number': row.attr_number,
                    'key_name': row.key_name,
                    'is_system_reserved': row.is_system_reserved,
                    'is_editable': row.is_editable,
                    'description': row.description,
                    'placeholder_example': row.placeholder_example,
                    'created_at': row.created_at,
                    'updated_at': row.updated_at
                }
                for row in rows
            ]

            return details

        finally:
            db.close()

    def update_attribute_keys(self, book_id: int, key_updates: dict) -> bool:
        """
        Update attribute key names.

        Updates specified attribute key names. System-reserved attributes (1-8)
        cannot be edited and will raise a ValueError if attempted.

        Args:
            book_id: Book ID for table lookup
            key_updates: Dict mapping attr_number to new key_name
                {9: 'Custom Difficulty', 18: 'Source Reference'}

        Returns:
            bool: True if updated successfully

        Raises:
            ValueError: If attempting to edit system-reserved attributes (1-8)

        Example:
            >>> service = AttributeKeyService()
            >>> service.update_attribute_keys(1, {
            ...     9: 'Custom Difficulty',
            ...     18: 'Source Reference',
            ...     19: 'Related Topics'
            ... })
        """
        if not key_updates:
            return True  # Nothing to update

        # Check for attempts to edit system-reserved attributes (1-8) or invalid numbers (> 80)
        reserved_attrs = [num for num in key_updates.keys() if 1 <= num <= 8]
        invalid_attrs = [num for num in key_updates.keys() if num > 80]
        if reserved_attrs:
            raise ValueError(
                f"Cannot edit system-reserved attributes: {reserved_attrs}. "
                "Attributes 1-8 are system-reserved and not editable."
            )
        if invalid_attrs:
            raise ValueError(
                f"Invalid attribute numbers: {invalid_attrs}. "
                "Valid attribute numbers are 1-80 (1-8 system-reserved, 9-80 user-defined)."
            )

        table_name = get_table_name(book_id, 'attribute_keys')
        db = SessionLocal()

        try:
            # Update each attribute key
            for attr_num, key_name in key_updates.items():
                sql = text(f"""
                    UPDATE {table_name}
                    SET key_name = :key_name, updated_at = NOW()
                    WHERE attr_number = :attr_num AND is_editable = TRUE
                """)

                db.execute(sql, {'key_name': key_name, 'attr_num': attr_num})

            db.commit()

            logger.info(f"Updated {len(key_updates)} attribute keys for book {book_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update attribute keys: {e}")
            raise
        finally:
            db.close()

    def get_user_defined_keys(self, book_id: int) -> dict:
        """
        Get only user-defined attribute keys (9-80).

        Returns only the 72 user-defined attributes, excluding system-reserved ones.

        Args:
            book_id: Book ID for table lookup

        Returns:
            dict: Dictionary mapping attr_number to key_name (9-80 only)

        Example:
            >>> service = AttributeKeyService()
            >>> user_keys = service.get_user_defined_keys(1)
            >>> print(len(user_keys))  # 72 (attributes 9-80)
        """
        table_name = get_table_name(book_id, 'attribute_keys')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT attr_number, key_name
                FROM {table_name}
                WHERE attr_number BETWEEN 9 AND 80
                ORDER BY attr_number
            """)

            result = db.execute(sql)
            rows = result.fetchall()

            # Convert to dict
            keys = {row.attr_number: row.key_name for row in rows}

            return keys

        finally:
            db.close()

    def get_system_reserved_keys(self, book_id: int) -> dict:
        """
        Get only system-reserved attribute keys (1-8).

        Returns only the 8 system-reserved attributes.

        Args:
            book_id: Book ID for table lookup

        Returns:
            dict: Dictionary mapping attr_number to key_name (1-8 only)

        Example:
            >>> service = AttributeKeyService()
            >>> system_keys = service.get_system_reserved_keys(1)
            >>> print(len(system_keys))  # 8 (attributes 1-8)
            >>> print(system_keys[1])  # 'related_image'
        """
        table_name = get_table_name(book_id, 'attribute_keys')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT attr_number, key_name
                FROM {table_name}
                WHERE attr_number BETWEEN 1 AND 8
                ORDER BY attr_number
            """)

            result = db.execute(sql)
            rows = result.fetchall()

            # Convert to dict
            keys = {row.attr_number: row.key_name for row in rows}

            return keys

        finally:
            db.close()
