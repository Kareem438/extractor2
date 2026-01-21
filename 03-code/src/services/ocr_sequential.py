"""
Sequential OCR Service

Implements user-controlled sequential OCR processing with:
- PaddleOCR (GPU)
- Surya OCR (GPU)
- Tesseract (CPU)
- Evaluation/Split/Mark pipeline

Aligned with sequential-ocr-svg-processing.md architecture.
"""

from typing import Dict, Any
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.utils.logging_config import logger
from src.services.gpu_manager import gpu_manager
from src.services.image_analyzer import get_image_analyzer
from src.services.svg_generator import generate_svg_from_json


def scan_and_save_pages(book_id: int, max_pages: int = None, skip_existing: bool = True):
    """
    Scan PDF pages and save as 600 DPI images to raw_pages table.

    This function ONLY renders and saves pages - it does NOT run OCR.
    This should be run FIRST before any OCR engine.

    Process:
    1. Get PDF file path from book metadata
    2. Get list of pages that need to be scanned (skip existing if requested)
    3. For each unscanned page:
       - Render page to 600 DPI PNG image
       - Save image to raw_{table_prefix}_pages table
    4. Update pages_scanned counter in processing_state

    Args:
        book_id: Book ID to process
        max_pages: Maximum pages to process (for testing). None = all pages
        skip_existing: If True (default), skip pages already in database to protect data integrity
    """
    import fitz  # PyMuPDF
    from PIL import Image
    import io

    logger.info(f"=" * 80)
    logger.info(f"Starting page scanning for book_id={book_id}")
    logger.info(f"Skip existing pages: {skip_existing}")
    logger.info(f"=" * 80)

    db = SessionLocal()

    try:
        # Get book metadata including file path
        result = db.execute(
            text("SELECT table_prefix, total_pages, file_path FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if not result:
            raise ValueError(f"Book {book_id} not found")

        table_prefix, total_pages, pdf_path = result

        if not pdf_path:
            raise ValueError(f"No file path found for book {book_id}")

        logger.info(f"PDF path: {pdf_path}")
        logger.info(f"Target table: raw_{table_prefix}_pages")
        logger.info(f"Total pages in book: {total_pages}")

        # Determine which pages to scan
        if skip_existing:
            # Get list of pages already scanned
            existing_pages_result = db.execute(
                text(f"SELECT page_number FROM raw_{table_prefix}_pages ORDER BY page_number")
            ).fetchall()
            existing_pages = set(row[0] for row in existing_pages_result)

            # Calculate pages that need to be scanned
            all_pages = set(range(1, total_pages + 1))
            pages_to_scan = sorted(all_pages - existing_pages)

            logger.info(f"Pages already scanned: {len(existing_pages)}")
            logger.info(f"Pages to scan: {len(pages_to_scan)}")

            if not pages_to_scan:
                logger.info("✅ All pages are already scanned. Nothing to do.")
                return

            # Apply max_pages limit
            if max_pages:
                pages_to_scan = pages_to_scan[:max_pages]
                logger.info(f"Limited to {max_pages} pages")
        else:
            # Scan pages sequentially from 1 to max_pages (or total_pages)
            pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
            pages_to_scan = list(range(1, pages_to_process + 1))
            logger.info(f"Scanning {len(pages_to_scan)} pages (may overwrite existing)")

        # Open PDF
        doc = fitz.open(pdf_path)

        # Process each page
        scanned_count = 0
        for page_num in pages_to_scan:
            page_idx = page_num - 1  # Convert to 0-based index

            logger.info(f"Scanning page {page_num} ({scanned_count + 1}/{len(pages_to_scan)})...")

            # Load page
            page = doc[page_idx]

            # Render to 600 DPI image
            mat = fitz.Matrix(600/72, 600/72)  # 600 DPI scaling
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Convert to PNG bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            img_data = img_bytes.getvalue()

            logger.info(f"  Image size: {pix.width}x{pix.height}, {len(img_data)} bytes")

            if skip_existing:
                # INSERT only - don't overwrite existing (should not happen since we filtered)
                db.execute(
                    text(f"""
                    INSERT INTO raw_{table_prefix}_pages
                        (page_number, original_image_data, original_format,
                         original_width, original_height, original_size_bytes)
                    VALUES (:page_num, :img_data, 'PNG', :width, :height, :size)
                    ON CONFLICT (page_number) DO NOTHING
                    """),
                    {
                        "page_num": page_num,
                        "img_data": img_data,
                        "width": pix.width,
                        "height": pix.height,
                        "size": len(img_data)
                    }
                )
            else:
                # INSERT or UPDATE (original behavior)
                db.execute(
                    text(f"""
                    INSERT INTO raw_{table_prefix}_pages
                        (page_number, original_image_data, original_format,
                         original_width, original_height, original_size_bytes)
                    VALUES (:page_num, :img_data, 'PNG', :width, :height, :size)
                    ON CONFLICT (page_number) DO UPDATE SET
                        original_image_data = EXCLUDED.original_image_data,
                        original_width = EXCLUDED.original_width,
                        original_height = EXCLUDED.original_height,
                        original_size_bytes = EXCLUDED.original_size_bytes,
                        updated_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "page_num": page_num,
                        "img_data": img_data,
                        "width": pix.width,
                        "height": pix.height,
                        "size": len(img_data)
                    }
                )
            db.commit()
            scanned_count += 1

            logger.info(f"  ✅ Page {page_num} saved to database")

            # Update processing state with highest page number scanned
            db.execute(
                text(f"""
                UPDATE {table_prefix}_processing_state
                SET pages_scanned = GREATEST(pages_scanned, :page_num),
                    current_page = :page_num,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
                """),
                {"page_num": page_num}
            )
            db.commit()

        doc.close()

        logger.info(f"=" * 80)
        logger.info(f"✅ Page scanning complete! Scanned {scanned_count} pages")
        logger.info(f"=" * 80)

    except Exception as e:
        logger.error(f"Error scanning pages: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


async def run_easyocr_sequential(book_id: int, max_pages: int = None):
    """
    Run EasyOCR on pre-scanned pages.

    NEW FLOW: Uses pre-scanned images from raw_pages table instead of rendering PDF.

    Process:
    1. Get book metadata
    2. For each page:
       - LOAD image from raw_{table_prefix}_pages
       - Run EasyOCR on the loaded image
       - Save results to raw_{table_prefix}_knowledge_units
       - If FIRST OCR run: Extract embedded images from PDF
    3. Mark easyocr_complete = true

    Args:
        book_id: Book ID to process
        max_pages: Maximum pages to process (for testing). None = all pages
    """
    import numpy as np
    from PIL import Image
    import easyocr
    import io

    logger.info(f"Starting EasyOCR processing for book_id={book_id}")

    db = SessionLocal()
    reader = None
    pdf_doc = None

    try:
        # Get book metadata including file path
        result = db.execute(
            text("SELECT table_prefix, total_pages, file_path FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if not result:
            raise ValueError(f"Book {book_id} not found")

        table_prefix, total_pages, pdf_path = result

        # Limit pages for testing if specified
        pages_to_process = min(max_pages, total_pages) if max_pages else total_pages

        # Check if this is the first OCR run (images not processed yet)
        state = db.execute(
            text(f"SELECT images_processed FROM {table_prefix}_processing_state WHERE id = 1")
        ).first()
        is_first_ocr = not state[0] if state else True

        logger.info(f"Processing {pages_to_process} of {total_pages} pages with EasyOCR (first run: {is_first_ocr})")
        logger.info(f"Loading images from raw_{table_prefix}_pages table")

        # If first OCR run, open PDF for embedded image extraction
        if is_first_ocr:
            import fitz
            if not pdf_path:
                raise ValueError(f"No file path found for book {book_id}")
            logger.info(f"Opening PDF for image extraction: {pdf_path}")
            pdf_doc = fitz.open(pdf_path)

        # Initialize EasyOCR (supports English and Arabic)
        logger.info("Loading EasyOCR...")
        reader = easyocr.Reader(['en', 'ar'], gpu=False)  # CPU mode for stability
        logger.info("EasyOCR loaded successfully")

        for page_num in range(1, pages_to_process + 1):
            logger.info(f"Processing page {page_num}/{pages_to_process} with EasyOCR")

            # Load image from raw_pages table
            page_result = db.execute(
                text(f"""
                SELECT original_image_data, original_width, original_height
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_num
                """),
                {"page_num": page_num}
            ).first()

            if not page_result:
                logger.error(f"Page {page_num} not found in raw_{table_prefix}_pages table! Run 'Scan Pages' first.")
                raise ValueError(f"Page {page_num} not scanned yet. Please run 'Scan Pages' first.")

            # Convert binary image data to PIL Image
            img_data = page_result[0]
            img = Image.open(io.BytesIO(img_data))
            logger.info(f"  Loaded image from database: {img.size[0]}x{img.size[1]} pixels")

            # Convert PIL Image to numpy array for EasyOCR
            img_array = np.array(img)

            # Run EasyOCR
            try:
                # EasyOCR returns list of ([bbox], text, confidence)
                results = reader.readtext(img_array)

                # Extract text and confidence from results
                if results:
                    texts = []
                    confidences = []

                    for bbox, line_text, conf in results:
                        texts.append(line_text)
                        confidences.append(conf)

                    # Combine all text with newlines
                    page_text = '\n'.join(texts)

                    # Calculate average confidence (EasyOCR returns 0-1, convert to 0-100)
                    avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 0.0
                    confidence_str = f"{avg_confidence:.2f}"

                    logger.info(f"Page {page_num}: Extracted {len(texts)} text lines, avg confidence: {confidence_str}%")
                else:
                    page_text = ""
                    confidence_str = "0.0"
                    logger.warning(f"Page {page_num}: No text detected by EasyOCR")

            except Exception as ocr_error:
                logger.error(f"EasyOCR failed on page {page_num}: {ocr_error}")
                page_text = ""
                confidence_str = "0.0"

            # Store in knowledge_units (attr2_value, attr5_value)
            db.execute(
                text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (page_number, text_content, attr2_value, attr5_value)
                VALUES (:page_num, '', :ocr_text, :confidence)
                """),
                {"page_num": page_num, "ocr_text": page_text, "confidence": confidence_str}
            )

            # If first OCR run: Extract embedded images from PDF
            if is_first_ocr and pdf_doc:
                pdf_page = pdf_doc[page_num - 1]  # Get page object from PDF
                image_list = pdf_page.get_images()
                if image_list:
                    logger.info(f"Page {page_num}: Found {len(image_list)} embedded images")
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            base_image = pdf_doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]

                            # Store image in images table
                            db.execute(
                                text(f"""
                                INSERT INTO {table_prefix}_images
                                (image_identifier, page_number, image_data, image_type, analyzed_during_ocr)
                                VALUES (:id, :page, :data, :type, 'easyocr')
                                """),
                                {
                                    "id": f"IMG-{book_id}-P{page_num}-{img_index}",
                                    "page": page_num,
                                    "data": image_bytes,
                                    "type": image_ext.upper()
                                }
                            )
                            logger.info(f"Extracted embedded image {img_index} from page {page_num}")
                        except Exception as img_error:
                            logger.warning(f"Failed to extract image {img_index} from page {page_num}: {img_error}")

            # Commit every 5 pages to ensure data is saved
            if page_num % 5 == 0 or page_num == pages_to_process:
                db.execute(
                    text(f"UPDATE {table_prefix}_processing_state SET current_page = :page WHERE id = 1"),
                    {"page": page_num}
                )
                db.commit()
                logger.info(f"Progress saved: {page_num}/{pages_to_process} pages")

        # Close PDF if it was opened
        if pdf_doc:
            pdf_doc.close()

        # Mark EasyOCR complete (only if processing all pages)
        completion_status = (pages_to_process == total_pages)
        db.execute(
            text(f"""
            UPDATE {table_prefix}_processing_state
            SET easyocr_complete = :complete, images_processed = :first_ocr,
                current_agent = 'easyocr', current_page = :page
            WHERE id = 1
            """),
            {"complete": completion_status, "first_ocr": is_first_ocr, "page": pages_to_process}
        )
        db.commit()

        logger.info(f"EasyOCR processing complete for book_id={book_id}: {pages_to_process}/{total_pages} pages processed")

    except Exception as e:
        logger.error(f"EasyOCR processing failed for book_id={book_id}: {e}", exc_info=True)
        raise
    finally:
        # Clean up
        if reader:
            del reader
        db.close()


# Global Surya model cache
_surya_models_cache = {
    'foundation': None,
    'detection': None,
    'recognition': None,
    'loaded': False
}


def load_surya_models():
    """
    Load Surya OCR models into GPU memory and cache them.

    Returns:
        dict: Status dictionary with 'success' and 'message' keys
    """
    global _surya_models_cache

    try:
        if _surya_models_cache['loaded']:
            logger.info("Surya models already loaded in cache")
            return {
                'success': True,
                'message': 'Surya OCR already loaded in GPU'
            }

        logger.info("Loading Surya OCR models to GPU...")

        from surya.foundation import FoundationPredictor
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor

        # Load models
        _surya_models_cache['foundation'] = FoundationPredictor()
        _surya_models_cache['detection'] = DetectionPredictor()
        _surya_models_cache['recognition'] = RecognitionPredictor(_surya_models_cache['foundation'])
        _surya_models_cache['loaded'] = True

        logger.info("✅ Surya OCR models loaded successfully to GPU")

        return {
            'success': True,
            'message': 'Surya OCR loaded successfully on GPU'
        }

    except Exception as e:
        logger.error(f"❌ Failed to load Surya models: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Failed to load Surya OCR: {str(e)}'
        }


def unload_surya_models():
    """
    Unload Surya OCR models from GPU memory to free up VRAM.

    Returns:
        dict: Status dictionary with 'success' and 'message' keys
    """
    global _surya_models_cache

    try:
        if not _surya_models_cache['loaded']:
            logger.info("Surya models not loaded, nothing to unload")
            return {
                'success': True,
                'message': 'Surya OCR was not loaded'
            }

        logger.info("Unloading Surya OCR models from GPU...")

        # Clear model references
        _surya_models_cache['foundation'] = None
        _surya_models_cache['detection'] = None
        _surya_models_cache['recognition'] = None
        _surya_models_cache['loaded'] = False

        # Force garbage collection to free memory
        import gc
        gc.collect()

        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
        except:
            pass

        logger.info("✅ Surya OCR models unloaded successfully from GPU")

        return {
            'success': True,
            'message': 'Surya OCR unloaded successfully from GPU'
        }

    except Exception as e:
        logger.error(f"❌ Failed to unload Surya models: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Failed to unload Surya OCR: {str(e)}'
        }


def check_surya_models_status():
    """
    Check if Surya OCR models are currently loaded in GPU memory.

    Returns:
        dict: Status dictionary with 'loaded', 'success', and 'message' keys
    """
    global _surya_models_cache

    try:
        is_loaded = _surya_models_cache['loaded']

        if is_loaded:
            logger.info("Surya models status: LOADED")
            return {
                'success': True,
                'loaded': True,
                'message': 'Surya OCR is currently loaded on GPU'
            }
        else:
            logger.info("Surya models status: NOT LOADED")
            return {
                'success': True,
                'loaded': False,
                'message': 'Surya OCR is NOT loaded on GPU'
            }

    except Exception as e:
        logger.error(f"❌ Failed to check Surya models status: {e}", exc_info=True)
        return {
            'success': False,
            'loaded': False,
            'message': f'Failed to check status: {str(e)}'
        }


def run_surya_on_single_image(image_bytes: bytes) -> dict:
    """
    Run Surya OCR on a single image (synchronous).

    This function is used for interactive clip OCR in the verify-pages UI.
    It uses the cached Surya models if available, or loads them if needed.

    Args:
        image_bytes: Raw image bytes (PNG format expected)

    Returns:
        dict: {
            'success': bool,
            'text': str,
            'confidence': float (0-1),
            'language': str,
            'error': str (only if success=False)
        }
    """
    global _surya_models_cache

    from PIL import Image
    import io

    logger.info("Running Surya OCR on single image clip")

    try:
        # Check if models are loaded, if not, load them
        if not _surya_models_cache['loaded']:
            logger.info("Surya models not loaded, loading now...")
            load_result = load_surya_models()
            if not load_result['success']:
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0.0,
                    'language': 'unknown',
                    'error': f"Failed to load Surya models: {load_result['message']}"
                }

        # Convert bytes to PIL Image
        img = Image.open(io.BytesIO(image_bytes))
        logger.info(f"Image loaded: {img.size[0]}x{img.size[1]} pixels, mode={img.mode}")

        # Ensure image is RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Get cached models
        det_predictor = _surya_models_cache['detection']
        rec_predictor = _surya_models_cache['recognition']

        if not det_predictor or not rec_predictor:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'language': 'unknown',
                'error': "Surya models not properly loaded"
            }

        # Run OCR using new RecognitionPredictor API (v0.17.0)
        from surya.common.surya.schema import TaskNames

        task_names = [TaskNames.ocr_with_boxes]
        predictions = rec_predictor(
            [img],
            task_names=task_names,
            det_predictor=det_predictor,
            math_mode=False
        )

        if predictions and len(predictions) > 0:
            prediction = predictions[0]

            # Extract text from all text lines
            texts = []
            confidences = []

            for text_line in prediction.text_lines:
                texts.append(text_line.text)
                if hasattr(text_line, 'confidence'):
                    confidences.append(text_line.confidence)

            # Combine all text
            ocr_text = '\n'.join(texts)

            # Calculate average confidence (Surya returns 0-1)
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
            else:
                avg_confidence = 0.9  # Default if not available

            logger.info(f"OCR completed: {len(ocr_text)} chars, confidence={avg_confidence:.2f}")

            return {
                'success': True,
                'text': ocr_text,
                'confidence': avg_confidence,
                'language': 'auto'  # Surya auto-detects
            }
        else:
            logger.warning("No predictions returned from Surya OCR")
            return {
                'success': True,
                'text': '',
                'confidence': 0.0,
                'language': 'auto'
            }

    except Exception as e:
        logger.error(f"❌ Surya OCR on clip failed: {e}", exc_info=True)
        return {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'language': 'unknown',
            'error': str(e)
        }


