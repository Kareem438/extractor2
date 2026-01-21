"""
Worker Main Polling Loop

Continuously polls database for pending tasks and executes them.
Handles worker lifecycle, heartbeat, and graceful shutdown.
"""

import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from src.database.connection import engine
from src.worker.config import get_config
from src.worker.executor import TaskExecutor
from src.worker.models import Task, PipelineStep
import logging
import signal
import sys

logger = logging.getLogger(__name__)


class WorkerLoop:
    """Main worker polling and execution loop"""

    def __init__(self, worker_id: Optional[str] = None):
        """
        Initialize worker loop.

        Args:
            worker_id: Optional worker ID (generated if not provided)
        """
        self.config = get_config()
        self.worker_id = worker_id or self.config.worker_id
        self.should_stop = False

        # Initialize executor
        self.executor = TaskExecutor(
            worker_id=self.worker_id,
            anthropic_api_key=self.config.anthropic_api_key,
            chroma_host=self.config.chroma_host,
            chroma_port=self.config.chroma_port
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.should_stop = True

    def start(self):
        """Start the worker loop"""
        logger.info(f"Starting worker {self.worker_id}")

        # Register worker in database
        self._register_worker()

        # Update status to running
        self._update_worker_status("running", started_at=datetime.now())

        # Main loop
        last_heartbeat = time.time()

        while not self.should_stop:
            try:
                # Update heartbeat periodically
                if time.time() - last_heartbeat > self.config.heartbeat_interval_seconds:
                    self._update_heartbeat()
                    last_heartbeat = time.time()

                # Check for stop command
                if self._check_stop_command():
                    logger.info("Stop command received")
                    break

                # Poll for pending tasks
                tasks = self._poll_pending_tasks()

                if tasks:
                    logger.info(f"Found {len(tasks)} pending task(s)")

                    # Execute tasks
                    for task in tasks:
                        if self.should_stop:
                            break

                        self._execute_task_with_steps(task)

                else:
                    # No tasks, sleep before next poll
                    time.sleep(self.config.poll_interval_seconds)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                self._update_worker_status(
                    "running",
                    last_error=str(e)
                )
                time.sleep(self.config.poll_interval_seconds)

        # Cleanup
        self._shutdown()

    def _register_worker(self):
        """Register worker in worker_status table"""
        sql = text("""
        INSERT INTO worker_status (worker_id, status, created_at)
        VALUES (:worker_id, 'stopped', NOW())
        ON CONFLICT (worker_id)
        DO UPDATE SET updated_at = NOW()
        """)

        with engine.connect() as conn:
            conn.execute(sql, {"worker_id": self.worker_id})
            conn.commit()

        logger.info(f"Registered worker: {self.worker_id}")

    def _update_worker_status(
        self,
        status: str,
        current_book_id: Optional[int] = None,
        current_entity_type: Optional[str] = None,
        current_record_id: Optional[int] = None,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        last_error: Optional[str] = None,
        started_at: Optional[datetime] = None
    ):
        """Update worker status in database"""

        updates = ["status = :status", "updated_at = NOW()"]
        params = {"worker_id": self.worker_id, "status": status}

        if current_book_id is not None:
            updates.append("current_book_id = :current_book_id")
            params["current_book_id"] = current_book_id

        if current_entity_type:
            updates.append("current_entity_type = :current_entity_type")
            params["current_entity_type"] = current_entity_type

        if current_record_id is not None:
            updates.append("current_record_id = :current_record_id")
            params["current_record_id"] = current_record_id

        if current_step is not None:
            updates.append("current_step = :current_step")
            params["current_step"] = current_step

        if total_steps is not None:
            updates.append("total_steps = :total_steps")
            params["total_steps"] = total_steps

        if last_error:
            updates.append("last_error = :last_error")
            params["last_error"] = last_error

        if started_at:
            updates.append("started_at = :started_at")
            params["started_at"] = started_at

        sql = text(f"""
        UPDATE worker_status
        SET {', '.join(updates)}
        WHERE worker_id = :worker_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def _update_heartbeat(self):
        """Update worker heartbeat"""
        sql = text("""
        UPDATE worker_status
        SET last_heartbeat = NOW()
        WHERE worker_id = :worker_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, {"worker_id": self.worker_id})
            conn.commit()

    def _check_stop_command(self) -> bool:
        """Check if a stop command has been issued"""
        sql = text("""
        SELECT id FROM worker_commands
        WHERE worker_id = :worker_id
          AND command = 'stop'
          AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(sql, {"worker_id": self.worker_id})
            row = result.fetchone()

            if row:
                # Mark command as executed
                update_sql = text("""
                UPDATE worker_commands
                SET status = 'executed',
                    executed_at = NOW(),
                    result = 'Worker stopped'
                WHERE id = :id
                """)
                conn.execute(update_sql, {"id": row[0]})
                conn.commit()
                return True

        return False

    def _poll_pending_tasks(self) -> List[Task]:
        """
        Poll for pending tasks across all books.

        Returns:
            List of tasks to execute
        """
        # Find all task queue tables
        sql = text("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE '%_task_queue'
        ORDER BY tablename
        """)

        tasks = []

        with engine.connect() as conn:
            result = conn.execute(sql)

            for row in result:
                table_name = row[0]

                # Extract table prefix
                table_prefix = table_name.replace("_task_queue", "")

                # Query pending tasks from this table
                task_sql = text(f"""
                SELECT id, entity_type, entity_id, current_step, total_steps,
                       status, priority, attempts, max_attempts, created_at, updated_at
                FROM {table_name}
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT :limit
                """)

                task_result = conn.execute(
                    task_sql,
                    {"limit": self.config.max_parallel_tasks}
                )

                for task_row in task_result:
                    task_dict = dict(task_row._mapping)
                    task_dict["table_prefix"] = table_prefix
                    task_dict["book_id"] = self._extract_book_id(table_prefix)

                    tasks.append(Task(**task_dict))

        return tasks

    def _extract_book_id(self, table_prefix: str) -> int:
        """Extract book ID from table prefix (e.g., 'book1_example' -> 1)"""
        try:
            return int(table_prefix.split("_")[0].replace("book", ""))
        except Exception:
            return 0

    def _execute_task_with_steps(self, task: Task):
        """Execute a task by loading its steps and running executor"""

        # Load pipeline steps for this book
        steps = self._load_pipeline_steps(task.table_prefix, task.entity_type)

        if not steps:
            logger.warning(
                f"No active pipeline steps for {task.table_prefix}, "
                f"entity_type={task.entity_type}"
            )
            # Mark task as completed (nothing to do)
            self._mark_task_completed(task)
            return

        # Update worker status
        self._update_worker_status(
            "running",
            current_book_id=task.book_id,
            current_entity_type=task.entity_type,
            current_record_id=task.entity_id,
            current_step=1,
            total_steps=len(steps)
        )

        # Execute task
        try:
            success = self.executor.execute_task(task, steps)

            if success:
                logger.info(f"Task {task.id} completed successfully")
            else:
                logger.warning(f"Task {task.id} failed")

        except Exception as e:
            logger.error(f"Failed to execute task {task.id}: {e}", exc_info=True)

        # Clear current task info
        self._update_worker_status(
            "running",
            current_book_id=None,
            current_entity_type=None,
            current_record_id=None,
            current_step=None,
            total_steps=None
        )

    def _load_pipeline_steps(
        self,
        table_prefix: str,
        entity_type: str
    ) -> List[PipelineStep]:
        """Load pipeline steps for a book and entity type"""

        table_name = f"{table_prefix}_pipeline_config"

        sql = text(f"""
        SELECT id, step_order, step_name, prompt_template,
               input_source, input_field, input_params,
               output_destination, output_field,
               claude_model, applies_to, on_failure,
               is_active, created_at, updated_at
        FROM {table_name}
        WHERE is_active = true
          AND (applies_to = :entity_type OR applies_to = 'both')
        ORDER BY step_order ASC
        """)

        steps = []

        with engine.connect() as conn:
            result = conn.execute(sql, {"entity_type": entity_type + "s"})

            for row in result:
                step_dict = dict(row._mapping)
                steps.append(PipelineStep(**step_dict))

        return steps

    def _mark_task_completed(self, task: Task):
        """Mark a task as completed"""
        table_name = f"{task.table_prefix}_task_queue"

        sql = text(f"""
        UPDATE {table_name}
        SET status = 'completed',
            completed_at = NOW(),
            updated_at = NOW()
        WHERE id = :task_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, {"task_id": task.id})
            conn.commit()

    def _shutdown(self):
        """Shutdown worker gracefully"""
        logger.info("Shutting down worker...")

        self._update_worker_status("stopped")

        logger.info("Worker stopped successfully")
