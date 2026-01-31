"""
Layout Detection API Routes

Provides endpoints for DocLayout-YOLO based automatic boundary detection.
Integrated with the Auto-Slicer feature for enhanced document processing.

Features:
- Layout detection with YOLO model
- Detection status and progress
- Region management (get, update, delete)
- Model management (list, activate, train)
- WebSocket for real-time progress

Phase: 1.3 of Automatic Boundaries Implementation
Author: Claude Code
Date: 2026-01-14
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from datetime import datetime
import json
import asyncio
import base64
from io import BytesIO

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

# Import layout detection service
try:
    from src.services.layout_detection_service import (
        layout_detection_service,
        DetectedRegion,
        DetectionResult,
        DetectionProgress,
        check_model_exists,
        ensure_model_directories,
        EXTENDED_CLASS_MAPPING
    )
    LAYOUT_SERVICE_AVAILABLE = True
except ImportError as e:
    LAYOUT_SERVICE_AVAILABLE = False
    logger.warning(f"Layout detection service not available: {e}")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

router = APIRouter()

# Global state for tracking active detection jobs
_active_detection_jobs: Dict[int, Dict[str, Any]] = {}
_detection_websocket_connections: Dict[int, List[WebSocket]] = {}


# =============================================================================
# Pydantic Models
# =============================================================================

class DetectionConfig(BaseModel):
    """Configuration for layout detection."""
    start_page: int
    end_page: int
    enabled_classes: Optional[List[str]] = None
    confidence_threshold: Optional[float] = 0.25
    review_mode: Optional[str] = "n_pages"  # "n_pages" or "all_batches"
    review_n_pages: Optional[int] = 10
    batch_size: Optional[int] = 20


class RegionUpdate(BaseModel):
    """Update for a detected region."""
    class_name: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    review_status: Optional[str] = None
    l3_title_id: Optional[int] = None  # Link to L3 title region
    z_index: Optional[int] = None  # Z-order for overlapping regions (higher = on top)


class L3LinkRequest(BaseModel):
    """Request to link a region to an L3 title."""
    region_id: int
    l3_title_id: int


class RegionCreate(BaseModel):
    """Create a new region manually."""
    page_number: int
    class_name: str
    x: int
    y: int
    width: int
    height: int


class ConfirmRegionsRequest(BaseModel):
    """Request to confirm reviewed regions."""
    page_numbers: List[int]
    skip_ignored: Optional[bool] = False


class LinkRegionsRequest(BaseModel):
    """Request to link a diagram to a paragraph or answer to a question."""
    diagram_region_id: int  # Can be diagram/table/equation/list OR answer
    paragraph_region_id: int  # Can be paragraph OR question


class ConfirmPageRequest(BaseModel):
    """Request to confirm classes or regions for a single page."""
    page_number: int


class ReadyForExtractionRequest(BaseModel):
    """Request to set ready-for-extraction status."""
    page_number: int
    ready: bool


class FinalizeLayoutRequest(BaseModel):
    """Request to finalize and save layout to DB."""
    page_numbers: List[int]
    skip_ignored: Optional[bool] = True


class IgnoreRuleCreate(BaseModel):
    """Request to create an ignore rule."""
    class_name: str
    x: int
    y: int
    width: int
    height: int
    tolerance: Optional[int] = 50
    source_region_id: Optional[int] = None


class DetectionStatusResponse(BaseModel):
    """Response for detection status."""
    status: str
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    pages_processed: Optional[int] = None
    regions_detected: Optional[int] = None
    started_at: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_book_by_id(book_id: int):
    """Get book metadata by ID."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT * FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    finally:
        db.close()


def get_layout_detection_config(book_id: int) -> Dict[str, Any]:
    """Get layout detection config for a book."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT layout_detection_config FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        )
        row = result.fetchone()
        if row and row[0]:
            return row[0]
        return {}
    finally:
        db.close()


def save_layout_detection_config(book_id: int, config: Dict[str, Any]):
    """Save layout detection config for a book."""
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE books_metadata
                SET layout_detection_config = :config
                WHERE book_id = :book_id
            """),
            {"book_id": book_id, "config": json.dumps(config)}
        )
        db.commit()
    finally:
        db.close()


def get_page_image(book_id: int, page_number: int) -> Optional[bytes]:
    """Get raw page image data."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        return None

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_pages"

    db = SessionLocal()
    try:
        result = db.execute(
            text(f"""
                SELECT original_image_data, original_format
                FROM {table_name}
                WHERE page_number = :page_number
            """),
            {"page_number": page_number}
        )
        row = result.fetchone()
        if row:
            return row[0]
        return None
    finally:
        db.close()


async def broadcast_detection_progress(book_id: int, progress: Dict[str, Any]):
    """Broadcast detection progress to all connected WebSocket clients."""
    if book_id not in _detection_websocket_connections:
        return

    disconnected = []
    for ws in _detection_websocket_connections[book_id]:
        try:
            await ws.send_json(progress)
        except Exception:
            disconnected.append(ws)

    # Remove disconnected clients
    for ws in disconnected:
        _detection_websocket_connections[book_id].remove(ws)


def region_matches_ignore_rule(region: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """Check if a region matches an ignore rule."""
    tolerance = rule.get("tolerance", 50)

    # Must match class name
    if region.get("class_name") != rule.get("class_name"):
        return False

    # Check position within tolerance
    if abs(region.get("x", 0) - rule.get("x", 0)) > tolerance:
        return False
    if abs(region.get("y", 0) - rule.get("y", 0)) > tolerance:
        return False

    # Check size within tolerance
    if abs(region.get("width", 0) - rule.get("width", 0)) > tolerance:
        return False
    if abs(region.get("height", 0) - rule.get("height", 0)) > tolerance:
        return False

    return True


def filter_regions_by_ignore_rules(regions: List[Dict[str, Any]], ignore_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out regions that match any ignore rule."""
    if not ignore_rules:
        return regions

    filtered = []
    for region in regions:
        matches_rule = any(region_matches_ignore_rule(region, rule) for rule in ignore_rules)
        if not matches_rule:
            filtered.append(region)

    return filtered


