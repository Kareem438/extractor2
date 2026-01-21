"""
Auto-Slicer API Routes

Provides endpoints for the Auto-slicer feature which bulk-processes
book pages using Surya OCR at 600 DPI.

Features:
- Configuration management (page ranges, titles, batches, OCR boundaries)
- Execution with pause/resume/cancel support
- WebSocket progress updates
- Failed page retry

Author: Claude Code
Date: 2026-01-12
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.utils.logging_config import logger
import json
import asyncio

router = APIRouter()

# Global state for tracking active auto-slicer jobs
_active_jobs: Dict[int, Dict[str, Any]] = {}
_websocket_connections: Dict[int, List[WebSocket]] = {}


# =============================================================================
# Pydantic Models
# =============================================================================

class TitleConfig(BaseModel):
    """Single title configuration."""
    title: str
    start_page: int
    end_page: int


class RectangleConfig(BaseModel):
    """Single OCR rectangle configuration."""
    label: str
    x: int
    y: int
    width: int
    height: int
    target: str  # 'text_content' or 'attr31'-'attr80'


class OCRBoundaryConfig(BaseModel):
    """OCR boundary configuration for a page range."""
    start_page: int
    end_page: int
    rectangles: List[RectangleConfig]


class BatchConfig(BaseModel):
    """Batch configuration for processing."""
    start_page: int
    end_page: int


class AutoSlicerConfig(BaseModel):
    """Full Auto-slicer configuration."""
    page_range: Optional[Dict[str, int]] = None  # {"start": 1, "end": 100}
    titles: Optional[Dict[str, List[TitleConfig]]] = None  # {"level1": [...], "level2": [...], "level3": [...]}
    batches: Optional[List[BatchConfig]] = None
    ocr_boundaries: Optional[List[OCRBoundaryConfig]] = None


class ExecutionState(BaseModel):
    """Execution state for pause/resume."""
    status: str  # 'idle', 'running', 'paused', 'completed', 'cancelled', 'error'
    last_completed_page: Optional[int] = None
    current_batch_index: Optional[int] = None
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    error_message: Optional[str] = None


class LastRunResult(BaseModel):
    """Last run results."""
    timestamp: str
    pages_processed: int
    pages_failed: int
    failed_pages: List[int]


# =============================================================================
# Helper Functions
# =============================================================================

def get_book_by_id(book_id: int):
    """Get book metadata by ID."""
    db = SessionLocal()
    try:
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        return book
    finally:
        db.close()


def get_auto_slicer_config(book_id: int) -> Optional[Dict]:
    """Get auto_slicer_config from books_metadata."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).first()

        if result and result[0]:
            return result[0]
        return None
    finally:
        db.close()


def save_auto_slicer_config(book_id: int, config: Dict) -> bool:
    """Save auto_slicer_config to books_metadata."""
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE books_metadata SET auto_slicer_config = :config WHERE book_id = :book_id"),
            {"book_id": book_id, "config": json.dumps(config)}
        )
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save auto_slicer_config: {e}")
        return False
    finally:
        db.close()


def is_job_running() -> Optional[int]:
    """Check if any auto-slicer job is running. Returns book_id or None."""
    for book_id, job in _active_jobs.items():
        if job.get('status') in ['running', 'paused']:
            return book_id
    return None


