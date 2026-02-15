"""
Few-Shot Service

Manages few-shot examples for V2 cloud extraction:
- Annotated image generation (colored outlines + labels)
- Storage and retrieval of few-shot examples
- Send/cache management for LLM context
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from src.database.connection import engine
from src.utils.logging_config import logger


class FewShotService:
    """Service for managing few-shot annotated examples."""

    def get_examples(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all few-shot examples for a book."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return []

        table_name = f"v2_{table_prefix}_few_shot_examples"
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT id, page_number, annotated_image_path, annotation_data,
                       cache_name, sent_to_llm, sent_at, llm_provider, model_name,
                       created_at
                FROM {table_name}
                ORDER BY page_number
            """))
            rows = result.fetchall()

        return [{
            "id": r[0], "page_number": r[1],
            "annotated_image_path": r[2],
            "annotation_data": r[3],
            "cache_name": r[4], "sent_to_llm": r[5],
            "sent_at": str(r[6]) if r[6] else None,
            "llm_provider": r[7], "model_name": r[8],
            "created_at": str(r[9]) if r[9] else None
        } for r in rows]

    def add_example(self, book_id: int, page_number: int,
                    annotation_data: Optional[Dict] = None,
                    cache_name: Optional[str] = None) -> Dict[str, Any]:
        """Add a new few-shot example page."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            raise ValueError(f"Book {book_id} not found")

        table_name = f"v2_{table_prefix}_few_shot_examples"
        annotation_json = json.dumps(annotation_data) if annotation_data else None

        with engine.connect() as conn:
            result = conn.execute(text(f"""
                INSERT INTO {table_name} (page_number, annotation_data, cache_name)
                VALUES (:page, :annotations, :cache_name)
                RETURNING id
            """), {
                "page": page_number,
                "annotations": annotation_json,
                "cache_name": cache_name
            })
            conn.commit()
            example_id = result.scalar()

        logger.info(f"Added few-shot example: book={book_id}, page={page_number}")
        return {"id": example_id, "page_number": page_number}

    def remove_example(self, book_id: int, example_id: int) -> bool:
        """Remove a few-shot example."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return False

        table_name = f"v2_{table_prefix}_few_shot_examples"
        with engine.connect() as conn:
            result = conn.execute(text(f"DELETE FROM {table_name} WHERE id = :id"), {"id": example_id})
            conn.commit()
            return result.rowcount > 0

    def update_annotations(self, book_id: int, example_id: int,
                           annotation_data: Dict) -> bool:
        """Update annotations for a few-shot example."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return False

        table_name = f"v2_{table_prefix}_few_shot_examples"
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                UPDATE {table_name}
                SET annotation_data = :annotations, updated_at = NOW()
                WHERE id = :id
            """), {
                "annotations": json.dumps(annotation_data),
                "id": example_id
            })
            conn.commit()
            return result.rowcount > 0

    def mark_as_sent(self, book_id: int, example_id: int,
                     provider: str, model: str) -> bool:
        """Mark a few-shot example as sent to LLM."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return False

        table_name = f"v2_{table_prefix}_few_shot_examples"
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                UPDATE {table_name}
                SET sent_to_llm = true, sent_at = NOW(),
                    llm_provider = :provider, model_name = :model
                WHERE id = :id
            """), {"provider": provider, "model": model, "id": example_id})
            conn.commit()
            return result.rowcount > 0

    def get_sent_examples(self, book_id: int) -> List[Dict[str, Any]]:
        """Get only examples that have been sent to LLM."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return []

        table_name = f"v2_{table_prefix}_few_shot_examples"
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT id, page_number, annotated_image_path, annotation_data,
                       cache_name, llm_provider, model_name
                FROM {table_name}
                WHERE sent_to_llm = true
                ORDER BY page_number
            """))
            rows = result.fetchall()

        return [{
            "id": r[0], "page_number": r[1],
            "annotated_image_path": r[2],
            "annotation_data": r[3],
            "cache_name": r[4],
            "llm_provider": r[5], "model_name": r[6]
        } for r in rows]

    def get_page_image_base64(self, book_id: int, page_number: int) -> Optional[str]:
        """Get base64-encoded page image for sending to LLM."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return None

        # Get image path from raw_pages table
        raw_pages_table = f"{table_prefix}_raw_pages"
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT image_path FROM {raw_pages_table}
                WHERE page_number = :page
            """), {"page": page_number})
            row = result.fetchone()

        if not row or not row[0]:
            return None

        image_path = row[0]
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return None

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def _get_table_prefix(self, book_id: int) -> Optional[str]:
        """Get table prefix for a book."""
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_prefix FROM books_metadata WHERE book_id = :id"
            ), {"id": book_id})
            row = result.fetchone()
        return row[0] if row else None
