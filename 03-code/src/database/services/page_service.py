"""
CHUNK-026: Database Service - Pages CRUD

CRUD operations for pages table with compressed page images and rectangle metadata.
Handles storage and retrieval of original and marked page images with JSON rectangle data.
"""

import json
from sqlalchemy import text
from PIL import Image
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.image_compression import compress_image, decompress_image
from src.utils.logging_config import logger


class PageService:
    """
    Service for CRUD operations on pages table.

    Provides methods for inserting and retrieving page data including
    original images, marked images, and rectangle metadata.
    """

    def insert_page(self, book_id: int, page_data: dict) -> bool:
        """
        Insert page with original and marked images.

        Stores page with both original and marked images compressed with LZ4,
        plus rectangle metadata as JSON.

        Args:
            book_id: Book ID for table lookup
            page_data: Page data dict with:
                - page_number (required): Page number (1-indexed)
                - page_image (required): Original PIL Image
                - marked_image (required): Marked PIL Image with rectangles
                - rectangle_data (required): Dict with 'green_rectangles' and 'orange_rectangles'

        Returns:
            bool: True if inserted successfully

        Example:
            >>> service = PageService()
            >>> page_data = {
            ...     'page_number': 1,
            ...     'page_image': Image.new('RGB', (800, 1000)),
            ...     'marked_image': Image.new('RGB', (800, 1000)),
            ...     'rectangle_data': {
            ...         'green_rectangles': [{'x': 100, 'y': 200, 'width': 300, 'height': 50}],
            ...         'orange_rectangles': []
            ...     }
            ... }
            >>> service.insert_page(1, page_data)
        """
        table_name = get_table_name(book_id, 'pages')
        db = SessionLocal()

        try:
            # Compress both images
            original_compressed = compress_image(page_data['page_image'])
            marked_compressed = compress_image(page_data['marked_image'])

            # Convert rectangle data to JSON
            rect_data = page_data['rectangle_data']
            green_rects_json = json.dumps(rect_data.get('green_rectangles', []))
            orange_rects_json = json.dumps(rect_data.get('orange_rectangles', []))

            # Insert page
            sql = text(f"""
                INSERT INTO {table_name} (
                    page_number, original_image_data, marked_image_data,
                    green_rectangles, orange_rectangles, marker_generated
                )
                VALUES (
                    :page_number, :original_image_data, :marked_image_data,
                    :green_rectangles::jsonb, :orange_rectangles::jsonb, TRUE
                )
                ON CONFLICT (page_number) DO UPDATE SET
                    original_image_data = EXCLUDED.original_image_data,
                    marked_image_data = EXCLUDED.marked_image_data,
                    green_rectangles = EXCLUDED.green_rectangles,
                    orange_rectangles = EXCLUDED.orange_rectangles,
                    marker_generated = TRUE,
                    marker_generated_at = NOW()
            """)

            db.execute(sql, {
                'page_number': page_data['page_number'],
                'original_image_data': original_compressed,
                'marked_image_data': marked_compressed,
                'green_rectangles': green_rects_json,
                'orange_rectangles': orange_rects_json
            })

            db.commit()
            logger.info(f"Inserted page {page_data['page_number']} into {table_name}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to insert page: {e}")
            raise
        finally:
            db.close()

    def get_page(self, book_id: int, page_number: int, include_images: bool = True) -> dict:
        """
        Get page data with optional image loading.

        Retrieves page data including rectangle metadata and optionally
        decompressed images.

        Args:
            book_id: Book ID for table lookup
            page_number: Page number to retrieve
            include_images: If True, decompress and include images (default: True)

        Returns:
            dict: Page data with:
                - page_number: Page number
                - green_rectangles: List of green rectangle dicts
                - orange_rectangles: List of orange rectangle dicts
                - marker_generated: Boolean flag
                - marker_generated_at: Timestamp
                - original_image: PIL Image (if include_images=True)
                - marked_image: PIL Image (if include_images=True)

        Raises:
            ValueError: If page not found

        Example:
            >>> service = PageService()
            >>> page = service.get_page(1, page_number=5)
            >>> print(f"Found {len(page['green_rectangles'])} text rectangles")
        """
        table_name = get_table_name(book_id, 'pages')
        db = SessionLocal()

        try:
            if include_images:
                sql = text(f"""
                    SELECT
                        page_number, original_image_data, marked_image_data,
                        green_rectangles, orange_rectangles,
                        marker_generated, marker_generated_at
                    FROM {table_name}
                    WHERE page_number = :page_number
                """)
            else:
                sql = text(f"""
                    SELECT
                        page_number, green_rectangles, orange_rectangles,
                        marker_generated, marker_generated_at
                    FROM {table_name}
                    WHERE page_number = :page_number
                """)

            result = db.execute(sql, {'page_number': page_number})
            row = result.fetchone()

            if not row:
                raise ValueError(f"Page {page_number} not found in book {book_id}")

            # Build result dict
            page_data = {
                'page_number': row.page_number,
                'green_rectangles': json.loads(row.green_rectangles) if row.green_rectangles else [],
                'orange_rectangles': json.loads(row.orange_rectangles) if row.orange_rectangles else [],
                'marker_generated': row.marker_generated,
                'marker_generated_at': row.marker_generated_at
            }

            # Decompress images if requested
            if include_images:
                page_data['original_image'] = decompress_image(row.original_image_data)
                page_data['marked_image'] = decompress_image(row.marked_image_data)

            return page_data

        finally:
            db.close()

    def get_page_count(self, book_id: int) -> int:
        """
        Get total number of pages stored.

        Args:
            book_id: Book ID for table lookup

        Returns:
            int: Number of pages in database

        Example:
            >>> service = PageService()
            >>> count = service.get_page_count(1)
            >>> print(f"Stored {count} pages")
        """
        table_name = get_table_name(book_id, 'pages')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT COUNT(*) FROM {table_name}
            """)

            result = db.execute(sql)
            return result.scalar()

        finally:
            db.close()

    def delete_page(self, book_id: int, page_number: int) -> bool:
        """
        Delete a page.

        Removes page data including images and rectangle metadata.

        Args:
            book_id: Book ID for table lookup
            page_number: Page number to delete

        Returns:
            bool: True if page was deleted, False if not found

        Example:
            >>> service = PageService()
            >>> success = service.delete_page(1, page_number=5)
        """
        table_name = get_table_name(book_id, 'pages')
        db = SessionLocal()

        try:
            sql = text(f"""
                DELETE FROM {table_name}
                WHERE page_number = :page_number
            """)

            result = db.execute(sql, {'page_number': page_number})
            db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted page {page_number} from {table_name}")
            else:
                logger.warning(f"Page {page_number} not found in {table_name}")

            return deleted

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete page: {e}")
            raise
        finally:
            db.close()
