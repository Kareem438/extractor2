"""
Worker Control API Routes

Endpoints for controlling and monitoring the backend worker process.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from src.database.connection import engine
from datetime import datetime
import subprocess
import os
import sys
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class WorkerStatusResponse(BaseModel):
    """Model for worker status response"""
    worker_id: str
    status: str
    current_book_id: Optional[int]
    current_entity_type: Optional[str]
    current_record_id: Optional[int]
    current_step: Optional[int]
    total_steps: Optional[int]
    records_processed: int
    records_failed: int
    records_remaining: int
    last_heartbeat: Optional[str]
    started_at: Optional[str]
    rate_limited_until: Optional[str]
    last_error: Optional[str]
    is_alive: bool = Field(..., description="Whether worker is responding (heartbeat within 30s)")


class WorkerCommandRequest(BaseModel):
    """Model for worker command request"""
    command: str = Field(..., description="'start', 'stop', 'pause', or 'resume'")
    worker_id: str = Field(default="worker-001", description="Worker ID to control")
    parameters: Optional[Dict[str, Any]] = None


class TaskProgressResponse(BaseModel):
    """Model for task progress"""
    task_id: int
    entity_type: str
    entity_id: int
    current_step: int
    total_steps: int
    status: str
    step_details: List[Dict[str, Any]] = Field(..., description="Per-step progress")


# Worker Control Endpoints

@router.get("/worker/status", response_model=WorkerStatusResponse)
async def get_worker_status(worker_id: str = "worker-001"):
    """Get current status of worker"""

    sql = text("""
    SELECT
        worker_id, status, current_book_id, current_entity_type,
        current_record_id, current_step, total_steps,
        records_processed, records_failed, records_remaining,
        last_heartbeat, started_at, rate_limited_until, last_error,
        created_at, updated_at
    FROM worker_status
    WHERE worker_id = :worker_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"worker_id": worker_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

        worker_dict = dict(row._mapping)

        # Convert timestamps to ISO format
        for field in ['last_heartbeat', 'started_at', 'rate_limited_until']:
            if worker_dict.get(field):
                worker_dict[field] = worker_dict[field].isoformat()

        # Check if worker is alive (heartbeat within last 30 seconds)
        is_alive = False
        if worker_dict['last_heartbeat']:
            last_heartbeat = datetime.fromisoformat(worker_dict['last_heartbeat'])
            is_alive = (datetime.now() - last_heartbeat).total_seconds() < 30

        worker_dict['is_alive'] = is_alive

        return WorkerStatusResponse(**worker_dict)


@router.post("/worker/command")
async def send_worker_command(request: WorkerCommandRequest):
    """Send a command to the worker"""

    if request.command not in ["start", "stop", "pause", "resume"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command: {request.command}. Must be 'start', 'stop', 'pause', or 'resume'"
        )

    # Special handling for 'start' command - launch worker process
    if request.command == "start":
        return await _start_worker(request.worker_id)

    # For other commands, insert into worker_commands table
    sql = text("""
    INSERT INTO worker_commands (worker_id, command, parameters, status)
    VALUES (:worker_id, :command, :parameters, 'pending')
    RETURNING id, worker_id, command, created_at
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {
            "worker_id": request.worker_id,
            "command": request.command,
            "parameters": request.parameters
        })
        conn.commit()
        row = result.fetchone()

        command_dict = dict(row._mapping)
        command_dict['created_at'] = command_dict['created_at'].isoformat()

        return {
            "success": True,
            "message": f"Command '{request.command}' sent to worker {request.worker_id}",
            "command": command_dict
        }


@router.get("/worker/commands")
async def get_worker_commands(
    worker_id: str = "worker-001",
    limit: int = 10
):
    """Get recent commands sent to worker"""

    sql = text("""
    SELECT id, worker_id, command, parameters, status, created_at, executed_at, result
    FROM worker_commands
    WHERE worker_id = :worker_id
    ORDER BY created_at DESC
    LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"worker_id": worker_id, "limit": limit})

        commands = []
        for row in result:
            cmd_dict = dict(row._mapping)
            cmd_dict['created_at'] = cmd_dict['created_at'].isoformat()
            if cmd_dict['executed_at']:
                cmd_dict['executed_at'] = cmd_dict['executed_at'].isoformat()
            commands.append(cmd_dict)

        return {"commands": commands}