async def broadcast_progress(book_id: int, message: Dict):
    """Broadcast progress to all WebSocket connections for a book."""
    if book_id in _websocket_connections:
        dead_connections = []
        for ws in _websocket_connections[book_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        # Remove dead connections
        for ws in dead_connections:
            _websocket_connections[book_id].remove(ws)


# =============================================================================
# Configuration Endpoints
# =============================================================================

@router.get("/auto-slicer/{book_id}/config")
async def get_config(book_id: int):
    """
    Get Auto-slicer configuration for a book.

    Returns the saved configuration including:
    - Page range
    - Title configuration (3 levels)
    - Batch configuration
    - OCR boundaries with rectangles
    - Execution state
    - Last run results
    """
    # Validate book exists
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get config
    config = get_auto_slicer_config(book_id)

    return {
        "book_id": book_id,
        "book_name": book.book_name,
        "total_pages": book.total_pages,
        "config": config or {},
        "has_config": config is not None
    }


@router.post("/auto-slicer/{book_id}/config")
async def save_config(book_id: int, config: AutoSlicerConfig):
    """
    Save Auto-slicer configuration for a book.

    Saves:
    - Page range (start/end)
    - Title configuration (3 levels with page ranges)
    - Batch configuration (optional)
    - OCR boundaries with multiple rectangles
    """
    # Validate book exists
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get existing config to preserve execution_state and last_run
    existing = get_auto_slicer_config(book_id) or {}

    # Build new config
    new_config = {
        "page_range": config.page_range,
        "titles": {
            "level1": [t.dict() for t in config.titles.get("level1", [])] if config.titles else [],
            "level2": [t.dict() for t in config.titles.get("level2", [])] if config.titles else [],
            "level3": [t.dict() for t in config.titles.get("level3", [])] if config.titles else []
        } if config.titles else existing.get("titles"),
        "batches": [b.dict() for b in config.batches] if config.batches else existing.get("batches"),
        "ocr_boundaries": [
            {
                "start_page": b.start_page,
                "end_page": b.end_page,
                "rectangles": [r.dict() for r in b.rectangles]
            }
            for b in config.ocr_boundaries
        ] if config.ocr_boundaries else existing.get("ocr_boundaries"),
        "execution_state": existing.get("execution_state"),
        "last_run": existing.get("last_run")
    }

    # Save
    if save_auto_slicer_config(book_id, new_config):
        return {
            "success": True,
            "message": "Configuration saved",
            "book_id": book_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save configuration")


# =============================================================================
# Execution Endpoints
# =============================================================================

@router.post("/auto-slicer/{book_id}/run")
async def start_execution(book_id: int):
    """
    Start Auto-slicer execution for a book.

    - Validates configuration exists
    - Checks no other job is running
    - Starts processing in background
    - Returns immediately with job status
    """
    # Check if another job is running
    running_book = is_job_running()
    if running_book and running_book != book_id:
        raise HTTPException(
            status_code=409,
            detail=f"Another Auto-slicer job is already running on book {running_book}"
        )

    # Validate book exists
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get config
    config = get_auto_slicer_config(book_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found. Please configure Auto-slicer first.")

    # Validate config has required fields
    if not config.get("page_range"):
        raise HTTPException(status_code=400, detail="Page range not configured")

    titles = config.get("titles", {})
    has_titles = any([
        len(titles.get("level1", [])) > 0,
        len(titles.get("level2", [])) > 0,
        len(titles.get("level3", [])) > 0
    ])
    if not has_titles:
        raise HTTPException(status_code=400, detail="At least one title must be configured")

    # Check if resuming from paused state
    execution_state = config.get("execution_state") or {}
    resume_from = None
    if execution_state.get("status") == "paused":
        resume_from = execution_state.get("last_completed_page", 0)

    # Start the job
    from datetime import datetime

    _active_jobs[book_id] = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "current_page": resume_from or config["page_range"]["start"],
        "total_pages": config["page_range"]["end"] - config["page_range"]["start"] + 1,
        "pages_processed": 0,
        "pages_failed": 0,
        "failed_pages": [],
        "cancel_requested": False,
        "pause_requested": False
    }

    # Update execution state in DB
    config["execution_state"] = {
        "status": "running",
        "last_completed_page": resume_from,
        "started_at": _active_jobs[book_id]["started_at"]
    }
    save_auto_slicer_config(book_id, config)

    # Start background processing
    asyncio.create_task(run_auto_slicer_job(book_id))

    return {
        "success": True,
        "message": "Auto-slicer started" if not resume_from else f"Auto-slicer resumed from page {resume_from}",
        "book_id": book_id,
        "status": "running"
    }


@router.get("/auto-slicer/{book_id}/status")
async def get_status(book_id: int):
    """
    Get current Auto-slicer execution status.

    Returns:
    - Current status (idle, running, paused, completed, error)
    - Progress information
    - Failed pages list
    """
    # Get from active jobs first
    if book_id in _active_jobs:
        job = _active_jobs[book_id]
        return {
            "book_id": book_id,
            "status": job["status"],
            "current_page": job.get("current_page"),
            "total_pages": job.get("total_pages"),
            "pages_processed": job.get("pages_processed", 0),
            "pages_failed": job.get("pages_failed", 0),
            "failed_pages": job.get("failed_pages", []),
            "started_at": job.get("started_at"),
            "paused_at": job.get("paused_at")
        }

    # Otherwise get from DB
    config = get_auto_slicer_config(book_id)
    if not config:
        return {
            "book_id": book_id,
            "status": "idle",
            "message": "No configuration found"
        }

    execution_state = config.get("execution_state") or {}
    last_run = config.get("last_run") or {}

    return {
        "book_id": book_id,
        "status": execution_state.get("status", "idle"),
        "last_completed_page": execution_state.get("last_completed_page"),
        "last_run": last_run
    }


@router.post("/auto-slicer/{book_id}/pause")
async def pause_execution(book_id: int):
    """
    Pause Auto-slicer execution.

    - Saves current progress to DB
    - Can be resumed later
    """
    if book_id not in _active_jobs:
        raise HTTPException(status_code=400, detail="No active job for this book")

    job = _active_jobs[book_id]
    if job["status"] != "running":
        raise HTTPException(status_code=400, detail=f"Job is not running (status: {job['status']})")

    # Request pause
    job["pause_requested"] = True

    return {
        "success": True,
        "message": "Pause requested. Job will pause after current page completes.",
        "book_id": book_id
    }


@router.post("/auto-slicer/{book_id}/resume")
async def resume_execution(book_id: int):
    """
    Resume paused Auto-slicer execution.

    - Continues from last completed page
    """
    config = get_auto_slicer_config(book_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")

    execution_state = config.get("execution_state", {})
    if execution_state.get("status") != "paused":
        raise HTTPException(status_code=400, detail="Job is not paused")

    # Use the run endpoint which handles resume
    return await start_execution(book_id)


@router.post("/auto-slicer/{book_id}/cancel")
async def cancel_execution(book_id: int):
    """
    Cancel Auto-slicer execution.

    - Stops processing immediately
    - Keeps completed work
    """
    if book_id not in _active_jobs:
        raise HTTPException(status_code=400, detail="No active job for this book")

    job = _active_jobs[book_id]
    if job["status"] not in ["running", "paused"]:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled (status: {job['status']})")

    # Request cancel
    job["cancel_requested"] = True

    # If paused, update status immediately
    if job["status"] == "paused":
        job["status"] = "cancelled"

        # Update DB
        config = get_auto_slicer_config(book_id)
        if config:
            config["execution_state"]["status"] = "cancelled"
            save_auto_slicer_config(book_id, config)

    return {
        "success": True,
        "message": "Cancel requested. Job will stop after current page.",
        "book_id": book_id
    }


@router.post("/auto-slicer/{book_id}/retry")
async def retry_failed_pages(book_id: int):
    """
    Retry processing failed pages.

    - Gets list of failed pages from last run
    - Processes only those pages
    """
    config = get_auto_slicer_config(book_id)
    if not config:
        raise HTTPException(status_code=400, detail="No configuration found")

    last_run = config.get("last_run", {})
    failed_pages = last_run.get("failed_pages", [])

    if not failed_pages:
        raise HTTPException(status_code=400, detail="No failed pages to retry")

    # Check if another job is running
    running_book = is_job_running()
    if running_book:
        raise HTTPException(
            status_code=409,
            detail=f"Another Auto-slicer job is already running on book {running_book}"
        )

    # Start retry job
    from datetime import datetime

    _active_jobs[book_id] = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "current_page": failed_pages[0],
        "retry_pages": failed_pages,
        "total_pages": len(failed_pages),
        "pages_processed": 0,
        "pages_failed": 0,
        "failed_pages": [],
        "cancel_requested": False,
        "pause_requested": False,
        "is_retry": True
    }

    # Start background processing
    asyncio.create_task(run_auto_slicer_retry_job(book_id))

    return {
        "success": True,
        "message": f"Retrying {len(failed_pages)} failed pages",
        "book_id": book_id,
        "pages_to_retry": failed_pages
    }


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws/auto-slicer/{book_id}")
async def websocket_progress(websocket: WebSocket, book_id: int):
    """
    WebSocket endpoint for real-time progress updates.

    Messages sent:
    - {"type": "progress", "current_page": N, "total_pages": M, "percent": P}
    - {"type": "page_complete", "page": N, "success": bool, "error": str}
    - {"type": "status_change", "status": "running|paused|completed|cancelled|error"}
    - {"type": "complete", "pages_processed": N, "pages_failed": M, "failed_pages": [...]}
    """
    await websocket.accept()

    # Add to connections
    if book_id not in _websocket_connections:
        _websocket_connections[book_id] = []
    _websocket_connections[book_id].append(websocket)

    try:
        # Send initial status
        if book_id in _active_jobs:
            job = _active_jobs[book_id]
            await websocket.send_json({
                "type": "status",
                "status": job["status"],
                "current_page": job.get("current_page"),
                "total_pages": job.get("total_pages"),
                "pages_processed": job.get("pages_processed", 0)
            })

        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong or disconnect)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)

                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    finally:
        # Remove from connections
        if book_id in _websocket_connections:
            if websocket in _websocket_connections[book_id]:
                _websocket_connections[book_id].remove(websocket)


