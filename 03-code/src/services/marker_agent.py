"""
Marker Agent Service

Generates visual overlays on page images showing verification status:
- Green rectangles: Verified knowledge units
- Orange rectangles: Unverified knowledge units

The marked images help users visualize what's been verified and what needs review.
"""

from typing import Dict, List, Tuple
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.utils.logging_config import logger


class MarkerAgent:
    """
    Generates marked page images with colored rectangles indicating verification status.
    """

    def __init__(self):
        """Initialize marker agent with default colors."""
        self.verified_color = (0, 255, 0, 128)  # Green with alpha
        self.unverified_color = (255, 165, 0, 128)  # Orange with alpha
        self.line_width = 3

    async def generate_marked_image(
        self,
        book_id: int,
        page_number: int,
        table_prefix: str
    ) -> bytes:
        """
        Generate a marked image for a specific page.

        Args:
            book_id: Book ID
            page_number: Page number to mark
            table_prefix: Table prefix for this book

        Returns:
            Marked image as bytes (JPEG format)
        """
        db = SessionLocal()
        try:
            # Step 1: Get page image
            image_data = await self._get_page_image(db, table_prefix, page_number)
            if not image_data:
                logger.warning(f"No image found for page {page_number}")
                return None

            # Step 2: Get knowledge units for this page
            units = await self._get_knowledge_units_for_page(db, table_prefix, page_number)

            # Step 3: Generate marked image
            marked_image_bytes = await self._draw_rectangles(
                image_data,
                units,
                page_number
            )

            return marked_image_bytes

        except Exception as e:
            logger.error(f"Failed to generate marked image for page {page_number}: {e}")
            raise
        finally:
            db.close()

    async def _get_page_image(
        self,
        db,
        table_prefix: str,
        page_number: int
    ) -> bytes:
        """
        Retrieve page image from images table.

        Args:
            db: Database session
            table_prefix: Table prefix
            page_number: Page number

        Returns:
            Image data as bytes
        """
        result = db.execute(
            text(f"""
            SELECT image_data
            FROM {table_prefix}_images
            WHERE page_number = :page_num
            LIMIT 1
            """),
            {"page_num": page_number}
        ).first()

        if result and result[0]:
            return bytes(result[0])
        return None

    async def _get_knowledge_units_for_page(
        self,
        db,
        table_prefix: str,
        page_number: int
    ) -> List[Dict]:
        """
        Get all knowledge units for a specific page with their verification status.

        Args:
            db: Database session
            table_prefix: Table prefix
            page_number: Page number

        Returns:
            List of knowledge unit dictionaries
        """
        results = db.execute(
            text(f"""
            SELECT unit_id, verified, position_x, position_y,
                   position_width, position_height
            FROM {table_prefix}_knowledge_units
            WHERE page_number = :page_num
            ORDER BY position_y, position_x
            """),
            {"page_num": page_number}
        ).fetchall()

        units = []
        for row in results:
            units.append({
                'unit_id': row[0],
                'verified': row[1],
                'position_x': row[2],
                'position_y': row[3],
                'position_width': row[4],
                'position_height': row[5]
            })

        return units

    async def _draw_rectangles(
        self,
        image_data: bytes,
        units: List[Dict],
        page_number: int
    ) -> bytes:
        """
        Draw colored rectangles on image based on verification status.

        Args:
            image_data: Original image bytes
            units: List of knowledge units with positions
            page_number: Page number (for logging)

        Returns:
            Marked image as bytes
        """
        try:
            # Load image
            image = Image.open(BytesIO(image_data))

            # Convert to RGBA for transparency support
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            # Create overlay layer
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # Draw rectangles for each unit
            for unit in units:
                # Skip units without position data
                if not all([
                    unit.get('position_x') is not None,
                    unit.get('position_y') is not None,
                    unit.get('position_width') is not None,
                    unit.get('position_height') is not None
                ]):
                    continue

                # Calculate rectangle coordinates
                x1 = unit['position_x']
                y1 = unit['position_y']
                x2 = x1 + unit['position_width']
                y2 = y1 + unit['position_height']

                # Choose color based on verification status
                color = self.verified_color if unit['verified'] else self.unverified_color

                # Draw filled rectangle with transparency
                draw.rectangle(
                    [(x1, y1), (x2, y2)],
                    fill=color,
                    outline=color[:3] + (255,),  # Solid outline
                    width=self.line_width
                )

            # Composite overlay onto original image
            marked_image = Image.alpha_composite(image, overlay)

            # Convert back to RGB for JPEG
            marked_image = marked_image.convert('RGB')

            # Save to bytes
            output = BytesIO()
            marked_image.save(output, format='JPEG', quality=90)
            marked_image_bytes = output.getvalue()

            logger.info(f"Generated marked image for page {page_number} with {len(units)} rectangles")
            return marked_image_bytes

        except Exception as e:
            logger.error(f"Failed to draw rectangles on page {page_number}: {e}")
            raise

    async def generate_marked_images_for_book(
        self,
        book_id: int,
        table_prefix: str,
        total_pages: int
    ) -> Dict[str, any]:
        """
        Generate marked images for all pages in a book.

        Args:
            book_id: Book ID
            table_prefix: Table prefix
            total_pages: Total number of pages

        Returns:
            Summary dictionary with success/failure counts
        """
        db = SessionLocal()
        try:
            success_count = 0
            failure_count = 0
            skipped_count = 0

            for page_num in range(1, total_pages + 1):
                try:
                    # Generate marked image
                    marked_image_bytes = await self.generate_marked_image(
                        book_id,
                        page_num,
                        table_prefix
                    )

                    if not marked_image_bytes:
                        skipped_count += 1
                        continue

                    # Store marked image in pages table
                    db.execute(
                        text(f"""
                        UPDATE {table_prefix}_pages
                        SET marked_image = :marked_img
                        WHERE page_number = :page_num
                        """),
                        {"marked_img": marked_image_bytes, "page_num": page_num}
                    )

                    success_count += 1

                    # Commit every 10 pages
                    if page_num % 10 == 0:
                        db.commit()
                        logger.info(f"Processed {page_num}/{total_pages} pages")

                except Exception as e:
                    logger.error(f"Failed to process page {page_num}: {e}")
                    failure_count += 1
                    continue

            # Final commit
            db.commit()

            logger.info(
                f"Marked image generation complete: "
                f"{success_count} success, {failure_count} failed, {skipped_count} skipped"
            )

            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'skipped_count': skipped_count,
                'total_pages': total_pages
            }

        except Exception as e:
            logger.error(f"Failed to generate marked images for book {book_id}: {e}")
            db.rollback()
            raise
        finally:
            db.close()


# Singleton instance
_marker_agent_instance = None


def get_marker_agent() -> MarkerAgent:
    """Get singleton MarkerAgent instance."""
    global _marker_agent_instance
    if _marker_agent_instance is None:
        _marker_agent_instance = MarkerAgent()
    return _marker_agent_instance
