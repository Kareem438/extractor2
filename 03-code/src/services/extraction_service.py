"""
Extraction Service for Phase 3B

Extracts knowledge units from Layout Review regions:
- Paragraph OCR with Surya at 600 DPI
- Diagram/Table/Equation/List image extraction
- L3 Title OCR
- L1/L2 title lookup from config
"""

import io
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from PIL import Image
from sqlalchemy import text

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

# Global state for extraction jobs
_active_extraction_jobs: Dict[int, Dict] = {}
_websocket_connections: Dict[int, List] = {}


def get_book_info(db, book_id: int) -> Dict:
    """Get book metadata including table prefix."""
    result = db.execute(
        text("SELECT table_prefix, book_name, total_pages, auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result:
        raise ValueError(f"Book {book_id} not found")

    config = result[3] if result[3] else {}
    if isinstance(config, str):
        import json
        config = json.loads(config)

    return {
        "table_prefix": result[0],
        "book_name": result[1],
        "total_pages": result[2],
        "config": config
    }


def get_page_image(db, table_prefix: str, page_number: int) -> Optional[bytes]:
    """Get raw page image data."""
    result = db.execute(
        text(f"SELECT original_image_data FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
        {"page_num": page_number}
    ).fetchone()

    return result[0] if result else None


def get_layout_regions(db, table_prefix: str, page_number: int) -> List[Dict]:
    """Get layout detection regions for a page."""
    result = db.execute(
        text(f"""
            SELECT id, class_name, x, y, width, height, confidence, l3_title_id
            FROM raw_{table_prefix}_layout_detections
            WHERE page_number = :page_num
            AND class_name != 'ignore'
            ORDER BY y, x
        """),
        {"page_num": page_number}
    ).fetchall()

    return [{
        "id": row[0],
        "class_name": row[1],
        "x": row[2],
        "y": row[3],
        "width": row[4],
        "height": row[5],
        "confidence": row[6],
        "l3_title_id": row[7]
    } for row in result]


def get_diagram_paragraph_links(db, table_prefix: str, page_number: int) -> Dict[int, int]:
    """Get diagram-to-paragraph links for a page.

    Returns: Dict mapping diagram_region_id -> paragraph_region_id
    """
    result = db.execute(
        text(f"""
            SELECT diagram_region_id, paragraph_region_id
            FROM raw_{table_prefix}_layout_detections ld
            WHERE ld.page_number = :page_num
            AND ld.linked_paragraph_id IS NOT NULL
        """),
        {"page_num": page_number}
    ).fetchall()

    # Also check the links stored in layout_detection_config
    # Links are stored as {diagram_region_id, paragraph_region_id}
    return {row[0]: row[1] for row in result}


def get_l3_title_text(db, table_prefix: str, l3_title_id: int) -> Optional[str]:
    """Get L3 title text by running OCR on the L3 title region."""
    if not l3_title_id:
        return None

    result = db.execute(
        text(f"""
            SELECT ocr_text FROM raw_{table_prefix}_layout_detections
            WHERE id = :id
        """),
        {"id": l3_title_id}
    ).fetchone()

    return result[0] if result and result[0] else None


def get_titles_for_page(config: Dict, page_number: int) -> Tuple[str, str]:
    """Get L1 and L2 titles for a page from auto-slicer config."""
    l1_title = None
    l2_title = None

    titles = config.get('titles', {})

    # Find L1 title
    for t in titles.get('level1', []):
        start = t.get('start_page', 1)
        end = t.get('end_page', 9999)
        if start <= page_number <= end:
            l1_title = t.get('title')

    # Find L2 title
    for t in titles.get('level2', []):
        start = t.get('start_page', 1)
        end = t.get('end_page', 9999)
        if start <= page_number <= end:
            l2_title = t.get('title')

    return l1_title, l2_title


def crop_region_image(page_image_bytes: bytes, region: Dict) -> bytes:
    """Crop a region from the page image and return as PNG bytes."""
    img = Image.open(io.BytesIO(page_image_bytes))

    # Crop the region
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    cropped = img.crop((x, y, x + w, y + h))

    # Convert to PNG bytes
    output = io.BytesIO()
    cropped.save(output, format='PNG')
    return output.getvalue()


async def run_surya_ocr(image_bytes: bytes) -> Tuple[str, float]:
    """Run Surya OCR on an image and return text with confidence.

    This is a placeholder - actual implementation needs Surya OCR integration.
    """
    try:
        from src.services.ocr_sequential import OCRService

        # Load image
        img = Image.open(io.BytesIO(image_bytes))

        # Create OCR service and run Surya
        ocr_service = OCRService()

        # Run OCR (Surya is typically the second engine tried)
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ocr_service.run_surya_ocr(img)
        )

        if result:
            return result.get('text', ''), result.get('confidence', 0.0)

        return '', 0.0

    except Exception as e:
        logger.error(f"Surya OCR error: {e}")
        # Fallback: try to return empty result
        return '', 0.0


def save_paragraph(db, table_prefix: str, page_number: int, region: Dict,
                   ocr_text: str, ocr_confidence: float,
                   l1_title: str, l2_title: str, l3_title: str,
                   raw_page_id: int) -> int:
    """Save extracted paragraph to database."""

    result = db.execute(
        text(f"""
            INSERT INTO raw_{table_prefix}_paragraph_images (
                raw_page_id, page_number,
                selection_x, selection_y, selection_width, selection_height,
                image_data, image_format,
                image_width, image_height, image_size_bytes,
                extracted_text, ocr_confidence,
                selected_level_text,
                approval_status, created_at
            ) VALUES (
                :raw_page_id, :page_number,
                :x, :y, :width, :height,
                :image_data, 'png',
                :width, :height, :image_size,
                :text, :confidence,
                :level_text,
                'pending', NOW()
            )
            RETURNING id
        """),
        {
            "raw_page_id": raw_page_id,
            "page_number": page_number,
            "x": region['x'],
            "y": region['y'],
            "width": region['width'],
            "height": region['height'],
            "image_data": region.get('image_bytes', b''),
            "image_size": len(region.get('image_bytes', b'')),
            "text": ocr_text,
            "confidence": ocr_confidence,
            "level_text": f"L1: {l1_title or '-'} | L2: {l2_title or '-'} | L3: {l3_title or '-'}"
        }
    )

    return result.fetchone()[0]


def save_diagram(db, table_prefix: str, page_number: int, region: Dict,
                 diagram_type: str, image_bytes: bytes,
                 l1_title: str, l2_title: str, l3_title: str,
                 parent_paragraph_id: Optional[int],
                 raw_page_id: int) -> int:
    """Save extracted diagram/table/equation/list to database."""

    result = db.execute(
        text(f"""
            INSERT INTO raw_{table_prefix}_diagram_images (
                raw_page_id, page_number,
                selection_x, selection_y, selection_width, selection_height,
                image_data, image_format,
                image_width, image_height, image_size_bytes,
                diagram_type,
                level_1_title, level_2_title, level_3_title,
                linked_knowledge_unit_id,
                approval_status, created_at
            ) VALUES (
                :raw_page_id, :page_number,
                :x, :y, :width, :height,
                :image_data, 'png',
                :width, :height, :image_size,
                :diagram_type,
                :l1, :l2, :l3,
                :parent_id,
                'pending', NOW()
            )
            RETURNING id
        """),
        {
            "raw_page_id": raw_page_id,
            "page_number": page_number,
            "x": region['x'],
            "y": region['y'],
            "width": region['width'],
            "height": region['height'],
            "image_data": image_bytes,
            "image_size": len(image_bytes),
            "diagram_type": diagram_type,
            "l1": l1_title,
            "l2": l2_title,
            "l3": l3_title,
            "parent_id": parent_paragraph_id
        }
    )

    return result.fetchone()[0]


def update_l3_title_ocr(db, table_prefix: str, region_id: int, ocr_text: str, confidence: float):
    """Update OCR text for an L3 title region."""
    db.execute(
        text(f"""
            UPDATE raw_{table_prefix}_layout_detections
            SET ocr_text = :text, ocr_confidence = :confidence, updated_at = NOW()
            WHERE id = :id
        """),
        {"id": region_id, "text": ocr_text, "confidence": confidence}
    )


def get_raw_page_id(db, table_prefix: str, page_number: int) -> Optional[int]:
    """Get raw page ID for a page number."""
    result = db.execute(
        text(f"SELECT id FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
        {"page_num": page_number}
    ).fetchone()

    return result[0] if result else None


async def broadcast_progress(book_id: int, message: Dict):
    """Broadcast progress update to WebSocket clients."""
    if book_id not in _websocket_connections:
        return

    import json
    message_str = json.dumps(message)

    dead_connections = []
    for ws in _websocket_connections.get(book_id, []):
        try:
            await ws.send_text(message_str)
        except:
            dead_connections.append(ws)

    for ws in dead_connections:
        _websocket_connections[book_id].remove(ws)


async def extract_page(book_id: int, page_number: int, job: Dict) -> Dict:
    """Extract all regions from a single page.

    Returns: Dict with counts of extracted items
    """
    db = SessionLocal()
    try:
        book_info = get_book_info(db, book_id)
        table_prefix = book_info['table_prefix']
        config = book_info['config']

        # Get page image
        page_image_bytes = get_page_image(db, table_prefix, page_number)
        if not page_image_bytes:
            logger.warning(f"No image found for page {page_number}")
            return {"paragraphs": 0, "diagrams": 0, "error": "No page image"}

        # Get raw page ID
        raw_page_id = get_raw_page_id(db, table_prefix, page_number)
        if not raw_page_id:
            logger.warning(f"No raw page record for page {page_number}")
            return {"paragraphs": 0, "diagrams": 0, "error": "No raw page record"}

        # Get L1/L2 titles for this page
        l1_title, l2_title = get_titles_for_page(config, page_number)

        # Get all regions for this page
        regions = get_layout_regions(db, table_prefix, page_number)

        # Get diagram-paragraph links
        # Note: Links are stored in layout_detection_config, not in the detections table
        layout_config = config.get('layout_detection_config', {})
        links = layout_config.get('links', [])
        link_map = {link['diagram_region_id']: link['paragraph_region_id'] for link in links}

        # Track counts
        paragraphs_extracted = 0
        diagrams_extracted = 0

        # First pass: Extract L3 title text
        l3_title_texts = {}
        for region in regions:
            if region['class_name'] in ['title_level_3', 'Title L3', 'title_l3']:
                # Crop and OCR the L3 title
                try:
                    image_bytes = crop_region_image(page_image_bytes, region)
                    ocr_text, confidence = await run_surya_ocr(image_bytes)
                    update_l3_title_ocr(db, table_prefix, region['id'], ocr_text, confidence)
                    l3_title_texts[region['id']] = ocr_text
                except Exception as e:
                    logger.error(f"Error OCR-ing L3 title region {region['id']}: {e}")
                    l3_title_texts[region['id']] = None

        db.commit()

        # Map from region_id to paragraph_id for linking
        region_to_paragraph = {}

        # Second pass: Extract paragraphs
        for region in regions:
            if region['class_name'] == 'paragraph':
                try:
                    # Crop region image
                    image_bytes = crop_region_image(page_image_bytes, region)
                    region['image_bytes'] = image_bytes

                    # Run Surya OCR
                    ocr_text, confidence = await run_surya_ocr(image_bytes)

                    # Get L3 title text
                    l3_title = None
                    if region.get('l3_title_id'):
                        l3_title = l3_title_texts.get(region['l3_title_id'])

                    # Save paragraph
                    para_id = save_paragraph(
                        db, table_prefix, page_number, region,
                        ocr_text, confidence,
                        l1_title, l2_title, l3_title,
                        raw_page_id
                    )

                    region_to_paragraph[region['id']] = para_id
                    paragraphs_extracted += 1

                    # Update progress
                    job['paragraphs_extracted'] = job.get('paragraphs_extracted', 0) + 1

                except Exception as e:
                    logger.error(f"Error extracting paragraph region {region['id']}: {e}")

        db.commit()

        # Third pass: Extract diagrams/tables/equations/lists
        diagram_classes = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered']

        for region in regions:
            if region['class_name'] in diagram_classes:
                try:
                    # Crop region image
                    image_bytes = crop_region_image(page_image_bytes, region)

                    # Get L3 title text
                    l3_title = None
                    if region.get('l3_title_id'):
                        l3_title = l3_title_texts.get(region['l3_title_id'])

                    # Get parent paragraph ID from link
                    parent_region_id = link_map.get(region['id'])
                    parent_paragraph_id = None
                    if parent_region_id:
                        parent_paragraph_id = region_to_paragraph.get(parent_region_id)

                    # Save diagram
                    save_diagram(
                        db, table_prefix, page_number, region,
                        region['class_name'], image_bytes,
                        l1_title, l2_title, l3_title,
                        parent_paragraph_id,
                        raw_page_id
                    )

                    diagrams_extracted += 1
                    job['diagrams_extracted'] = job.get('diagrams_extracted', 0) + 1

                except Exception as e:
                    logger.error(f"Error extracting diagram region {region['id']}: {e}")

        db.commit()

        return {
            "paragraphs": paragraphs_extracted,
            "diagrams": diagrams_extracted
        }

    except Exception as e:
        logger.error(f"Error extracting page {page_number}: {e}")
        db.rollback()
        return {"paragraphs": 0, "diagrams": 0, "error": str(e)}
    finally:
        db.close()


async def run_extraction_job(book_id: int, page_numbers: List[int]):
    """Run extraction for multiple pages."""
    job = _active_extraction_jobs.get(book_id)
    if not job:
        return

    job['status'] = 'running'
    job['total_pages'] = len(page_numbers)
    job['current_page'] = 0
    job['paragraphs_extracted'] = 0
    job['diagrams_extracted'] = 0
    job['started_at'] = datetime.utcnow().isoformat()

    await broadcast_progress(book_id, {
        "type": "started",
        "total_pages": len(page_numbers)
    })

    try:
        for idx, page_num in enumerate(page_numbers):
            if job.get('cancel_requested'):
                job['status'] = 'cancelled'
                await broadcast_progress(book_id, {"type": "cancelled"})
                return

            job['current_page'] = page_num
            job['pages_processed'] = idx

            await broadcast_progress(book_id, {
                "type": "progress",
                "current_page": page_num,
                "pages_processed": idx,
                "total_pages": len(page_numbers),
                "paragraphs_extracted": job['paragraphs_extracted'],
                "diagrams_extracted": job['diagrams_extracted']
            })

            # Extract the page
            result = await extract_page(book_id, page_num, job)

            if result.get('error'):
                job.setdefault('errors', []).append({
                    "page": page_num,
                    "error": result['error']
                })

        job['status'] = 'completed'
        job['completed_at'] = datetime.utcnow().isoformat()

        # Update config to mark pages as extracted
        db = SessionLocal()
        try:
            result = db.execute(
                text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).fetchone()

            if result and result[0]:
                import json
                config = result[0] if isinstance(result[0], dict) else json.loads(result[0])
                extracted = set(config.get('extracted_pages', []))
                extracted.update(page_numbers)
                config['extracted_pages'] = list(extracted)
                config['extraction_status'] = 'completed'
                config['last_extraction'] = datetime.utcnow().isoformat()

                db.execute(
                    text("UPDATE books_metadata SET auto_slicer_config = :config WHERE book_id = :book_id"),
                    {"book_id": book_id, "config": json.dumps(config)}
                )
                db.commit()
        finally:
            db.close()

        await broadcast_progress(book_id, {
            "type": "completed",
            "paragraphs_extracted": job['paragraphs_extracted'],
            "diagrams_extracted": job['diagrams_extracted'],
            "errors": job.get('errors', [])
        })

    except Exception as e:
        logger.error(f"Extraction job failed: {e}")
        job['status'] = 'error'
        job['error'] = str(e)

        await broadcast_progress(book_id, {
            "type": "error",
            "error": str(e)
        })


def start_extraction(book_id: int, page_numbers: List[int]) -> Dict:
    """Start extraction job for a book."""
    if book_id in _active_extraction_jobs:
        status = _active_extraction_jobs[book_id].get('status')
        if status == 'running':
            return {"error": "Extraction already running", "status": "running"}

    _active_extraction_jobs[book_id] = {
        "status": "starting",
        "page_numbers": page_numbers
    }

    # Start the job in background
    asyncio.create_task(run_extraction_job(book_id, page_numbers))

    return {
        "status": "started",
        "pages": page_numbers,
        "message": "Extraction started"
    }


def get_extraction_status(book_id: int) -> Dict:
    """Get current extraction status."""
    job = _active_extraction_jobs.get(book_id)

    if not job:
        return {"status": "idle"}

    return {
        "status": job.get('status', 'unknown'),
        "current_page": job.get('current_page', 0),
        "total_pages": job.get('total_pages', 0),
        "pages_processed": job.get('pages_processed', 0),
        "paragraphs_extracted": job.get('paragraphs_extracted', 0),
        "diagrams_extracted": job.get('diagrams_extracted', 0),
        "errors": job.get('errors', [])
    }


def cancel_extraction(book_id: int) -> Dict:
    """Cancel a running extraction job."""
    job = _active_extraction_jobs.get(book_id)

    if not job:
        return {"error": "No active job"}

    if job.get('status') != 'running':
        return {"error": f"Job is not running (status: {job.get('status')})"}

    job['cancel_requested'] = True
    return {"status": "cancelling"}


def register_websocket(book_id: int, websocket):
    """Register a WebSocket connection for progress updates."""
    if book_id not in _websocket_connections:
        _websocket_connections[book_id] = []
    _websocket_connections[book_id].append(websocket)


def unregister_websocket(book_id: int, websocket):
    """Unregister a WebSocket connection."""
    if book_id in _websocket_connections:
        if websocket in _websocket_connections[book_id]:
            _websocket_connections[book_id].remove(websocket)