def save_detection_results(book_id: int, results: List[Dict[str, Any]]):
    """Save detection results to the database, filtering by ignore rules."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        return

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    # Get ignore rules for this book
    config = get_layout_detection_config(book_id)
    ignore_rules = config.get("ignore_rules", [])

    db = SessionLocal()
    try:
        saved_count = 0
        ignored_count = 0

        for result in results:
            page_number = result["page_number"]

            # Filter regions by ignore rules
            original_regions = result["regions"]
            filtered_regions = filter_regions_by_ignore_rules(original_regions, ignore_rules)
            ignored_count += len(original_regions) - len(filtered_regions)

            for region in filtered_regions:
                db.execute(
                    text(f"""
                        INSERT INTO {table_name} (
                            page_number, class_name, class_id,
                            x, y, width, height, confidence,
                            model_version, review_status, created_at
                        ) VALUES (
                            :page_number, :class_name, :class_id,
                            :x, :y, :width, :height, :confidence,
                            :model_version, 'pending', NOW()
                        )
                    """),
                    {
                        "page_number": page_number,
                        "class_name": region["class_name"],
                        "class_id": region["class_id"],
                        "x": region["x"],
                        "y": region["y"],
                        "width": region["width"],
                        "height": region["height"],
                        "confidence": region["confidence"],
                        # model_version: 0 = base model, 1+ = fine-tuned versions
                        "model_version": 0 if result.get("model_version") in ("base", None) else int(result.get("model_version", 0))
                    }
                )
                saved_count += 1

        db.commit()
        logger.info(f"Saved {saved_count} detection results for book {book_id} (filtered out {ignored_count} by ignore rules)")
    except Exception as e:
        logger.error(f"Error saving detection results: {e}")
        db.rollback()
    finally:
        db.close()


# =============================================================================
# Detection Endpoints
# =============================================================================

@router.get("/api/layout-detection/status")
async def get_service_status():
    """Get layout detection service status."""
    model_exists, model_message = check_model_exists() if LAYOUT_SERVICE_AVAILABLE else (False, "Service not available")

    return {
        "service_available": LAYOUT_SERVICE_AVAILABLE,
        "model_exists": model_exists,
        "model_message": model_message,
        "gpu_available": layout_detection_service.device == "cuda" if LAYOUT_SERVICE_AVAILABLE else False,
        "model_loaded": layout_detection_service.is_loaded if LAYOUT_SERVICE_AVAILABLE else False
    }


@router.get("/api/layout-detection/classes")
async def get_available_classes():
    """Get available detection classes with their configuration."""
    if not LAYOUT_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Layout detection service not available")

    return {
        "classes": layout_detection_service.get_class_config()
    }


@router.post("/api/auto-slicer/{book_id}/detect-layout")
async def start_layout_detection(
    book_id: int,
    config: DetectionConfig,
    background_tasks: BackgroundTasks
):
    """
    Start layout detection for a book.

    This runs YOLO detection on the specified page range and stores
    results in the layout_detections table.
    """
    if not LAYOUT_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Layout detection service not available")

    # Check if book exists
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    # Check if detection is already running
    if book_id in _active_detection_jobs:
        job = _active_detection_jobs[book_id]
        if job.get("status") == "running":
            raise HTTPException(
                status_code=409,
                detail="Detection already in progress for this book"
            )

    # Initialize job state
    _active_detection_jobs[book_id] = {
        "status": "starting",
        "config": config.model_dump(),
        "started_at": datetime.now().isoformat(),
        "current_page": 0,
        "total_pages": config.end_page - config.start_page + 1,
        "pages_processed": 0,
        "regions_detected": 0
    }

    # Start detection in background
    background_tasks.add_task(
        run_layout_detection,
        book_id,
        config
    )

    return {
        "status": "started",
        "message": f"Layout detection started for pages {config.start_page}-{config.end_page}",
        "book_id": book_id
    }


async def run_layout_detection(book_id: int, config: DetectionConfig):
    """Background task to run layout detection."""
    try:
        # Update status
        _active_detection_jobs[book_id]["status"] = "loading_model"

        # Load model - GPU-Only, no CPU fallback
        if not layout_detection_service.is_loaded:
            success = layout_detection_service.load_model()
            if not success:
                # Get the specific GPU error message
                error_msg = layout_detection_service.gpu_error_message or "Failed to load model"
                _active_detection_jobs[book_id]["status"] = "error"
                _active_detection_jobs[book_id]["error"] = error_msg

                # Broadcast error to WebSocket clients
                await broadcast_detection_progress(book_id, {
                    "type": "detection_error",
                    "status": "error",
                    "error": error_msg,
                    "gpu_error": True
                })
                return

        # Configure enabled classes and save to config
        if config.enabled_classes:
            layout_detection_service.set_enabled_classes(config.enabled_classes)
            # Save enabled classes to book config for later use
            layout_config = get_layout_detection_config(book_id)
            layout_config["enabled_classes"] = config.enabled_classes
            layout_config["confidence_threshold"] = config.confidence_threshold or 0.25
            save_layout_detection_config(book_id, layout_config)

        if config.confidence_threshold:
            layout_detection_service.set_confidence_threshold(config.confidence_threshold)

        # Update status
        _active_detection_jobs[book_id]["status"] = "running"

        # Process pages
        results = []
        for page_num in range(config.start_page, config.end_page + 1):
            # Check for cancellation
            if _active_detection_jobs[book_id].get("cancelled"):
                _active_detection_jobs[book_id]["status"] = "cancelled"
                break

            try:
                # Get page image
                image_data = get_page_image(book_id, page_num)
                if not image_data:
                    logger.warning(f"No image found for page {page_num}")
                    continue

                # Convert to PIL Image
                image = Image.open(BytesIO(image_data))

                # Detect regions
                result = layout_detection_service.detect_single_page(image, page_num)
                results.append(result.to_dict())

                # Update progress
                _active_detection_jobs[book_id]["current_page"] = page_num
                _active_detection_jobs[book_id]["pages_processed"] += 1
                _active_detection_jobs[book_id]["regions_detected"] += len(result.regions)

                # Broadcast progress
                await broadcast_detection_progress(book_id, {
                    "type": "detection_progress",
                    "current_page": page_num,
                    "total_pages": _active_detection_jobs[book_id]["total_pages"],
                    "pages_processed": _active_detection_jobs[book_id]["pages_processed"],
                    "regions_detected": _active_detection_jobs[book_id]["regions_detected"],
                    "status": "processing"
                })

            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                continue

        # Save results to database
        if results:
            save_detection_results(book_id, results)

        # Unload model to free VRAM
        layout_detection_service.unload_model()

        # Update final status
        _active_detection_jobs[book_id]["status"] = "completed"
        _active_detection_jobs[book_id]["completed_at"] = datetime.now().isoformat()

        # Broadcast completion
        await broadcast_detection_progress(book_id, {
            "type": "detection_complete",
            "pages_processed": _active_detection_jobs[book_id]["pages_processed"],
            "regions_detected": _active_detection_jobs[book_id]["regions_detected"],
            "status": "completed"
        })

        logger.info(f"Layout detection completed for book {book_id}")

    except Exception as e:
        logger.error(f"Layout detection failed: {e}", exc_info=True)
        _active_detection_jobs[book_id]["status"] = "error"
        _active_detection_jobs[book_id]["error"] = str(e)

        # Ensure model is unloaded on error
        layout_detection_service.unload_model()


@router.get("/api/auto-slicer/{book_id}/layout-config")
async def get_layout_config(book_id: int):
    """Get the layout detection configuration for a book (including enabled classes)."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    config = get_layout_detection_config(book_id)
    return {
        "book_id": book_id,
        "enabled_classes": config.get("enabled_classes", []),
        "confidence_threshold": config.get("confidence_threshold", 0.25),
        "ignore_rules": config.get("ignore_rules", []),
        "page_confirmations": config.get("page_confirmations", {}),
        "ready_for_extraction": config.get("ready_for_extraction", {})
    }


