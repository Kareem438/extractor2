"""
Auto-Slicer Service

Handles the core processing logic for the Auto-slicer feature:
- Loading PDF pages at 600 DPI
- Running Surya OCR on page regions
- Storing results in paragraph_images and knowledge_units tables
- Managing multiple OCR rectangles with attribute mapping

Author: Claude Code
Date: 2026-01-12
"""

import io
from typing import Dict, List, Optional, Any
from PIL import Image
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.utils.logging_config import logger


def get_book_info(book_id: int) -> Optional[Dict]:
    """Get book metadata including table_prefix and file_path."""
    db = SessionLocal()
    try:
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if book:
            return {
                "book_id": book.book_id,
                "book_name": book.book_name,
                "table_prefix": book.table_prefix,
                "file_path": book.file_path,
                "total_pages": book.total_pages
            }
        return None
    finally:
        db.close()


def get_page_image(book_id: int, page_number: int) -> Optional[bytes]:
    """
    Get page image from raw_*_pages table.
    Returns image bytes at 600 DPI (already stored from scan-pages).
    """
    book_info = get_book_info(book_id)
    if not book_info:
        return None

    table_prefix = book_info["table_prefix"]
    db = SessionLocal()

    try:
        result = db.execute(
            text(f"SELECT original_image_data FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
            {"page_num": page_number}
        ).first()

        if result and result[0]:
            return bytes(result[0])
        return None
    except Exception as e:
        logger.error(f"Error getting page image: {e}")
        return None
    finally:
        db.close()


def render_page_from_pdf(book_id: int, page_number: int, dpi: int = 600) -> Optional[bytes]:
    """
    Render a page from PDF at specified DPI.
    Fallback if page not in raw_*_pages table.
    """
    import fitz  # PyMuPDF

    book_info = get_book_info(book_id)
    if not book_info or not book_info["file_path"]:
        return None

    try:
        doc = fitz.open(book_info["file_path"])
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None

        page = doc[page_number - 1]  # 0-indexed
        zoom = dpi / 72  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img_bytes = pix.tobytes("png")
        doc.close()

        return img_bytes

    except Exception as e:
        logger.error(f"Error rendering page from PDF: {e}")
        return None


def crop_image(image_bytes: bytes, x: int, y: int, width: int, height: int) -> Optional[bytes]:
    """Crop an image to the specified rectangle."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        cropped = img.crop((x, y, x + width, y + height))

        output = io.BytesIO()
        cropped.save(output, format='PNG')
        return output.getvalue()

    except Exception as e:
        logger.error(f"Error cropping image: {e}")
        return None


def run_surya_ocr(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run Surya OCR on image bytes.

    Returns:
        dict: {
            'success': bool,
            'text': str,
            'confidence': float,
            'error': str (if failed)
        }
    """
    try:
        from src.services.ocr_sequential import run_surya_on_single_image
        return run_surya_on_single_image(image_bytes)
    except Exception as e:
        logger.error(f"Surya OCR error: {e}")
        return {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'error': str(e)
        }


def get_titles_for_page(page_number: int, config: Dict) -> Dict[str, str]:
    """
    Get applicable titles for a page number based on title configuration.

    Returns:
        dict: {
            'level_1_title': str or None,
            'level_2_title': str or None,
            'level_3_title': str or None
        }
    """
    titles_config = config.get("titles", {})
    result = {
        "level_1_title": None,
        "level_2_title": None,
        "level_3_title": None
    }

    for level in ["level1", "level2", "level3"]:
        level_titles = titles_config.get(level, [])
        for title_config in level_titles:
            start = title_config.get("start_page", 0)
            end = title_config.get("end_page", 0)
            if start <= page_number <= end:
                # Map level1 -> level_1_title, etc.
                key = level.replace("level", "level_") + "_title"
                result[key] = title_config.get("title")
                break  # Use first matching title for this level

    return result


def get_ocr_boundary_for_page(page_number: int, config: Dict) -> Optional[Dict]:
    """
    Get OCR boundary configuration for a page.

    Returns the boundary config if page is within a configured range,
    or None to use full page.
    """
    boundaries = config.get("ocr_boundaries", [])

    for boundary in boundaries:
        start = boundary.get("start_page", 0)
        end = boundary.get("end_page", 0)
        if start <= page_number <= end:
            return boundary

    return None


def create_paragraph_image(
    book_id: int,
    page_number: int,
    image_data: bytes,
    ocr_text: str,
    rectangle_label: str = "Main Text",
    selection_x: int = 0,
    selection_y: int = 0,
    selection_width: int = 0,
    selection_height: int = 0,
    titles: Dict[str, str] = None
) -> Optional[int]:
    """
    Create a paragraph_image record.

    Returns the created record ID.
    """
    book_info = get_book_info(book_id)
    if not book_info:
        logger.error(f"Book info not found for book_id {book_id}")
        return None

    table_prefix = book_info["table_prefix"]
    db = SessionLocal()

    try:
        # Get raw_page_id for this page
        raw_page_result = db.execute(
            text(f"SELECT id FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
            {"page_num": page_number}
        ).first()
        raw_page_id = raw_page_result[0] if raw_page_result else None

        if not raw_page_id:
            logger.error(f"Raw page not found for page {page_number}")
            return None

        # Get image dimensions
        img = Image.open(io.BytesIO(image_data))
        img_width, img_height = img.size
        img_format = img.format or 'PNG'

        # Use image dimensions if selection not provided
        if selection_width == 0:
            selection_width = img_width
        if selection_height == 0:
            selection_height = img_height

        # Get next display_order
        order_result = db.execute(
            text(f"SELECT COALESCE(MAX(display_order), 0) + 1 FROM raw_{table_prefix}_paragraph_images")
        ).first()
        display_order = order_result[0] if order_result else 1

        # Prepare titles
        level_1 = titles.get("level_1_title") if titles else None
        level_2 = titles.get("level_2_title") if titles else None
        level_3 = titles.get("level_3_title") if titles else None

        # Insert into raw_*_paragraph_images
        result = db.execute(
            text(f"""
                INSERT INTO raw_{table_prefix}_paragraph_images
                (raw_page_id, page_number, selection_x, selection_y, selection_width, selection_height,
                 image_data, image_format, image_width, image_height,
                 image_size_bytes, extracted_text, is_enabled, created_by,
                 approval_status, description, display_order,
                 level_1_title, level_2_title, level_3_title)
                VALUES (:raw_page_id, :page_num, :sel_x, :sel_y, :sel_w, :sel_h,
                        :image_data, :img_format, :img_width, :img_height,
                        :img_size, :text, TRUE, 'auto-slicer',
                        'pending', :description, :display_order,
                        :level_1, :level_2, :level_3)
                RETURNING id
            """),
            {
                "raw_page_id": raw_page_id,
                "page_num": page_number,
                "sel_x": selection_x,
                "sel_y": selection_y,
                "sel_w": selection_width,
                "sel_h": selection_height,
                "image_data": image_data,
                "img_format": img_format.lower(),
                "img_width": img_width,
                "img_height": img_height,
                "img_size": len(image_data),
                "text": ocr_text,
                "description": rectangle_label,
                "display_order": display_order,
                "level_1": level_1,
                "level_2": level_2,
                "level_3": level_3
            }
        )
        db.commit()

        row = result.first()
        created_id = row[0] if row else None
        logger.info(f"Created paragraph_image id={created_id} for page {page_number}")
        return created_id

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating paragraph_image for page {page_number}: {e}", exc_info=True)
        return None
    finally:
        db.close()


def create_knowledge_unit(
    book_id: int,
    page_number: int,
    text_content: str,
    titles: Dict[str, str],
    additional_attrs: Dict[str, str] = None
) -> Optional[int]:
    """
    Create a knowledge_unit record.

    Args:
        book_id: Book ID
        page_number: Page number
        text_content: OCR text for text_content column
        titles: Dict with level_1_title, level_2_title, level_3_title
                (mapped to chapter, topic, sub_topic columns)
        additional_attrs: Dict mapping attr column names to OCR text values

    Returns the created record ID (unit_id).
    """
    book_info = get_book_info(book_id)
    if not book_info:
        return None

    table_prefix = book_info["table_prefix"]
    db = SessionLocal()

    try:
        # Build column names and values
        # Map level titles to actual table columns: chapter, topic, sub_topic
        columns = [
            "page_number", "text_content",
            "chapter", "topic", "sub_topic",
            "attr29_value", "attr30_value"
        ]
        values = {
            "page_num": page_number,
            "text_content": text_content,
            "chapter": titles.get("level_1_title"),
            "topic": titles.get("level_2_title"),
            "sub_topic": titles.get("level_3_title"),
            "attr29_value": "auto-slicer",  # Source marker
            "attr30_value": str(page_number)  # Page number as string
        }

        # Add additional attributes
        if additional_attrs:
            for attr_col, attr_value in additional_attrs.items():
                if attr_col.startswith("attr") and attr_col.endswith("_value"):
                    columns.append(attr_col)
                    values[attr_col] = attr_value

        # Build SQL with correct placeholders
        placeholders = []
        for col in columns:
            if col == "page_number":
                placeholders.append(":page_num")
            else:
                placeholders.append(f":{col}")

        col_list = ", ".join(columns)

        sql = f"""
            INSERT INTO {table_prefix}_knowledge_units
            ({col_list})
            VALUES ({', '.join(placeholders)})
            RETURNING unit_id
        """

        result = db.execute(text(sql), values)
        db.commit()

        row = result.first()
        return row[0] if row else None

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating knowledge_unit: {e}", exc_info=True)
        return None
    finally:
        db.close()


async def process_page(book_id: int, page_number: int, config: Dict) -> Dict[str, Any]:
    """
    Process a single page with Auto-slicer.

    1. Get page image (from DB or render from PDF)
    2. Get OCR boundary configuration
    3. For each rectangle:
       - Crop image to rectangle
       - Run Surya OCR
       - Store result in appropriate column
    4. Create paragraph_image record
    5. Create knowledge_unit record

    Returns:
        dict: {
            'success': bool,
            'page_number': int,
            'text_length': int,
            'error': str (if failed)
        }
    """
    logger.info(f"Processing page {page_number} for book {book_id}")

    try:
        # Get page image
        image_bytes = get_page_image(book_id, page_number)
        if not image_bytes:
            # Try rendering from PDF
            image_bytes = render_page_from_pdf(book_id, page_number, dpi=600)

        if not image_bytes:
            return {
                'success': False,
                'page_number': page_number,
                'error': 'Could not get page image'
            }

        # Get titles for this page
        titles = get_titles_for_page(page_number, config)

        # Get OCR boundary
        boundary = get_ocr_boundary_for_page(page_number, config)

        # Determine rectangles to process
        if boundary and boundary.get("rectangles"):
            rectangles = boundary["rectangles"]
        else:
            # No boundary - use full page as single rectangle
            img = Image.open(io.BytesIO(image_bytes))
            rectangles = [{
                "label": "Full Page",
                "x": 0,
                "y": 0,
                "width": img.size[0],
                "height": img.size[1],
                "target": "text_content"
            }]

        # Process each rectangle
        main_text = ""
        additional_attrs = {}
        main_image_bytes = None
        main_rect = None  # Track main rectangle for coordinates

        for rect in rectangles:
            # Crop image
            cropped = crop_image(
                image_bytes,
                rect.get("x", 0),
                rect.get("y", 0),
                rect.get("width", 0),
                rect.get("height", 0)
            )

            if not cropped:
                logger.warning(f"Failed to crop rectangle '{rect.get('label')}' on page {page_number}")
                continue

            # Run OCR
            ocr_result = run_surya_ocr(cropped)

            if not ocr_result.get("success"):
                logger.warning(f"OCR failed for rectangle '{rect.get('label')}' on page {page_number}: {ocr_result.get('error')}")
                continue

            ocr_text = ocr_result.get("text", "")
            target = rect.get("target", "text_content")

            if target == "text_content":
                main_text = ocr_text
                main_image_bytes = cropped
                main_rect = rect  # Store the main rectangle
            else:
                # Additional attribute (attr31-attr80)
                attr_col = f"{target}_value"
                additional_attrs[attr_col] = ocr_text

        # Create paragraph_image record
        if main_image_bytes:
            para_id = create_paragraph_image(
                book_id=book_id,
                page_number=page_number,
                image_data=main_image_bytes,
                ocr_text=main_text,
                rectangle_label=main_rect.get("label", "Main Text") if main_rect else "Main Text",
                selection_x=main_rect.get("x", 0) if main_rect else 0,
                selection_y=main_rect.get("y", 0) if main_rect else 0,
                selection_width=main_rect.get("width", 0) if main_rect else 0,
                selection_height=main_rect.get("height", 0) if main_rect else 0,
                titles=titles
            )
            logger.info(f"Created paragraph_image {para_id} for page {page_number}")

        # Create knowledge_unit record
        ku_id = create_knowledge_unit(
            book_id=book_id,
            page_number=page_number,
            text_content=main_text,
            titles=titles,
            additional_attrs=additional_attrs
        )
        logger.info(f"Created knowledge_unit {ku_id} for page {page_number}")

        return {
            'success': True,
            'page_number': page_number,
            'text_length': len(main_text),
            'paragraph_image_id': para_id if main_image_bytes else None,
            'knowledge_unit_id': ku_id
        }

    except Exception as e:
        logger.error(f"Error processing page {page_number}: {e}", exc_info=True)
        return {
            'success': False,
            'page_number': page_number,
            'error': str(e)
        }


def get_page_thumbnail(book_id: int, page_number: int, max_width: int = 800) -> Optional[bytes]:
    """
    Get a thumbnail of a page for preview.

    Args:
        book_id: Book ID
        page_number: Page number
        max_width: Maximum width of thumbnail

    Returns:
        PNG image bytes or None
    """
    try:
        # Get full page image
        image_bytes = get_page_image(book_id, page_number)
        if not image_bytes:
            image_bytes = render_page_from_pdf(book_id, page_number, dpi=150)

        if not image_bytes:
            return None

        # Resize for thumbnail
        img = Image.open(io.BytesIO(image_bytes))

        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

    except Exception as e:
        logger.error(f"Error creating thumbnail: {e}")
        return None