# =============================================================================
# Background Processing Functions
# =============================================================================

async def run_auto_slicer_job(book_id: int):
    """
    Background task that runs the Auto-slicer processing.
    """
    from datetime import datetime
    from src.services.auto_slicer_service import process_page

    job = _active_jobs.get(book_id)
    if not job:
        return

    config = get_auto_slicer_config(book_id)
    if not config:
        job["status"] = "error"
        job["error_message"] = "Configuration not found"
        return

    page_range = config["page_range"]
    start_page = job.get("current_page", page_range["start"])
    end_page = page_range["end"]

    # Get batches or create default
    batches = config.get("batches")
    if not batches:
        # No batches defined - process all at once
        batches = [{"start_page": start_page, "end_page": end_page}]

    try:
        for batch_idx, batch in enumerate(batches):
            if job["cancel_requested"]:
                break

            batch_start = max(batch["start_page"], start_page)
            batch_end = batch["end_page"]

            for page_num in range(batch_start, batch_end + 1):
                # Check for cancel/pause
                if job["cancel_requested"]:
                    job["status"] = "cancelled"
                    break

                if job["pause_requested"]:
                    job["status"] = "paused"
                    job["paused_at"] = datetime.utcnow().isoformat()

                    # Save state to DB
                    config["execution_state"] = {
                        "status": "paused",
                        "last_completed_page": page_num - 1,
                        "current_batch_index": batch_idx,
                        "started_at": job["started_at"],
                        "paused_at": job["paused_at"]
                    }
                    save_auto_slicer_config(book_id, config)

                    await broadcast_progress(book_id, {
                        "type": "status_change",
                        "status": "paused",
                        "last_completed_page": page_num - 1
                    })
                    return

                # Update current page
                job["current_page"] = page_num
                total_pages = end_page - page_range["start"] + 1
                pages_done = page_num - page_range["start"]

                # Broadcast progress (before processing)
                progress_percent = (pages_done / total_pages) * 100
                await broadcast_progress(book_id, {
                    "type": "progress",
                    "current_page": page_num,
                    "total_pages": total_pages,
                    "percent": round(progress_percent, 1)
                })

                # Process page
                try:
                    logger.info(f"Processing page {page_num} of {total_pages}")
                    result = await process_page(book_id, page_num, config)

                    if result["success"]:
                        job["pages_processed"] += 1
                        # Send updated progress after completion
                        pages_complete = page_num - page_range["start"] + 1
                        await broadcast_progress(book_id, {
                            "type": "progress",
                            "current_page": page_num,
                            "total_pages": total_pages,
                            "percent": round((pages_complete / total_pages) * 100, 1)
                        })
                        await broadcast_progress(book_id, {
                            "type": "page_complete",
                            "page": page_num,
                            "success": True
                        })
                    else:
                        job["pages_failed"] += 1
                        job["failed_pages"].append(page_num)
                        await broadcast_progress(book_id, {
                            "type": "page_complete",
                            "page": page_num,
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        })

                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}", exc_info=True)
                    job["pages_failed"] += 1
                    job["failed_pages"].append(page_num)
                    await broadcast_progress(book_id, {
                        "type": "page_complete",
                        "page": page_num,
                        "success": False,
                        "error": str(e)
                    })

                # Small delay between pages
                await asyncio.sleep(0.1)

            # Pause between batches
            if batch_idx < len(batches) - 1 and not job["cancel_requested"]:
                await asyncio.sleep(1)

        # Job completed
        if job["status"] == "running":
            job["status"] = "completed"

        # Save final state
        config["execution_state"] = {
            "status": job["status"],
            "last_completed_page": end_page if job["status"] == "completed" else job.get("current_page")
        }
        config["last_run"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "pages_processed": job["pages_processed"],
            "pages_failed": job["pages_failed"],
            "failed_pages": job["failed_pages"]
        }
        save_auto_slicer_config(book_id, config)

        # Broadcast completion
        await broadcast_progress(book_id, {
            "type": "complete",
            "status": job["status"],
            "pages_processed": job["pages_processed"],
            "pages_failed": job["pages_failed"],
            "failed_pages": job["failed_pages"]
        })

    except Exception as e:
        logger.error(f"Auto-slicer job failed: {e}")
        job["status"] = "error"
        job["error_message"] = str(e)

        config["execution_state"] = {
            "status": "error",
            "error_message": str(e)
        }
        save_auto_slicer_config(book_id, config)

        await broadcast_progress(book_id, {
            "type": "status_change",
            "status": "error",
            "error": str(e)
        })