class UpdateEnabledClassesRequest(BaseModel):
    """Request model for updating enabled classes."""
    enabled_classes: List[str]


@router.put("/api/auto-slicer/{book_id}/layout-config/enabled-classes")
async def update_enabled_classes(book_id: int, request: UpdateEnabledClassesRequest):
    """Update the enabled classes for layout detection without running detection."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get current config and update enabled classes
    config = get_layout_detection_config(book_id)
    config["enabled_classes"] = request.enabled_classes
    save_layout_detection_config(book_id, config)

    logger.info(f"Updated enabled classes for book {book_id}: {request.enabled_classes}")

    return {
        "success": True,
        "book_id": book_id,
        "enabled_classes": request.enabled_classes
    }


@router.get("/api/auto-slicer/{book_id}/detection-status")
async def get_detection_status(book_id: int):
    """Get the current detection status for a book."""
    if book_id not in _active_detection_jobs:
        return {"status": "idle", "message": "No detection job found"}

    job = _active_detection_jobs[book_id]
    return {
        "status": job.get("status", "unknown"),
        "current_page": job.get("current_page"),
        "total_pages": job.get("total_pages"),
        "pages_processed": job.get("pages_processed"),
        "regions_detected": job.get("regions_detected"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error": job.get("error")
    }


@router.post("/api/auto-slicer/{book_id}/cancel-detection")
async def cancel_detection(book_id: int):
    """Cancel an active detection job."""
    if book_id not in _active_detection_jobs:
        raise HTTPException(status_code=404, detail="No active detection job")

    job = _active_detection_jobs[book_id]
    if job.get("status") != "running":
        raise HTTPException(status_code=400, detail="Detection is not running")

    _active_detection_jobs[book_id]["cancelled"] = True
    return {"status": "cancelling", "message": "Detection will be cancelled"}


# =============================================================================
# Region Management Endpoints
# =============================================================================

@router.get("/api/auto-slicer/{book_id}/detected-regions")
async def get_detected_regions(
    book_id: int,
    page_number: Optional[int] = None,
    review_status: Optional[str] = None
):
    """Get detected regions for a book."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Build query
        query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = {}

        if page_number is not None:
            query += " AND page_number = :page_number"
            params["page_number"] = page_number

        if review_status:
            query += " AND review_status = :review_status"
            params["review_status"] = review_status

        query += " ORDER BY page_number, id"

        result = db.execute(text(query), params)
        rows = result.fetchall()

        regions = [dict(row._mapping) for row in rows]

        # Convert datetime objects to strings
        for region in regions:
            for key, value in region.items():
                if hasattr(value, 'isoformat'):
                    region[key] = value.isoformat()

        return {"regions": regions, "count": len(regions)}

    except Exception as e:
        logger.error(f"Error getting detected regions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/api/auto-slicer/{book_id}/detected-regions/{page_number}")
async def get_page_regions(book_id: int, page_number: int):
    """Get detected regions for a specific page."""
    return await get_detected_regions(book_id, page_number=page_number)


