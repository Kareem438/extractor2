"""
CHUNK-024: Database Service - Knowledge Units CRUD

CRUD operations for knowledge units table with pagination, filtering, and merging.
Handles batch inserts, updates, and record merging operations.
"""

from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.logging_config import logger


class KnowledgeUnitService:
    """
    Service for CRUD operations on knowledge units table.

    Provides methods for inserting, querying, updating, and merging
    knowledge units in book-specific tables.
    """

    def insert_knowledge_units(self, book_id: int, knowledge_units: list[dict]) -> int:
        """
        Batch insert knowledge units.

        Inserts multiple knowledge units in a single transaction for efficiency.
        Creates records in the book-specific knowledge_units table.

        Args:
            book_id: Book ID for table lookup
            knowledge_units: List of knowledge unit dicts with fields:
                - text_content (required): Text content
                - text_length (required): Character count
                - line_count (required): Number of lines
                - page_number (required): Source page number
                - language (required): Detected language
                - confidence_score (required): Extraction confidence (0-100)
                - position_x, position_y, position_width, position_height (optional)
                - extraction_method (optional)
                - raw_knowledge_unit_id (optional): FK to raw data

        Returns:
            int: Number of records inserted

        Example:
            >>> service = KnowledgeUnitService()
            >>> units = [
            ...     {'text_content': 'Text 1', 'text_length': 6, 'line_count': 1,
            ...      'page_number': 1, 'language': 'english', 'confidence_score': 95.0}
            ... ]
            >>> count = service.insert_knowledge_units(1, units)
            >>> print(f"Inserted {count} units")
        """
        if not knowledge_units:
            return 0

        table_name = get_table_name(book_id, 'knowledge_units')
        db = SessionLocal()

        try:
            # Build insert query with all fields
            sql = text(f"""
                INSERT INTO {table_name} (
                    text_content, text_length, line_count, page_number,
                    language, confidence_score, extraction_method,
                    position_x, position_y, position_width, position_height,
                    raw_knowledge_unit_id, verified
                )
                VALUES (
                    :text_content, :text_length, :line_count, :page_number,
                    :language, :confidence_score, :extraction_method,
                    :position_x, :position_y, :position_width, :position_height,
                    :raw_knowledge_unit_id, :verified
                )
            """)

            # Normalize each unit to include all fields
            normalized_units = []
            for unit in knowledge_units:
                normalized = {
                    'text_content': unit['text_content'],
                    'text_length': unit['text_length'],
                    'line_count': unit['line_count'],
                    'page_number': unit['page_number'],
                    'language': unit['language'],
                    'confidence_score': unit['confidence_score'],
                    'extraction_method': unit.get('extraction_method'),
                    'position_x': unit.get('position_x'),
                    'position_y': unit.get('position_y'),
                    'position_width': unit.get('position_width'),
                    'position_height': unit.get('position_height'),
                    'raw_knowledge_unit_id': unit.get('raw_knowledge_unit_id'),
                    'verified': unit.get('verified', False)
                }
                normalized_units.append(normalized)

            # Execute batch insert
            db.execute(sql, normalized_units)
            db.commit()

            logger.info(f"Inserted {len(knowledge_units)} knowledge units into {table_name}")
            return len(knowledge_units)

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to insert knowledge units: {e}")
            raise
        finally:
            db.close()

    def get_knowledge_units(self, book_id: int, page: int = 1, limit: int = 50,
                           verified: bool = None, page_number: int = None) -> dict:
        """
        Get paginated knowledge units with optional filtering.

        Retrieves knowledge units with pagination and optional filters for
        verification status and page number.

        Args:
            book_id: Book ID for table lookup
            page: Page number for pagination (1-indexed, default: 1)
            limit: Number of records per page (default: 50)
            verified: Filter by verified status (None = all, True = verified only, False = unverified only)
            page_number: Filter by source page number (None = all pages)

        Returns:
            dict: {
                'records': list[dict] - Knowledge unit records
                'total': int - Total number of records matching filter
                'page': int - Current page number
                'limit': int - Records per page
                'has_more': bool - Whether there are more pages
            }

        Example:
            >>> service = KnowledgeUnitService()
            >>> result = service.get_knowledge_units(1, page=1, limit=20, verified=False)
            >>> print(f"Found {result['total']} unverified units")
        """
        table_name = get_table_name(book_id, 'knowledge_units')
        db = SessionLocal()

        try:
            # Build WHERE clause
            where_conditions = []
            params = {}

            if verified is not None:
                where_conditions.append("verified = :verified")
                params['verified'] = verified

            if page_number is not None:
                where_conditions.append("page_number = :page_number")
                params['page_number'] = page_number

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # Count total records
            count_sql = text(f"""
                SELECT COUNT(*) FROM {table_name}
                {where_clause}
            """)
            total = db.execute(count_sql, params).scalar()

            # Get paginated records
            offset = (page - 1) * limit
            params['limit'] = limit
            params['offset'] = offset

            query_sql = text(f"""
                SELECT
                    unit_id, text_content, page_number,
                    ocr_method, confidence_score,
                    language, chapter, topic, sub_topic,
                    verified, notes,
                    attr1_value, attr2_value, attr3_value, attr4_value, attr5_value,
                    attr6_value, attr7_value, attr8_value, attr9_value, attr10_value,
                    created_at, updated_at
                FROM {table_name}
                {where_clause}
                ORDER BY page_number ASC, unit_id ASC
                LIMIT :limit OFFSET :offset
            """)

            result = db.execute(query_sql, params)
            records = [dict(row._mapping) for row in result]

            return {
                'records': records,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total
            }

        except Exception as e:
            logger.error(f"Failed to get knowledge units: {e}")
            raise
        finally:
            db.close()

    def update_knowledge_unit(self, book_id: int, record_id: int, updates: dict) -> bool:
        """
        Update single knowledge unit.

        Updates specified fields of a knowledge unit record. Only fields
        present in the updates dict will be modified.

        Args:
            book_id: Book ID for table lookup
            record_id: ID of the record to update
            updates: Dict of fields to update, e.g.:
                - text_content: Updated text
                - verified: True/False
                - chapter, topic, sub_topic: Hierarchy updates
                - confidence_score: Updated confidence

        Returns:
            bool: True if record was updated, False if not found

        Example:
            >>> service = KnowledgeUnitService()
            >>> success = service.update_knowledge_unit(
            ...     1, 123,
            ...     {'verified': True, 'chapter': 'Chapter 1'}
            ... )
        """
        if not updates:
            return False

        table_name = get_table_name(book_id, 'knowledge_units')
        db = SessionLocal()

        try:
            # Build SET clause
            set_clauses = []
            params = {'record_id': record_id}

            for field, value in updates.items():
                # Prevent updating primary key or timestamps
                if field not in ['id', 'created_at']:
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = value

            if not set_clauses:
                return False

            # Always update updated_at
            set_clauses.append("updated_at = NOW()")

            set_clause = ", ".join(set_clauses)

            update_sql = text(f"""
                UPDATE {table_name}
                SET {set_clause}
                WHERE unit_id = :record_id
            """)

            result = db.execute(update_sql, params)
            db.commit()

            updated = result.rowcount > 0
            if updated:
                logger.info(f"Updated knowledge unit {record_id} in {table_name}")
            else:
                logger.warning(f"Knowledge unit {record_id} not found in {table_name}")

            return updated

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update knowledge unit: {e}")
            raise
        finally:
            db.close()

    def merge_knowledge_units(self, book_id: int, keep_id: int, delete_id: int) -> bool:
        """
        Merge two knowledge units.

        Combines two knowledge units by:
        1. Merging text_content from both records
        2. Marking delete_id record as disabled (attr8_value = 'disabled')
        3. Setting merged_into_record_id on deleted record
        4. Tracking original IDs in keep_id record

        Args:
            book_id: Book ID for table lookup
            keep_id: ID of record to keep (will be updated with merged content)
            delete_id: ID of record to merge into keep_id (will be disabled)

        Returns:
            bool: True if merge successful, False if records not found

        Example:
            >>> service = KnowledgeUnitService()
            >>> success = service.merge_knowledge_units(1, keep_id=100, delete_id=101)
            >>> print(f"Merge {'successful' if success else 'failed'}")
        """
        table_name = get_table_name(book_id, 'knowledge_units')
        db = SessionLocal()

        try:
            # Get both records
            get_sql = text(f"""
                SELECT unit_id, text_content, text_length, original_record_ids
                FROM {table_name}
                WHERE unit_id = :unit_id
            """)

            keep_record = db.execute(get_sql, {'unit_id': keep_id}).fetchone()
            delete_record = db.execute(get_sql, {'unit_id': delete_id}).fetchone()

            if not keep_record or not delete_record:
                logger.warning(f"One or both records not found: keep_id={keep_id}, delete_id={delete_id}")
                return False

            # Merge text content
            merged_text = keep_record.text_content + "\n" + delete_record.text_content
            merged_length = len(merged_text)

            # Track original IDs
            original_ids = list(keep_record.original_record_ids or [])
            if str(keep_id) not in original_ids:
                original_ids.append(str(keep_id))
            if str(delete_id) not in original_ids:
                original_ids.append(str(delete_id))

            # Update keep record
            update_keep_sql = text(f"""
                UPDATE {table_name}
                SET
                    text_content = :text_content,
                    text_length = :text_length,
                    original_record_ids = :original_ids,
                    updated_at = NOW()
                WHERE unit_id = :unit_id
            """)

            db.execute(update_keep_sql, {
                'unit_id': keep_id,
                'text_content': merged_text,
                'text_length': merged_length,
                'original_ids': original_ids
            })

            # Mark delete record as disabled
            update_delete_sql = text(f"""
                UPDATE {table_name}
                SET
                    attr8_value = 'disabled',
                    merged_into_record_id = :merged_into,
                    updated_at = NOW()
                WHERE unit_id = :unit_id
            """)

            db.execute(update_delete_sql, {
                'unit_id': delete_id,
                'merged_into': keep_id
            })

            db.commit()
            logger.info(f"Merged knowledge unit {delete_id} into {keep_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to merge knowledge units: {e}")
            raise
        finally:
            db.close()