# Task Progress Endpoints

@router.get("/books/{book_id}/tasks/{entity_type}/{entity_id}/progress", response_model=TaskProgressResponse)
async def get_task_progress(book_id: int, entity_type: str, entity_id: int):
    """Get progress for a specific task"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    # Get task info
    task_queue_table = f"{table_prefix}_task_queue"
    step_progress_table = f"{table_prefix}_step_progress"

    task_sql = text(f"""
    SELECT id, entity_type, entity_id, current_step, total_steps, status
    FROM {task_queue_table}
    WHERE entity_type = :entity_type AND entity_id = :entity_id
    """)

    with engine.connect() as conn:
        result = conn.execute(task_sql, {"entity_type": entity_type, "entity_id": entity_id})
        task_row = result.fetchone()

        if not task_row:
            raise HTTPException(status_code=404, detail="Task not found")

        task_dict = dict(task_row._mapping)

        # Get step details
        step_sql = text(f"""
        SELECT step_order, step_name, status, started_at, completed_at, duration_ms, error_message
        FROM {step_progress_table}
        WHERE entity_type = :entity_type AND entity_id = :entity_id
        ORDER BY step_order ASC
        """)

        result = conn.execute(step_sql, {"entity_type": entity_type, "entity_id": entity_id})

        step_details = []
        for row in result:
            step_dict = dict(row._mapping)
            if step_dict['started_at']:
                step_dict['started_at'] = step_dict['started_at'].isoformat()
            if step_dict['completed_at']:
                step_dict['completed_at'] = step_dict['completed_at'].isoformat()
            step_details.append(step_dict)

        task_dict['step_details'] = step_details

        return TaskProgressResponse(**task_dict)


@router.get("/books/{book_id}/tasks/progress/summary")
async def get_tasks_progress_summary(book_id: int):
    """Get summary of all tasks progress for a book"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    task_queue_table = f"{table_prefix}_task_queue"

    sql = text(f"""
    SELECT
        entity_type,
        status,
        COUNT(*) as count,
        AVG(current_step::float / NULLIF(total_steps, 0) * 100) as avg_progress_pct
    FROM {task_queue_table}
    GROUP BY entity_type, status
    ORDER BY entity_type, status
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)

        summary = {}
        for row in result:
            entity_type = row[0]
            status = row[1]
            count = row[2]
            avg_progress = row[3] or 0

            if entity_type not in summary:
                summary[entity_type] = {
                    "total": 0,
                    "by_status": {},
                    "avg_progress_pct": 0
                }

            summary[entity_type]["by_status"][status] = count
            summary[entity_type]["total"] += count

        # Calculate overall average progress
        total_sql = text(f"""
        SELECT
            entity_type,
            AVG(current_step::float / NULLIF(total_steps, 0) * 100) as avg_progress_pct
        FROM {task_queue_table}
        GROUP BY entity_type
        """)

        result = conn.execute(total_sql)
        for row in result:
            entity_type = row[0]
            avg_progress = row[1] or 0
            if entity_type in summary:
                summary[entity_type]["avg_progress_pct"] = round(avg_progress, 2)

        return {"summary": summary}


# Helper Functions

async def _get_table_prefix(book_id: int) -> str:
    """Get table prefix for a book ID"""

    sql = text("""
    SELECT table_prefix
    FROM books_metadata
    WHERE id = :book_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        return row[0]


async def _start_worker(worker_id: str):
    """Start the worker process"""

    # Get Python executable path
    python_exe = sys.executable

    # Get worker script path
    worker_script = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "worker", "main.py"
    )

    # Check if worker is already running
    try:
        status = await get_worker_status(worker_id)
        if status.is_alive and status.status in ["running", "paused"]:
            return {
                "success": False,
                "message": f"Worker {worker_id} is already running",
                "status": status.status
            }
    except HTTPException:
        # Worker not found in DB - that's okay, it will be registered on startup
        pass

    # Start worker process in background
    try:
        # Use subprocess.Popen to start in background
        process = subprocess.Popen(
            [python_exe, "-m", "src.worker.main", "--worker-id", worker_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        logger.info(f"Started worker process {worker_id} with PID {process.pid}")

        return {
            "success": True,
            "message": f"Worker {worker_id} started successfully",
            "pid": process.pid,
            "worker_id": worker_id
        }

    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start worker: {str(e)}")