@router.put("/api/auto-slicer/{book_id}/detected-region/{region_id}")
async def update_region(book_id: int, region_id: int, update: RegionUpdate):
    """Update a detected region (for corrections)."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Get original values first
        result = db.execute(
            text(f"SELECT * FROM {table_name} WHERE id = :id"),
            {"id": region_id}
        )
        original = result.fetchone()
        if not original:
            raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

        original_dict = dict(original._mapping)

        # Build update query
        updates = []
        params = {"id": region_id}

        if update.class_name is not None:
            updates.append("class_name = :class_name")
            params["class_name"] = update.class_name
            # Store original if first correction
            if not original_dict.get("was_corrected"):
                updates.append("original_class = :original_class")
                params["original_class"] = original_dict["class_name"]

        if update.x is not None:
            updates.append("x = :x")
            params["x"] = update.x
            if not original_dict.get("was_corrected"):
                updates.append("original_x = :original_x")
                params["original_x"] = original_dict["x"]

        if update.y is not None:
            updates.append("y = :y")
            params["y"] = update.y
            if not original_dict.get("was_corrected"):
                updates.append("original_y = :original_y")
                params["original_y"] = original_dict["y"]

        if update.width is not None:
            updates.append("width = :width")
            params["width"] = update.width
            if not original_dict.get("was_corrected"):
                updates.append("original_width = :original_width")
                params["original_width"] = original_dict["width"]

        if update.height is not None:
            updates.append("height = :height")
            params["height"] = update.height
            if not original_dict.get("was_corrected"):
                updates.append("original_height = :original_height")
                params["original_height"] = original_dict["height"]

        if update.review_status is not None:
            updates.append("review_status = :review_status")
            params["review_status"] = update.review_status
            if update.review_status == "reviewed":
                updates.append("reviewed_at = NOW()")

        if update.z_index is not None:
            # Ensure z_index column exists
            try:
                db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS z_index INTEGER DEFAULT 0"))
                db.commit()
            except Exception:
                db.rollback()  # Column might already exist

            updates.append("z_index = :z_index")
            params["z_index"] = update.z_index

        # Handle l3_title_id update (can be set to None to unlink)
        if update.l3_title_id is not None or 'l3_title_id' in (update.model_dump() if hasattr(update, 'model_dump') else update.dict()):
            # Ensure l3_title_id column exists
            try:
                db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS l3_title_id INTEGER"))
                db.commit()
            except Exception:
                db.rollback()  # Column might already exist

            updates.append("l3_title_id = :l3_title_id")
            params["l3_title_id"] = update.l3_title_id

        # Mark as corrected
        if any([update.class_name, update.x, update.y, update.width, update.height]):
            updates.append("was_corrected = TRUE")
            updates.append("correction_type = :correction_type")
            params["correction_type"] = "manual_adjustment"
            updates.append("correction_timestamp = NOW()")

        updates.append("updated_at = NOW()")

        if updates:
            query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id"
            db.execute(text(query), params)
            db.commit()

        return {"status": "updated", "region_id": region_id}

    except Exception as e:
        logger.error(f"Error updating region: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/api/auto-slicer/{book_id}/detected-region/{region_id}")
async def delete_region(book_id: int, region_id: int):
    """Delete a detected region and its associated links."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # First, delete any links that reference this region (as diagram or paragraph)
        links_deleted = db.execute(
            text("""
                DELETE FROM layout_reference_links
                WHERE book_id = :book_id
                AND (diagram_id = :region_id OR paragraph_id = :region_id)
            """),
            {"book_id": book_id, "region_id": region_id}
        ).rowcount

        # Then delete the region itself
        result = db.execute(
            text(f"DELETE FROM {table_name} WHERE id = :id RETURNING id"),
            {"id": region_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Region {region_id} not found")

        db.commit()
        logger.info(f"Deleted region {region_id} and {links_deleted} associated links")
        return {"status": "deleted", "region_id": region_id, "links_deleted": links_deleted}

    except Exception as e:
        logger.error(f"Error deleting region: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/auto-slicer/{book_id}/add-region")
async def add_region(book_id: int, region: RegionCreate):
    """Add a new region manually."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    # Get class ID
    class_config = EXTENDED_CLASS_MAPPING.get(region.class_name, {})
    class_id = class_config.get("id", 0)

    db = SessionLocal()
    try:
        result = db.execute(
            text(f"""
                INSERT INTO {table_name} (
                    page_number, class_name, class_id,
                    x, y, width, height,
                    confidence, was_corrected, correction_type,
                    review_status, created_at
                ) VALUES (
                    :page_number, :class_name, :class_id,
                    :x, :y, :width, :height,
                    1.0, TRUE, 'manually_added',
                    'reviewed', NOW()
                ) RETURNING id
            """),
            {
                "page_number": region.page_number,
                "class_name": region.class_name,
                "class_id": class_id,
                "x": region.x,
                "y": region.y,
                "width": region.width,
                "height": region.height
            }
        )
        new_id = result.fetchone()[0]
        db.commit()

        return {"status": "created", "region_id": new_id}

    except Exception as e:
        logger.error(f"Error adding region: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/auto-slicer/{book_id}/confirm-regions")
async def confirm_regions(book_id: int, request: ConfirmRegionsRequest):
    """Mark regions on specified pages as reviewed."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    table_name = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Build query - optionally skip ignored regions
        if request.skip_ignored:
            result = db.execute(
                text(f"""
                    UPDATE {table_name}
                    SET review_status = 'reviewed', reviewed_at = NOW(), updated_at = NOW()
                    WHERE page_number = ANY(:page_numbers)
                    AND review_status = 'pending'
                    AND class_name != 'ignore'
                """),
                {"page_numbers": request.page_numbers}
            )
            # Delete ignored regions
            db.execute(
                text(f"""
                    DELETE FROM {table_name}
                    WHERE page_number = ANY(:page_numbers)
                    AND class_name = 'ignore'
                """),
                {"page_numbers": request.page_numbers}
            )
        else:
            result = db.execute(
                text(f"""
                    UPDATE {table_name}
                    SET review_status = 'reviewed', reviewed_at = NOW(), updated_at = NOW()
                    WHERE page_number = ANY(:page_numbers)
                    AND review_status = 'pending'
                """),
                {"page_numbers": request.page_numbers}
            )
        db.commit()

        return {
            "status": "confirmed",
            "pages": request.page_numbers,
            "regions_confirmed": result.rowcount
        }

    except Exception as e:
        logger.error(f"Error confirming regions: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Region Linking Endpoints (Diagram <-> Paragraph)
# =============================================================================

@router.get("/api/auto-slicer/{book_id}/region-links")
async def get_region_links(book_id: int):
    """Get all diagram-paragraph links for a book."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT id, diagram_id as diagram_region_id,
                       paragraph_id as paragraph_region_id,
                       reference_type as link_type, created_at
                FROM layout_reference_links
                WHERE book_id = :book_id
                ORDER BY created_at
            """),
            {"book_id": book_id}
        )
        rows = result.fetchall()

        links = []
        for row in rows:
            link = dict(row._mapping)
            # Convert datetime to string
            if link.get('created_at') and hasattr(link['created_at'], 'isoformat'):
                link['created_at'] = link['created_at'].isoformat()
            links.append(link)

        return {"links": links, "count": len(links)}

    except Exception as e:
        # Table might not exist yet
        logger.warning(f"Error getting region links: {e}")
        return {"links": [], "count": 0}
    finally:
        db.close()


@router.post("/api/auto-slicer/{book_id}/link-regions")
async def link_regions(book_id: int, request: LinkRegionsRequest):
    """Create a link between a diagram and a paragraph, or answer and question."""
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    detections_table = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Verify both regions exist and are the correct types
        source_region = db.execute(
            text(f"SELECT id, class_name FROM {detections_table} WHERE id = :id"),
            {"id": request.diagram_region_id}
        ).fetchone()

        target_region = db.execute(
            text(f"SELECT id, class_name FROM {detections_table} WHERE id = :id"),
            {"id": request.paragraph_region_id}
        ).fetchone()

        if not source_region:
            raise HTTPException(status_code=404, detail="Source region not found")
        if not target_region:
            raise HTTPException(status_code=404, detail="Target region not found")

        source_class = source_region[1]
        target_class = target_region[1]

        # Valid linking combinations:
        # 1. diagram/table/equation/list → paragraph
        # 2. answer → question
        linkable_to_paragraph = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered']

        if source_class == 'answer':
            # Answer must link to question
            if target_class != 'question':
                raise HTTPException(status_code=400, detail="Answer can only be linked to a question")
        elif source_class in linkable_to_paragraph:
            # Diagram/table/equation/list must link to paragraph
            if target_class != 'paragraph':
                raise HTTPException(status_code=400, detail=f"{source_class} can only be linked to a paragraph")
        else:
            raise HTTPException(status_code=400, detail=f"Region type '{source_class}' cannot be linked")

        # Check if link already exists
        existing = db.execute(
            text("""
                SELECT id FROM layout_reference_links
                WHERE book_id = :book_id
                AND diagram_id = :diagram_id
                AND paragraph_id = :paragraph_id
            """),
            {
                "book_id": book_id,
                "diagram_id": request.diagram_region_id,
                "paragraph_id": request.paragraph_region_id
            }
        ).fetchone()

        if existing:
            return {"status": "exists", "link_id": existing[0]}

        # Create the link
        result = db.execute(
            text("""
                INSERT INTO layout_reference_links (
                    book_id, diagram_id, paragraph_id,
                    reference_type, detection_method, created_at
                ) VALUES (
                    :book_id, :diagram_id, :paragraph_id,
                    'reference', 'manual', NOW()
                ) RETURNING id
            """),
            {
                "book_id": book_id,
                "diagram_id": request.diagram_region_id,
                "paragraph_id": request.paragraph_region_id
            }
        )
        link_id = result.fetchone()[0]
        db.commit()

        return {"status": "created", "link_id": link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating link: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/api/auto-slicer/{book_id}/unlink-regions/{link_id}")
async def unlink_regions(book_id: int, link_id: int):
    """Remove a link between a diagram and a paragraph."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                DELETE FROM layout_reference_links
                WHERE id = :id AND book_id = :book_id
                RETURNING id
            """),
            {"id": link_id, "book_id": book_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Link {link_id} not found")

        db.commit()
        return {"status": "deleted", "link_id": link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing link: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/auto-slicer/{book_id}/l3-link")
async def link_to_l3_title(book_id: int, request: L3LinkRequest):
    """Link a region to an L3 title region.

    This stores the l3_title_id on the region, linking content
    regions to their parent L3 (section) titles.
    """
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    detections_table = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Verify the L3 title region exists and is title_level_3
        l3_region = db.execute(
            text(f"SELECT id, class_name FROM {detections_table} WHERE id = :id"),
            {"id": request.l3_title_id}
        ).fetchone()

        if not l3_region:
            raise HTTPException(status_code=404, detail="L3 title region not found")
        # Accept both title_level_3 and title_l3 variations
        valid_l3_classes = ['title_level_3', 'title_l3', 'Title L3']
        if l3_region[1] not in valid_l3_classes:
            raise HTTPException(status_code=400, detail="Target region must be a Title L3")

        # Verify the source region exists
        source_region = db.execute(
            text(f"SELECT id FROM {detections_table} WHERE id = :id"),
            {"id": request.region_id}
        ).fetchone()

        if not source_region:
            raise HTTPException(status_code=404, detail="Source region not found")

        # Update the region with l3_title_id
        # First check if the column exists, if not create it
        try:
            db.execute(
                text(f"""
                    ALTER TABLE {detections_table}
                    ADD COLUMN IF NOT EXISTS l3_title_id INTEGER
                """)
            )
            db.commit()
        except Exception:
            db.rollback()
            # Column might already exist, continue

        # Set the l3_title_id on the region
        db.execute(
            text(f"""
                UPDATE {detections_table}
                SET l3_title_id = :l3_title_id
                WHERE id = :region_id
            """),
            {"l3_title_id": request.l3_title_id, "region_id": request.region_id}
        )
        db.commit()

        return {"status": "linked", "region_id": request.region_id, "l3_title_id": request.l3_title_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating L3 link: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Page Confirmation Endpoints
# =============================================================================

def get_page_confirmations(book_id: int) -> Dict[int, Dict[str, bool]]:
    """Get page confirmation status from book config."""
    config = get_layout_detection_config(book_id)
    return config.get("page_confirmations", {})


def set_page_confirmation(book_id: int, page_number: int, confirm_type: str):
    """Set page confirmation status in book config."""
    config = get_layout_detection_config(book_id)
    if "page_confirmations" not in config:
        config["page_confirmations"] = {}

    page_key = str(page_number)  # JSON keys must be strings
    if page_key not in config["page_confirmations"]:
        config["page_confirmations"][page_key] = {}

    config["page_confirmations"][page_key][confirm_type] = True
    save_layout_detection_config(book_id, config)


@router.post("/api/auto-slicer/{book_id}/confirm-page-classes")
async def confirm_page_classes(book_id: int, request: ConfirmPageRequest):
    """Confirm that classes on a page have been reviewed."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    set_page_confirmation(book_id, request.page_number, "classes_confirmed")

    return {
        "status": "confirmed",
        "page_number": request.page_number,
        "confirmation_type": "classes"
    }


@router.post("/api/auto-slicer/{book_id}/confirm-page-regions")
async def confirm_page_regions(book_id: int, request: ConfirmPageRequest):
    """Confirm that region boundaries on a page have been reviewed."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    set_page_confirmation(book_id, request.page_number, "regions_confirmed")

    return {
        "status": "confirmed",
        "page_number": request.page_number,
        "confirmation_type": "regions"
    }


@router.get("/api/auto-slicer/{book_id}/page-confirmations")
async def get_all_page_confirmations(book_id: int):
    """Get confirmation status for all pages."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    confirmations = get_page_confirmations(book_id)
    return {"confirmations": confirmations}


@router.post("/api/auto-slicer/{book_id}/set-ready-for-extraction")
async def set_ready_for_extraction(book_id: int, request: ReadyForExtractionRequest):
    """Set ready-for-extraction status for a page."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    config = get_layout_detection_config(book_id)
    if "ready_for_extraction" not in config:
        config["ready_for_extraction"] = {}

    page_key = str(request.page_number)
    config["ready_for_extraction"][page_key] = request.ready
    save_layout_detection_config(book_id, config)

    return {
        "status": "updated",
        "page_number": request.page_number,
        "ready": request.ready
    }


@router.get("/api/auto-slicer/{book_id}/page-status/{page_number}")
async def get_page_status(book_id: int, page_number: int):
    """Get status for a specific page (confirmations, ready for extraction)."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    config = get_layout_detection_config(book_id)
    confirmations = config.get("page_confirmations", {})
    ready_for_extraction = config.get("ready_for_extraction", {})

    page_key = str(page_number)
    page_conf = confirmations.get(page_key, {})

    return {
        "page_number": page_number,
        "classes_confirmed": page_conf.get("classes_confirmed", False),
        "regions_confirmed": page_conf.get("regions_confirmed", False),
        "ready_for_extraction": ready_for_extraction.get(page_key, False)
    }


@router.post("/api/auto-slicer/{book_id}/finalize-layout")
async def finalize_layout(book_id: int, request: FinalizeLayoutRequest):
    """
    Finalize layout detection - save confirmed regions to the actual
    paragraphs and diagrams tables.

    Only pages where BOTH classes AND regions are confirmed will be processed.
    Regions with class 'ignore' will be deleted.
    """
    book = get_book_by_id(book_id)
    if not book or not book.get("table_prefix"):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    table_prefix = book["table_prefix"]
    detections_table = f"raw_{table_prefix}_layout_detections"

    # Get confirmation status
    confirmations = get_page_confirmations(book_id)

    # Filter to only fully confirmed pages
    fully_confirmed = []
    for page in request.page_numbers:
        page_conf = confirmations.get(str(page), {})
        if page_conf.get("classes_confirmed") and page_conf.get("regions_confirmed"):
            fully_confirmed.append(page)

    if not fully_confirmed:
        raise HTTPException(
            status_code=400,
            detail="No pages are fully confirmed. Confirm both classes and regions first."
        )

    db = SessionLocal()
    try:
        processed_count = 0
        ignored_count = 0

        for page_number in fully_confirmed:
            # Delete ignored regions
            if request.skip_ignored:
                result = db.execute(
                    text(f"""
                        DELETE FROM {detections_table}
                        WHERE page_number = :page_number
                        AND class_name = 'ignore'
                    """),
                    {"page_number": page_number}
                )
                ignored_count += result.rowcount

            # Mark remaining regions as finalized
            result = db.execute(
                text(f"""
                    UPDATE {detections_table}
                    SET review_status = 'finalized',
                        reviewed_at = NOW(),
                        updated_at = NOW()
                    WHERE page_number = :page_number
                    AND review_status != 'finalized'
                """),
                {"page_number": page_number}
            )
            processed_count += result.rowcount

        db.commit()

        return {
            "status": "finalized",
            "pages_processed": len(fully_confirmed),
            "regions_finalized": processed_count,
            "ignored_deleted": ignored_count,
            "fully_confirmed_pages": fully_confirmed
        }

    except Exception as e:
        logger.error(f"Error finalizing layout: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws/layout-detection/{book_id}")
async def websocket_detection_progress(websocket: WebSocket, book_id: int):
    """WebSocket endpoint for real-time detection progress updates."""
    await websocket.accept()

    # Add to connections
    if book_id not in _detection_websocket_connections:
        _detection_websocket_connections[book_id] = []
    _detection_websocket_connections[book_id].append(websocket)

    try:
        # Send initial status
        if book_id in _active_detection_jobs:
            job = _active_detection_jobs[book_id]
            await websocket.send_json({
                "type": "initial_status",
                "status": job.get("status"),
                "current_page": job.get("current_page"),
                "total_pages": job.get("total_pages"),
                "pages_processed": job.get("pages_processed"),
                "regions_detected": job.get("regions_detected")
            })

        # Keep connection alive
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                # Handle ping/pong or other messages
                if message == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for book {book_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove from connections
        if book_id in _detection_websocket_connections:
            if websocket in _detection_websocket_connections[book_id]:
                _detection_websocket_connections[book_id].remove(websocket)


# =============================================================================
# Ignore Rules Endpoints
# =============================================================================

@router.post("/api/auto-slicer/{book_id}/ignore-rules")
async def create_ignore_rule(book_id: int, rule: IgnoreRuleCreate):
    """
    Create an ignore rule for similar regions.

    This will:
    1. Store the ignore rule in the book's configuration
    2. Delete the source region
    3. Delete all matching regions (same class, position within tolerance)
    4. Return the count of deleted regions
    """
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    table_prefix = book.get("table_prefix")
    if not table_prefix:
        raise HTTPException(status_code=400, detail="Book has no table prefix")

    detections_table = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Get current config
        config = get_layout_detection_config(book_id)
        if "ignore_rules" not in config:
            config["ignore_rules"] = []

        # Create the rule
        new_rule = {
            "id": len(config["ignore_rules"]) + 1,
            "class_name": rule.class_name,
            "x": rule.x,
            "y": rule.y,
            "width": rule.width,
            "height": rule.height,
            "tolerance": rule.tolerance,
            "created_at": datetime.now().isoformat()
        }
        config["ignore_rules"].append(new_rule)

        # Find matching regions to delete
        tolerance = rule.tolerance
        result = db.execute(
            text(f"""
                SELECT id FROM {detections_table}
                WHERE class_name = :class_name
                AND ABS(x - :x) <= :tolerance
                AND ABS(y - :y) <= :tolerance
                AND ABS(width - :width) <= :tolerance
                AND ABS(height - :height) <= :tolerance
            """),
            {
                "class_name": rule.class_name,
                "x": rule.x,
                "y": rule.y,
                "width": rule.width,
                "height": rule.height,
                "tolerance": tolerance
            }
        )
        matching_ids = [row[0] for row in result.fetchall()]

        # Delete matching regions
        if matching_ids:
            db.execute(
                text(f"""
                    DELETE FROM {detections_table}
                    WHERE id = ANY(:ids)
                """),
                {"ids": matching_ids}
            )

        db.commit()

        # Save updated config
        save_layout_detection_config(book_id, config)

        return {
            "status": "created",
            "rule_id": new_rule["id"],
            "deleted_count": len(matching_ids),
            "deleted_region_ids": matching_ids
        }

    except Exception as e:
        logger.error(f"Error creating ignore rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/api/auto-slicer/{book_id}/ignore-rules")
async def get_ignore_rules(book_id: int):
    """Get all ignore rules for a book."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    config = get_layout_detection_config(book_id)
    rules = config.get("ignore_rules", [])

    return {
        "book_id": book_id,
        "rules": rules,
        "count": len(rules)
    }


@router.delete("/api/auto-slicer/{book_id}/ignore-rules/{rule_id}")
async def delete_ignore_rule(book_id: int, rule_id: int):
    """Delete an ignore rule by ID."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    config = get_layout_detection_config(book_id)
    rules = config.get("ignore_rules", [])

    # Find and remove the rule
    original_count = len(rules)
    config["ignore_rules"] = [r for r in rules if r.get("id") != rule_id]

    if len(config["ignore_rules"]) == original_count:
        raise HTTPException(status_code=404, detail="Ignore rule not found")

    save_layout_detection_config(book_id, config)

    return {
        "status": "deleted",
        "rule_id": rule_id
    }


@router.delete("/api/auto-slicer/{book_id}/page-detections/{page_number}")
async def delete_page_detections(book_id: int, page_number: int):
    """Delete all layout detections for a specific page."""
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    table_prefix = book.get("table_prefix")
    if not table_prefix:
        raise HTTPException(status_code=400, detail="Book has no table prefix")

    detections_table = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        result = db.execute(
            text(f"""
                DELETE FROM {detections_table}
                WHERE page_number = :page_number
            """),
            {"page_number": page_number}
        )
        deleted_count = result.rowcount
        db.commit()

        return {
            "status": "deleted",
            "page_number": page_number,
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Error deleting page detections: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/auto-slicer/{book_id}/reset-page-regions/{page_number}")
async def reset_page_regions(book_id: int, page_number: int):
    """
    Reset regions for a specific page: delete all existing regions and re-run layout detection.
    
    This is useful when the user wants to start fresh with layout detection on a page
    after making manual corrections that didn't work out.
    """
    if not LAYOUT_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Layout detection service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    table_prefix = book.get("table_prefix")
    if not table_prefix:
        raise HTTPException(status_code=400, detail="Book has no table prefix")

    detections_table = f"raw_{table_prefix}_layout_detections"

    db = SessionLocal()
    try:
        # Step 1: Delete all existing regions for this page
        delete_result = db.execute(
            text(f"""
                DELETE FROM {detections_table}
                WHERE page_number = :page_number
            """),
            {"page_number": page_number}
        )
        deleted_count = delete_result.rowcount
        
        # Also delete any links involving regions on this page
        # First get region IDs that were on this page (they're deleted now, but links reference them)
        db.execute(
            text("""
                DELETE FROM layout_reference_links
                WHERE book_id = :book_id
                AND (diagram_id IN (
                    SELECT id FROM layout_reference_links WHERE book_id = :book_id
                ) OR paragraph_id IN (
                    SELECT id FROM layout_reference_links WHERE book_id = :book_id
                ))
            """),
            {"book_id": book_id}
        )
        
        db.commit()
        logger.info(f"Deleted {deleted_count} regions from page {page_number} of book {book_id}")

        # Step 2: Re-run layout detection for this single page
        # Load model if not loaded
        if not layout_detection_service.is_loaded:
            success = layout_detection_service.load_model()
            if not success:
                error_msg = layout_detection_service.gpu_error_message or "Failed to load model"
                raise HTTPException(status_code=503, detail=f"GPU Error: {error_msg}")

        # Get layout config for enabled classes and confidence threshold
        config = get_layout_detection_config(book_id)
        enabled_classes = config.get("enabled_classes", [])
        confidence_threshold = config.get("confidence_threshold", 0.25)
        
        if enabled_classes:
            layout_detection_service.set_enabled_classes(enabled_classes)
        if confidence_threshold:
            layout_detection_service.set_confidence_threshold(confidence_threshold)

        # Get page image
        image_data = get_page_image(book_id, page_number)
        if not image_data:
            raise HTTPException(status_code=404, detail=f"Page {page_number} image not found")

        # Convert to PIL Image
        if not PIL_AVAILABLE:
            raise HTTPException(status_code=503, detail="PIL not available")
        
        image = Image.open(BytesIO(image_data))

        # Detect regions
        result = layout_detection_service.detect_single_page(image, page_number)
        
        # Save new detection results
        save_detection_results(book_id, [result.to_dict()])
        
        # Unload model to free VRAM
        layout_detection_service.unload_model()
        
        # Clear page confirmation status since we re-detected
        if "page_confirmations" in config:
            page_key = str(page_number)
            if page_key in config["page_confirmations"]:
                del config["page_confirmations"][page_key]
        if "ready_for_extraction" in config:
            page_key = str(page_number)
            if page_key in config["ready_for_extraction"]:
                del config["ready_for_extraction"][page_key]
        save_layout_detection_config(book_id, config)

        return {
            "status": "reset_complete",
            "page_number": page_number,
            "deleted_count": deleted_count,
            "new_regions_count": len(result.regions),
            "message": f"Deleted {deleted_count} old regions, detected {len(result.regions)} new regions"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting page regions: {e}", exc_info=True)
        db.rollback()
        # Ensure model is unloaded on error
        if LAYOUT_SERVICE_AVAILABLE:
            layout_detection_service.unload_model()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# YOLO Training Endpoints (Requirement 7C)
# =============================================================================

# Import training service
try:
    from src.services.yolo_training_service import get_yolo_training_service
    TRAINING_SERVICE_AVAILABLE = True
except ImportError as e:
    TRAINING_SERVICE_AVAILABLE = False
    logger.warning(f"YOLO training service not available: {e}")


class TrainingConfig(BaseModel):
    """Configuration for YOLO training."""
    epochs: int = 50
    batch_size: int = 8
    learning_rate: float = 0.001
    auto_backup: bool = True
    background: bool = True


@router.get("/api/auto-slicer/{book_id}/training/statistics")
async def get_training_statistics(book_id: int):
    """
    Get statistics about user corrections for YOLO training.
    
    Returns correction counts, class distribution, and training readiness.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        stats = service.get_correction_statistics()
        return {"success": True, "book_id": book_id, **stats}
    except Exception as e:
        logger.error(f"Error getting training statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/auto-slicer/{book_id}/training/export")
async def export_training_data(book_id: int):
    """
    Export training data in YOLO format.
    
    Creates images/ and labels/ folders with YOLO-format annotations.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        result = service.export_training_data()
        return result
    except Exception as e:
        logger.error(f"Error exporting training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/auto-slicer/{book_id}/training/backup")
async def backup_model(book_id: int):
    """
    Backup the current YOLO model before training.
    
    Creates a timestamped backup in models/backups/
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        result = service.backup_current_model()
        return result
    except Exception as e:
        logger.error(f"Error backing up model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/auto-slicer/{book_id}/training/backups")
async def list_model_backups(book_id: int):
    """List all available model backups."""
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        backups = service.list_backups()
        return {"success": True, "backups": backups}
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/auto-slicer/{book_id}/training/start")
async def start_training(book_id: int, config: TrainingConfig):
    """
    Start YOLO fine-tuning training.
    
    By default runs in background mode and returns a job ID.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        result = service.start_training(
            epochs=config.epochs,
            batch_size=config.batch_size,
            learning_rate=config.learning_rate,
            auto_backup=config.auto_backup,
            background=config.background
        )
        return result
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/auto-slicer/{book_id}/training/progress/{job_id}")
async def get_training_progress(book_id: int, job_id: str):
    """Get progress of a training job."""
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        result = service.get_training_progress(job_id)
        return result
    except Exception as e:
        logger.error(f"Error getting training progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/auto-slicer/{book_id}/training/jobs")
async def list_training_jobs(book_id: int):
    """List all training jobs for this book."""
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        jobs = service.list_training_jobs()
        return {"success": True, "jobs": jobs}
    except Exception as e:
        logger.error(f"Error listing training jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# YOLO Model Management Endpoints (Requirement 8)
# =============================================================================

@router.get("/api/books/{book_id}/yolo-model")
async def get_book_yolo_model(book_id: int):
    """
    Get YOLO model info for a book.
    
    Returns model type (global/book_specific), path, existence, size, training date.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        return service.get_book_model_info()
    except Exception as e:
        logger.error(f"Error getting YOLO model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SetYoloModelRequest(BaseModel):
    """Request to set YOLO model type for a book."""
    model_type: str  # "global" or "book_specific"


@router.put("/api/books/{book_id}/yolo-model")
async def set_book_yolo_model(book_id: int, request: SetYoloModelRequest):
    """
    Set YOLO model for a book.
    
    model_type: "global" to use global model, "book_specific" to use book's trained model.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        
        if request.model_type == "global":
            # Set to None to use global model
            service.set_book_model_path(None)
            return {
                "success": True,
                "model_type": "global",
                "model_path": None
            }
        elif request.model_type == "book_specific":
            # Check if book has a trained model
            from pathlib import Path
            book_model_path = Path("models/layout_detection") / f"book_{book_id}_yolo.pt"
            
            if not book_model_path.exists():
                raise HTTPException(
                    status_code=400, 
                    detail="No trained model found for this book. Train a model first."
                )
            
            service.set_book_model_path(str(book_model_path))
            return {
                "success": True,
                "model_type": "book_specific",
                "model_path": str(book_model_path)
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid model_type. Use 'global' or 'book_specific'.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting YOLO model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CopyYoloModelRequest(BaseModel):
    """Request to copy another book's YOLO model."""
    source_book_id: int


@router.post("/api/books/{book_id}/copy-yolo-model")
async def copy_yolo_model(book_id: int, request: CopyYoloModelRequest):
    """
    Copy another book's YOLO model to use for this book.
    
    Creates an independent copy of the source book's model.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check source book exists
    source_book = get_book_by_id(request.source_book_id)
    if not source_book:
        raise HTTPException(status_code=404, detail="Source book not found")
    
    try:
        service = get_yolo_training_service(book_id)
        result = service.copy_model_from_book(request.source_book_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying YOLO model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/yolo-models/books")
async def get_books_with_yolo_models_endpoint():
    """
    List all books that have trained YOLO models.
    
    Used for the "Copy from another book" modal.
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    try:
        from src.services.yolo_training_service import get_books_with_yolo_models
        books = get_books_with_yolo_models()
        return {"books": books}
    except Exception as e:
        logger.error(f"Error getting books with YOLO models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/books/{book_id}/use-trained-model")
async def use_trained_model(book_id: int):
    """
    Set the book to use its trained model after training completes.
    
    Called from the post-training prompt when user confirms "Use this model".
    """
    if not TRAINING_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Training service not available")
    
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        from pathlib import Path
        book_model_path = Path("models/layout_detection") / f"book_{book_id}_yolo.pt"
        
        if not book_model_path.exists():
            raise HTTPException(
                status_code=400, 
                detail="No trained model found for this book"
            )
        
        service = get_yolo_training_service(book_id)
        service.set_book_model_path(str(book_model_path))
        
        return {
            "success": True,
            "message": "Book now using its trained model",
            "model_path": str(book_model_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting trained model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
