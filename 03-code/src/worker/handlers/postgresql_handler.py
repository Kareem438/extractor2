"""
PostgreSQL Input/Output Handler

Handles reading from and writing to PostgreSQL tables for pipeline steps.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import text
from src.database.connection import engine
import logging

logger = logging.getLogger(__name__)


class PostgreSQLHandler:
    """Handler for PostgreSQL read/write operations"""

    def __init__(self, table_prefix: str):
        """
        Initialize PostgreSQL handler for a specific book.

        Args:
            table_prefix: Table prefix for this book (e.g., 'book1_example')
        """
        self.table_prefix = table_prefix

    def read_entity_data(
        self,
        entity_type: str,
        entity_id: int,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Read entity data from PostgreSQL.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID in the table
            fields: List of fields to read (None = all fields)

        Returns:
            Dictionary of field_name -> value

        Raises:
            ValueError: If entity not found
        """
        # Determine table name
        if entity_type == "paragraph":
            table_name = f"raw_{self.table_prefix}_paragraph_images"
        elif entity_type == "diagram":
            table_name = f"raw_{self.table_prefix}_diagram_images"
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Build query
        if fields:
            fields_str = ", ".join(fields)
        else:
            fields_str = "*"

        sql = text(f"""
        SELECT {fields_str}
        FROM {table_name}
        WHERE id = :entity_id
        """)

        with engine.connect() as conn:
            result = conn.execute(sql, {"entity_id": entity_id})
            row = result.fetchone()

            if row is None:
                raise ValueError(
                    f"Entity not found: {entity_type} with id {entity_id}"
                )

            # Convert row to dictionary
            return dict(row._mapping)

    def write_entity_field(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        value: Any
    ) -> bool:
        """
        Write a single field value to PostgreSQL.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID in the table
            field_name: Column name to update
            value: Value to write

        Returns:
            True if successful

        Raises:
            ValueError: If entity not found or field invalid
        """
        # Determine table name
        if entity_type == "paragraph":
            table_name = f"raw_{self.table_prefix}_paragraph_images"
        elif entity_type == "diagram":
            table_name = f"raw_{self.table_prefix}_diagram_images"
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Validate field name (prevent SQL injection)
        if not self._is_valid_column_name(field_name):
            raise ValueError(f"Invalid column name: {field_name}")

        # Update query
        sql = text(f"""
        UPDATE {table_name}
        SET {field_name} = :value,
            updated_at = NOW()
        WHERE id = :entity_id
        """)

        with engine.connect() as conn:
            result = conn.execute(
                sql,
                {"entity_id": entity_id, "value": value}
            )
            conn.commit()

            if result.rowcount == 0:
                raise ValueError(
                    f"Entity not found: {entity_type} with id {entity_id}"
                )

            logger.info(
                f"Updated {entity_type} {entity_id} field '{field_name}' "
                f"with value of length {len(str(value))}"
            )

            return True

    def write_knowledge_unit_field(
        self,
        unit_id: int,
        field_name: str,
        value: Any
    ) -> bool:
        """
        Write a field value to knowledge_units table.

        Args:
            unit_id: Knowledge unit ID
            field_name: Column name to update
            value: Value to write

        Returns:
            True if successful

        Raises:
            ValueError: If unit not found or field invalid
        """
        table_name = f"{self.table_prefix}_knowledge_units"

        # Validate field name
        if not self._is_valid_column_name(field_name):
            raise ValueError(f"Invalid column name: {field_name}")

        # Update query
        sql = text(f"""
        UPDATE {table_name}
        SET {field_name} = :value,
            updated_at = NOW()
        WHERE unit_id = :unit_id
        """)

        with engine.connect() as conn:
            result = conn.execute(
                sql,
                {"unit_id": unit_id, "value": value}
            )
            conn.commit()

            if result.rowcount == 0:
                raise ValueError(f"Knowledge unit not found: {unit_id}")

            logger.info(
                f"Updated knowledge_unit {unit_id} field '{field_name}' "
                f"with value of length {len(str(value))}"
            )

            return True

    def read_field(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str
    ) -> Any:
        """
        Read a single field value from PostgreSQL.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_id: Entity ID
            field_name: Column name to read

        Returns:
            Field value

        Raises:
            ValueError: If entity or field not found
        """
        data = self.read_entity_data(entity_type, entity_id, fields=[field_name])
        return data.get(field_name)

    def _is_valid_column_name(self, column_name: str) -> bool:
        """
        Validate column name to prevent SQL injection.

        Args:
            column_name: Column name to validate

        Returns:
            True if valid column name
        """
        # Allow only alphanumeric, underscore
        import re
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, column_name))

    def batch_read_entities(
        self,
        entity_type: str,
        entity_ids: List[int],
        fields: Optional[List[str]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Read multiple entities in a single query for efficiency.

        Args:
            entity_type: 'paragraph' or 'diagram'
            entity_ids: List of entity IDs
            fields: List of fields to read

        Returns:
            Dictionary mapping entity_id -> {field_name: value}
        """
        if not entity_ids:
            return {}

        # Determine table name
        if entity_type == "paragraph":
            table_name = f"raw_{self.table_prefix}_paragraph_images"
        elif entity_type == "diagram":
            table_name = f"raw_{self.table_prefix}_diagram_images"
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Build query
        if fields:
            fields_str = ", ".join(["id"] + fields)
        else:
            fields_str = "*"

        sql = text(f"""
        SELECT {fields_str}
        FROM {table_name}
        WHERE id = ANY(:entity_ids)
        """)

        with engine.connect() as conn:
            result = conn.execute(sql, {"entity_ids": entity_ids})

            entities = {}
            for row in result:
                row_dict = dict(row._mapping)
                entity_id = row_dict.pop('id')
                entities[entity_id] = row_dict

            return entities