def run_surya_sequential(book_id: int, max_pages: int = None):
    """
    Run Surya OCR processing sequentially for all pages.

    NEW FLOW: Uses pre-scanned images from raw_pages table instead of rendering PDF.

    Process:
    1. Load Surya into GPU (2GB+ VRAM)
    2. For each page:
       - LOAD image from raw_{table_prefix}_pages
       - Run Surya OCR on loaded image
       - Save results to raw_{table_prefix}_knowledge_units
    3. Unload Surya from GPU
    4. Mark surya_ocr_complete = true

    Args:
        book_id: Book ID to process
        max_pages: Optional limit on number of pages to process (for testing)
    """
    from PIL import Image
    from surya.foundation import FoundationPredictor
    from surya.detection import DetectionPredictor
    from surya.recognition import RecognitionPredictor
    from surya.common.surya.schema import TaskNames
    import io

    pages_msg = f" (limiting to {max_pages} pages)" if max_pages else ""
    logger.info(f"=== Surya OCR function called for book_id={book_id}{pages_msg} ===")
    logger.info(f"Starting Surya OCR sequential processing for book_id={book_id}")

    db = SessionLocal()

    try:
        # Get book metadata
        result = db.execute(
            text("SELECT table_prefix, total_pages FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if not result:
            raise ValueError(f"Book {book_id} not found")

        table_prefix, total_pages = result

        # Determine how many pages to process
        pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
        pages_msg = f" (max {max_pages} pages)" if max_pages else ""

        logger.info(f"Processing {pages_to_process}/{total_pages} pages with Surya OCR{pages_msg}")
        logger.info(f"Loading images from raw_{table_prefix}_pages table")

        # Load Surya predictors (GPU mode) - New v0.17.0 API
        logger.info("Loading Surya OCR models to GPU (v0.17.0 API)...")
        foundation_predictor = FoundationPredictor()
        det_predictor = DetectionPredictor()
        rec_predictor = RecognitionPredictor(foundation_predictor)
        logger.info("Surya OCR models loaded successfully")

        for page_num in range(1, pages_to_process + 1):
            logger.info(f"Processing page {page_num}/{pages_to_process} with Surya OCR")

            # Load image from raw_pages table
            page_result = db.execute(
                text(f"""
                SELECT original_image_data, original_width, original_height
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_num
                """),
                {"page_num": page_num}
            ).first()

            if not page_result:
                logger.error(f"Page {page_num} not found in raw_{table_prefix}_pages table! Run 'Scan Pages' first.")
                raise ValueError(f"Page {page_num} not scanned yet. Please run 'Scan Pages' first.")

            # Convert binary image data to PIL Image
            img_data = page_result[0]
            img = Image.open(io.BytesIO(img_data))
            logger.info(f"  Loaded image from database: {img.size[0]}x{img.size[1]} pixels")

            # Run Surya OCR (New v0.17.0 API)
            try:
                # Run OCR using new RecognitionPredictor API
                task_names = [TaskNames.ocr_with_boxes]  # Task for each image
                predictions = rec_predictor(
                    [img],  # List of PIL images
                    task_names=task_names,
                    det_predictor=det_predictor,
                    math_mode=False  # Disable math recognition for Arabic
                )

                if predictions and len(predictions) > 0:
                    prediction = predictions[0]

                    # Extract text from all text lines
                    texts = []
                    confidences = []

                    for text_line in prediction.text_lines:
                        texts.append(text_line.text)
                        # In v0.17.0, confidence might be stored differently, check if it exists
                        if hasattr(text_line, 'confidence'):
                            confidences.append(text_line.confidence)

                    # Combine all text
                    page_text = '\n'.join(texts)

                    # Calculate average confidence (Surya returns 0-1, convert to 0-100)
                    if confidences:
                        avg_confidence = sum(confidences) / len(confidences) * 100
                    else:
                        avg_confidence = 90.0  # Default confidence if not available
                    confidence_str = f"{avg_confidence:.2f}"

                    logger.info(f"Page {page_num}: Extracted {len(texts)} text lines, avg confidence: {confidence_str}%")
                else:
                    page_text = ""
                    confidence_str = "0.0"
                    logger.warning(f"Page {page_num}: No text detected by Surya OCR")

            except Exception as ocr_error:
                logger.error(f"Surya OCR failed on page {page_num}: {ocr_error}", exc_info=True)
                page_text = ""
                confidence_str = "0.0"

            # Save raw OCR result to raw_knowledge_units table
            db.execute(
                text(f"""
                INSERT INTO raw_{table_prefix}_knowledge_units
                    (page_number, ocr_engine, full_page_text, text_length, confidence_score, language, ocr_run_timestamp)
                VALUES (:page_num, 'surya', :ocr_text, :text_len, :confidence, 'ar', CURRENT_TIMESTAMP)
                ON CONFLICT (page_number, ocr_engine) DO UPDATE SET
                    full_page_text = EXCLUDED.full_page_text,
                    text_length = EXCLUDED.text_length,
                    confidence_score = EXCLUDED.confidence_score,
                    ocr_run_timestamp = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """),
                {
                    "page_num": page_num,
                    "ocr_text": page_text,
                    "text_len": len(page_text),
                    "confidence": float(confidence_str) / 100.0  # Convert 0-100 to 0-1
                }
            )

            # Also update the old knowledge_units table for backwards compatibility
            db.execute(
                text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET attr3_value = :ocr_text, attr6_value = :confidence
                WHERE page_number = :page_num
                """),
                {"page_num": page_num, "ocr_text": page_text, "confidence": confidence_str}
            )

            # Update progress tracking
            db.execute(
                text(f"""
                UPDATE {table_prefix}_processing_state
                SET current_page = :page, surya_pages_processed = :page
                WHERE id = 1
                """),
                {"page": page_num}
            )

            # Commit after every page for immediate progress visibility
            db.commit()
            logger.info(f"✓ Page {page_num}/{pages_to_process} completed and saved")

        # Mark Surya OCR complete (only if processed all pages)
        completion_status = (pages_to_process == total_pages)
        db.execute(
            text(f"""
            UPDATE {table_prefix}_processing_state
            SET surya_ocr_complete = :complete, current_agent = 'surya', current_page = :page,
                surya_pages_processed = :page
            WHERE id = 1
            """),
            {"complete": completion_status, "page": pages_to_process}
        )
        db.commit()

        logger.info(f"✅ Surya OCR processing complete for book_id={book_id}: {pages_to_process} pages processed")

    except Exception as e:
        logger.error(f"❌ Surya OCR processing failed for book_id={book_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
        logger.info(f"=== Surya OCR function finished for book_id={book_id} ===")


async def run_tesseract_sequential(book_id: int, max_pages: int = None):
    """
    Run Tesseract processing sequentially for all pages.

    NEW FLOW: Uses pre-scanned images from raw_pages table instead of rendering PDF.

    Process:
    1. Load Tesseract (CPU-based)
    2. For each page:
       - LOAD image from raw_{table_prefix}_pages
       - Run Tesseract on loaded image
       - Save results to raw_{table_prefix}_knowledge_units
    3. Mark tesseract_complete = true

    Args:
        book_id: Book ID to process
        max_pages: Optional limit on number of pages to process (for testing)
    """
    from PIL import Image
    import pytesseract
    import io

    logger.info(f"Starting Tesseract sequential processing for book_id={book_id}")

    db = SessionLocal()

    try:
        # Get book metadata
        result = db.execute(
            text("SELECT table_prefix, total_pages FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if not result:
            raise ValueError(f"Book {book_id} not found")

        table_prefix, total_pages = result

        # Determine how many pages to process
        pages_to_process = min(max_pages, total_pages) if max_pages else total_pages

        logger.info(f"Processing {pages_to_process}/{total_pages} pages with Tesseract OCR")
        logger.info(f"Loading images from raw_{table_prefix}_pages table")

        # Configure Tesseract for English and Arabic
        custom_config = r'--oem 3 --psm 6 -l eng+ara'

        for page_num in range(1, pages_to_process + 1):
            logger.info(f"Processing page {page_num}/{pages_to_process} with Tesseract OCR")

            # Load image from raw_pages table
            page_result = db.execute(
                text(f"""
                SELECT original_image_data, original_width, original_height
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_num
                """),
                {"page_num": page_num}
            ).first()

            if not page_result:
                logger.error(f"Page {page_num} not found in raw_{table_prefix}_pages table! Run 'Scan Pages' first.")
                raise ValueError(f"Page {page_num} not scanned yet. Please run 'Scan Pages' first.")

            # Convert binary image data to PIL Image
            img_data = page_result[0]
            img = Image.open(io.BytesIO(img_data))
            logger.info(f"  Loaded image from database: {img.size[0]}x{img.size[1]} pixels")

            # Run Tesseract OCR
            try:
                # Get text with confidence data
                data = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)

                # Extract text and confidence from results
                texts = []
                confidences = []

                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = data['conf'][i]

                    # Skip empty text and invalid confidence values
                    if text and conf != -1:
                        texts.append(text)
                        confidences.append(float(conf))

                if texts:
                    # Combine all text with spaces
                    page_text = ' '.join(texts)

                    # Calculate average confidence (Tesseract returns 0-100)
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    confidence_str = f"{avg_confidence:.2f}"

                    logger.info(f"Page {page_num}: Extracted {len(texts)} text elements, avg confidence: {confidence_str}%")
                else:
                    page_text = ""
                    confidence_str = "0.0"
                    logger.warning(f"Page {page_num}: No text detected by Tesseract")

            except Exception as ocr_error:
                logger.error(f"Tesseract OCR failed on page {page_num}: {ocr_error}")
                page_text = ""
                confidence_str = "0.0"

            # Update knowledge_units with Tesseract results (attr4_value, attr7_value)
            db.execute(
                text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET attr4_value = :ocr_text, attr7_value = :confidence
                WHERE page_number = :page_num
                """),
                {"page_num": page_num, "ocr_text": page_text, "confidence": confidence_str}
            )

            # Commit every 5 pages
            if page_num % 5 == 0 or page_num == total_pages:
                db.execute(
                    text(f"UPDATE {table_prefix}_processing_state SET current_page = :page WHERE id = 1"),
                    {"page": page_num}
                )
                db.commit()
                logger.info(f"Progress saved: {page_num}/{total_pages} pages")

        # Close PDF
        pdf_doc.close()

        # Mark Tesseract complete
        db.execute(
            text(f"""
            UPDATE {table_prefix}_processing_state
            SET tesseract_complete = true, current_agent = 'tesseract', current_page = :page
            WHERE id = 1
            """),
            {"page": total_pages}
        )
        db.commit()

        logger.info(f"Tesseract processing complete for book_id={book_id}: {total_pages} pages processed")

    except Exception as e:
        logger.error(f"Tesseract processing failed for book_id={book_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def run_evaluate_split_mark(book_id: int):
    """
    Evaluate OCR results, select best, run splitter and marker agents.

    Process:
    1. Evaluation: Compare confidence scores (attr5, attr6, attr7)
    2. Select best OCR result per page
    3. Copy winning text to main text_content field
    4. Set ocr_method field
    5. Run Splitter Agent (semantic 3-5 line chunks)
    6. Run Marker Agent (green/orange rectangles)
    7. Update status to "ready for verification"

    Args:
        book_id: Book ID to process
    """
    logger.info(f"Starting Evaluate/Split/Mark for book_id={book_id}")

    db = SessionLocal()
    try:
        # Get book metadata
        result = db.execute(
            text("SELECT table_prefix, total_pages FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if not result:
            raise ValueError(f"Book {book_id} not found")

        table_prefix, total_pages = result

        # Step 1: Evaluate and select best OCR
        logger.info("Evaluating OCR results...")
        for page_num in range(1, total_pages + 1):
            # Get all OCR results for this page
            results = db.execute(
                text(f"""
                SELECT attr2_value, attr3_value, attr4_value,
                       attr5_value, attr6_value, attr7_value
                FROM {table_prefix}_knowledge_units
                WHERE page_number = :page_num
                """),
                {"page_num": page_num}
            ).first()

            if not results:
                continue

            # Compare confidences
            confidences = {
                'paddleocr': float(results[3]) if results[3] else 0,
                'surya': float(results[4]) if results[4] else 0,
                'tesseract': float(results[5]) if results[5] else 0
            }

            # Select best
            best_method = max(confidences, key=confidences.get)
            best_text = results[0] if best_method == 'paddleocr' else \
                       results[1] if best_method == 'surya' else results[2]
            best_confidence = confidences[best_method]

            # Update main text field
            db.execute(
                text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET text_content = :text, ocr_method = :method, confidence_score = :confidence
                WHERE page_number = :page_num
                """),
                {"text": best_text, "method": best_method, "confidence": best_confidence, "page_num": page_num}
            )

        db.commit()
        logger.info("OCR evaluation complete")

        # Step 2: Run Splitter Agent
        logger.info("Running Splitter Agent...")
        from src.services.text_splitter import get_text_splitter
        splitter = get_text_splitter()

        # Note: Chunking is done in-memory for display purposes
        # The text_content field contains the full page text
        # Frontend can split on-demand for display
        logger.info("Splitter Agent ready (frontend will handle display chunking)")

        # Step 3: Run Marker Agent
        logger.info("Running Marker Agent...")
        from src.services.marker_agent import get_marker_agent
        marker = get_marker_agent()

        # Generate marked images for all pages
        marker_result = await marker.generate_marked_images_for_book(
            book_id,
            table_prefix,
            total_pages
        )
        logger.info(
            f"Marker Agent complete: {marker_result['success_count']} pages marked, "
            f"{marker_result['skipped_count']} skipped"
        )

        # Mark complete
        db.execute(
            text(f"""
            UPDATE {table_prefix}_processing_state
            SET evaluation_complete = true, splitter_complete = true,
                marker_complete = true, status = 'ready_for_verification'
            WHERE id = 1
            """)
        )
        db.commit()

        logger.info(f"Evaluate/Split/Mark complete for book_id={book_id}")

    except Exception as e:
        logger.error(f"Evaluate/Split/Mark failed for book_id={book_id}: {e}")
        raise
    finally:
        db.close()


def analyze_and_store_image(book_id: int, page_num: int, image_data: bytes, table_prefix: str):
    """
    Analyze image with Claude Sonnet 4.5 and generate SVG.

    Args:
        book_id: Book ID
        page_num: Page number
        image_data: Image binary data
        table_prefix: Table prefix for this book
    """
    try:
        # Analyze with Claude
        analyzer = get_image_analyzer()
        analysis = analyzer.analyze_image(image_data)

        # Generate SVG
        svg_code = generate_svg_from_json(analysis['structured_json'])

        # Store in images table
        db = SessionLocal()
        try:
            db.execute(
                text(f"""
                INSERT INTO {table_prefix}_images
                (image_identifier, page_number, image_data, image_type,
                 ai_description, structured_json, svg_code, confidence_score,
                 analyzed_during_ocr)
                VALUES (:id, :page, :data, :type, :desc, :json, :svg, :conf, 'paddleocr')
                """),
                {
                    "id": f"IMG-{book_id}-{page_num}",
                    "page": page_num,
                    "data": image_data,
                    "type": analysis['image_type'],
                    "desc": analysis['description'],
                    "json": analysis['structured_json'],
                    "svg": svg_code,
                    "conf": analysis['confidence_score']
                }
            )
            db.commit()
        finally:
            db.close()

        logger.info(f"Image analyzed and stored: page {page_num}")

    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