async def run_auto_slicer_retry_job(book_id: int):
    """
    Background task that retries failed pages.
    """
    from datetime import datetime
    from src.services.auto_slicer_service import process_page

    job = _active_jobs.get(book_id)
    if not job:
        return

    config = get_auto_slicer_config(book_id)
    if not config:
        job["status"] = "error"
        return

    retry_pages = job.get("retry_pages", [])

    try:
        for idx, page_num in enumerate(retry_pages):
            if job["cancel_requested"]:
                job["status"] = "cancelled"
                break

            job["current_page"] = page_num

            # Broadcast progress
            await broadcast_progress(book_id, {
                "type": "progress",
                "current_page": page_num,
                "pages_remaining": len(retry_pages) - idx,
                "percent": round((idx / len(retry_pages)) * 100, 1)
            })

            # Process page
            try:
                result = await process_page(book_id, page_num, config)

                if result["success"]:
                    job["pages_processed"] += 1
                else:
                    job["pages_failed"] += 1
                    job["failed_pages"].append(page_num)

            except Exception as e:
                logger.error(f"Error retrying page {page_num}: {e}")
                job["pages_failed"] += 1
                job["failed_pages"].append(page_num)

            await asyncio.sleep(0.1)

        # Job completed
        if job["status"] == "running":
            job["status"] = "completed"

        # Update last_run
        config["last_run"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "pages_processed": job["pages_processed"],
            "pages_failed": job["pages_failed"],
            "failed_pages": job["failed_pages"]
        }
        save_auto_slicer_config(book_id, config)

        await broadcast_progress(book_id, {
            "type": "complete",
            "status": job["status"],
            "pages_processed": job["pages_processed"],
            "pages_failed": job["pages_failed"],
            "failed_pages": job["failed_pages"]
        })

    except Exception as e:
        logger.error(f"Auto-slicer retry job failed: {e}")
        job["status"] = "error"


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/auto-slicer/available-attributes")
async def get_available_attributes():
    """
    Get list of available attributes for rectangle mapping.

    Returns attributes 31-80 (attr1-30 are reserved).
    """
    attributes = []
    for i in range(31, 81):
        attributes.append({
            "value": f"attr{i}",
            "label": f"Attribute {i}",
            "column": f"attr{i}_value"
        })

    return {
        "attributes": attributes,
        "reserved_range": "1-30",
        "available_range": "31-80"
    }


@router.get("/auto-slicer/{book_id}/page/{page_number}/image")
async def get_raw_page_image(book_id: int, page_number: int):
    """
    Get raw page image for Auto-slicer preview.

    Returns the original page image from raw_{prefix}_pages table.
    """
    from fastapi.responses import Response

    db = SessionLocal()
    try:
        # Get book to find table prefix
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book.table_prefix

        # Get raw page image
        query = text(f"""
            SELECT original_image_data, original_format
            FROM raw_{table_prefix}_pages
            WHERE page_number = :page_number
        """)
        result = db.execute(query, {"page_number": page_number}).first()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail=f"Page {page_number} image not found")

        image_data, image_format = result

        # Determine content type
        content_type = "image/png"
        if image_format:
            if image_format.lower() in ["jpeg", "jpg"]:
                content_type = "image/jpeg"
            elif image_format.lower() == "png":
                content_type = "image/png"

        return Response(content=image_data, media_type=content_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw page image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get page image: {str(e)}")
    finally:
        db.close()
