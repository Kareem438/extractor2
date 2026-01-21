"""
CHUNK-025: Database Service - Images CRUD

CRUD operations for images table with LZ4 compression and thumbnail generation.
Handles image storage, retrieval, and compression for efficient database storage.
"""

from sqlalchemy import text
from PIL import Image
from src.database.connection import SessionLocal
from src.database.utils import get_table_name
from src.utils.image_compression import compress_image, decompress_image
from src.utils.logging_config import logger


class ImageService:
    """
    Service for CRUD operations on images table.

    Provides methods for inserting and retrieving images with
    automatic LZ4 compression and thumbnail generation.
    """

    def insert_images(self, book_id: int, images: list[dict]) -> int:
        """
        Insert images with LZ4 compression and thumbnail generation.

        Compresses images using LZ4 before storage and generates 200x200
        thumbnails for efficient preview display.

        Args:
            book_id: Book ID for table lookup
            images: List of image dicts with:
                - image_id (required): Unique image identifier (e.g., 'IMG-001-00')
                - page_number (required): Source page number
                - image_data (required): PIL Image object
                - ai_description (optional): AI-generated caption
                - confidence_score (optional): Caption confidence (0-100)
                - image_type (optional): Classified type (diagram/photo/chart/other)
                - original_width (optional): Original image width
                - original_height (optional): Original image height

        Returns:
            int: Number of images inserted

        Example:
            >>> service = ImageService()
            >>> img = Image.new('RGB', (400, 300), color='white')
            >>> images = [
            ...     {'image_id': 'IMG-001-00', 'page_number': 1, 'image_data': img}
            ... ]
            >>> count = service.insert_images(1, images)
        """
        if not images:
            return 0

        table_name = get_table_name(book_id, 'images')
        db = SessionLocal()

        try:
            for img in images:
                # Compress full image with LZ4
                compressed_image = compress_image(img['image_data'])

                # Generate and compress thumbnail (200x200)
                thumbnail = img['image_data'].copy()
                thumbnail.thumbnail((200, 200), Image.Resampling.LANCZOS)
                compressed_thumbnail = compress_image(thumbnail)

                # Insert into database
                sql = text(f"""
                    INSERT INTO {table_name} (
                        image_id, page_number, image_data, thumbnail_data,
                        ai_description, confidence_score, image_type,
                        original_width, original_height
                    )
                    VALUES (
                        :image_id, :page_number, :image_data, :thumbnail_data,
                        :ai_description, :confidence_score, :image_type,
                        :original_width, :original_height
                    )
                """)

                db.execute(sql, {
                    'image_id': img['image_id'],
                    'page_number': img['page_number'],
                    'image_data': compressed_image,
                    'thumbnail_data': compressed_thumbnail,
                    'ai_description': img.get('ai_description'),
                    'confidence_score': img.get('confidence_score'),
                    'image_type': img.get('image_type'),
                    'original_width': img.get('original_width', img['image_data'].width),
                    'original_height': img.get('original_height', img['image_data'].height)
                })

            db.commit()
            logger.info(f"Inserted {len(images)} images into {table_name}")
            return len(images)

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to insert images: {e}")
            raise
        finally:
            db.close()

    def get_image(self, book_id: int, image_id: str, thumbnail: bool = False) -> Image.Image:
        """
        Get and decompress image.

        Retrieves image from database and decompresses from LZ4 format.
        Can optionally retrieve thumbnail instead of full image.

        Args:
            book_id: Book ID for table lookup
            image_id: Unique image identifier (e.g., 'IMG-001-00')
            thumbnail: If True, return thumbnail instead of full image (default: False)

        Returns:
            Image.Image: Decompressed PIL Image object

        Raises:
            ValueError: If image_id not found

        Example:
            >>> service = ImageService()
            >>> image = service.get_image(1, 'IMG-001-00')
            >>> thumbnail = service.get_image(1, 'IMG-001-00', thumbnail=True)
        """
        table_name = get_table_name(book_id, 'images')
        db = SessionLocal()

        try:
            # Select appropriate field based on thumbnail parameter
            field = 'thumbnail_data' if thumbnail else 'image_data'

            sql = text(f"""
                SELECT {field}
                FROM {table_name}
                WHERE image_id = :image_id
            """)

            result = db.execute(sql, {'image_id': image_id})
            row = result.fetchone()

            if not row:
                raise ValueError(f"Image {image_id} not found in book {book_id}")

            # Decompress and return image
            compressed_bytes = row[0]
            image = decompress_image(compressed_bytes)

            logger.debug(f"Retrieved {'thumbnail' if thumbnail else 'image'} {image_id} from {table_name}")
            return image

        finally:
            db.close()

    def get_images_by_page(self, book_id: int, page_number: int) -> list[dict]:
        """
        Get all images for a specific page.

        Retrieves metadata for all images on a page without loading
        full image data (for performance).

        Args:
            book_id: Book ID for table lookup
            page_number: Page number to query

        Returns:
            list[dict]: List of image metadata dicts with:
                - image_id: Image identifier
                - page_number: Source page
                - ai_description: AI caption
                - confidence_score: Caption confidence
                - image_type: Classified type
                - original_width: Image width
                - original_height: Image height
                - created_at: Timestamp

        Example:
            >>> service = ImageService()
            >>> images = service.get_images_by_page(1, page_number=5)
            >>> for img in images:
            ...     print(f"{img['image_id']}: {img['ai_description']}")
        """
        table_name = get_table_name(book_id, 'images')
        db = SessionLocal()

        try:
            sql = text(f"""
                SELECT
                    image_id, page_number, ai_description, confidence_score,
                    image_type, original_width, original_height, created_at
                FROM {table_name}
                WHERE page_number = :page_number
                ORDER BY image_id
            """)

            result = db.execute(sql, {'page_number': page_number})
            images = [dict(row._mapping) for row in result]

            return images

        finally:
            db.close()

    def delete_image(self, book_id: int, image_id: str) -> bool:
        """
        Delete an image.

        Removes image and thumbnail data from database.

        Args:
            book_id: Book ID for table lookup
            image_id: Image identifier to delete

        Returns:
            bool: True if image was deleted, False if not found

        Example:
            >>> service = ImageService()
            >>> success = service.delete_image(1, 'IMG-001-00')
        """
        table_name = get_table_name(book_id, 'images')
        db = SessionLocal()

        try:
            sql = text(f"""
                DELETE FROM {table_name}
                WHERE image_id = :image_id
            """)

            result = db.execute(sql, {'image_id': image_id})
            db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted image {image_id} from {table_name}")
            else:
                logger.warning(f"Image {image_id} not found in {table_name}")

            return deleted

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete image: {e}")
            raise
        finally:
            db.close()
