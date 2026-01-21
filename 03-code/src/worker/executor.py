"""
Task Execution Engine

Executes pipeline steps for tasks by coordinating all handlers.
Handles step execution, error handling, and progress tracking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from anthropic import RateLimitError
from src.database.connection import engine
from src.worker.models import Task, PipelineStep, TaskStatus, StepStatus
from src.worker.template_engine import TemplateEngine
from src.worker.handlers import PostgreSQLHandler, ChromaDBHandler, ClaudeHandler
from src.worker.rate_limiter import RateLimiter
import logging
import time

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes pipeline tasks step by step"""

    def __init__(
        self,
        worker_id: str,
        anthropic_api_key: str,
        chroma_host: str = "localhost",
        chroma_port: int = 8000
    ):
        """
        Initialize task executor.

        Args:
            worker_id: Worker ID
            anthropic_api_key: Claude API key
            chroma_host: ChromaDB host
            chroma_port: ChromaDB port
        """
        self.worker_id = worker_id
        self.claude_handler = ClaudeHandler(anthropic_api_key)
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port

        # Rate limiter
        self.rate_limiter = RateLimiter(worker_id)

        # Handler cache (per table_prefix)
        self.pg_handlers: Dict[str, PostgreSQLHandler] = {}
        self.chroma_handlers: Dict[str, ChromaDBHandler] = {}
        self.template_engines: Dict[str, TemplateEngine] = {}

    def get_handlers(self, table_prefix: str):
        """Get or create handlers for a specific book"""
        if table_prefix not in self.pg_handlers:
            self.pg_handlers[table_prefix] = PostgreSQLHandler(table_prefix)

        if table_prefix not in self.chroma_handlers:
            self.chroma_handlers[table_prefix] = ChromaDBHandler(
                table_prefix,
                self.chroma_host,
                self.chroma_port
            )

        if table_prefix not in self.template_engines:
            self.template_engines[table_prefix] = TemplateEngine(table_prefix)

        return (
            self.pg_handlers[table_prefix],
            self.chroma_handlers[table_prefix],
            self.template_engines[table_prefix]
        )

    def execute_task(self, task: Task, steps: List[PipelineStep]) -> bool:
        """
        Execute all steps for a task.

        Args:
            task: Task to execute
            steps: Pipeline steps to execute

        Returns:
            True if all steps completed successfully
        """
        logger.info(
            f"Starting task execution: {task.entity_type} {task.entity_id} "
            f"({len(steps)} steps)"
        )

        # Get handlers
        pg_handler, chroma_handler, template_engine = self.get_handlers(
            task.table_prefix
        )

        # Update task status to running
        self._update_task_status(task, "running", started_at=datetime.now())

        # Execute each step sequentially
        for step in steps:
            try:
                success = self._execute_step(
                    task,
                    step,
                    pg_handler,
                    chroma_handler,
                    template_engine
                )

                if not success:
                    # Step failed
                    if step.on_failure == "skip_remaining":
                        logger.warning(
                            f"Step {step.step_order} failed with 'skip_remaining' policy. "
                            f"Aborting remaining steps."
                        )
                        self._update_task_status(task, "failed")
                        return False
                    else:
                        logger.warning(
                            f"Step {step.step_order} failed with 'continue' policy. "
                            f"Continuing to next step."
                        )
                        continue

            except RateLimitError as e:
                # Handle rate limiting
                logger.warning(f"Rate limit error during step execution: {e}")
                self.rate_limiter.handle_rate_limit(e)

                # Wait for rate limit to clear
                self.rate_limiter.wait_for_rate_limit_clear(
                    self.claude_handler.test_api_connection
                )

                # Retry this step
                return self.execute_task(task, steps)

            except Exception as e:
                logger.error(f"Unexpected error executing step {step.step_order}: {e}")
                self._update_task_status(task, "failed", last_error=str(e))
                return False

        # All steps completed
        self._update_task_status(task, "completed", completed_at=datetime.now())
        logger.info(f"Task completed successfully: {task.entity_type} {task.entity_id}")
        return True

    def _execute_step(
        self,
        task: Task,
        step: PipelineStep,
        pg_handler: PostgreSQLHandler,
        chroma_handler: ChromaDBHandler,
        template_engine: TemplateEngine
    ) -> bool:
        """
        Execute a single pipeline step.

        Returns:
            True if step completed successfully
        """
        logger.info(
            f"Executing step {step.step_order}/{task.total_steps}: {step.step_name}"
        )

        start_time = datetime.now()

        # Update step progress to running
        self._update_step_progress(
            task,
            step,
            status="running",
            started_at=start_time
        )

        try:
            # 1. Read input data
            input_data = self._read_input(
                task,
                step,
                pg_handler,
                chroma_handler
            )

            # 2. Prepare prompt (if Claude step)
            if step.claude_model and step.prompt_template:
                # Substitute template variables
                prompt = template_engine.substitute(
                    step.prompt_template,
                    input_data
                )

                # Phase 6: Enhance prompt with diagram context and custom prompts
                if task.entity_type == "diagram":
                    from src.worker.diagram_context import (
                        build_diagram_context,
                        get_custom_prompt_for_diagram,
                        enhance_prompt_with_context
                    )

                    # Build context from sequential texts
                    context = build_diagram_context(
                        task.entity_type,
                        input_data
                    )

                    # Get custom prompt based on diagram type
                    prompt_type = input_data.get("prompt_type")
                    custom_prompt = get_custom_prompt_for_diagram(
                        task.book_id,
                        prompt_type
                    )

                    # Enhance prompt
                    prompt = enhance_prompt_with_context(
                        prompt,
                        context,
                        custom_prompt
                    )

                # Call Claude API
                api_response = self.claude_handler.call_api(
                    prompt=prompt,
                    model=step.claude_model
                )

                output_value = api_response["response"]


            else:
                # Non-Claude step (e.g., just embedding sync)
                api_response = None
                # For embedding operations, use input text
                output_value = input_data.get(step.input_field, "")

            # 3. Write output
            self._write_output(
                task,
                step,
                output_value,
                pg_handler,
                chroma_handler
            )

            # 4. Update step progress to completed
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            self._update_step_progress(
                task,
                step,
                status="completed",
                api_response=api_response,
                output_value=str(output_value)[:500],  # Truncate for storage
                completed_at=end_time,
                duration_ms=duration_ms
            )

            return True

        except Exception as e:
            logger.error(f"Step {step.step_order} failed: {e}")

            # Update step progress to failed
            self._update_step_progress(
                task,
                step,
                status="failed",
                error_message=str(e)
            )

            return False

    def _read_input(
        self,
        task: Task,
        step: PipelineStep,
        pg_handler: PostgreSQLHandler,
        chroma_handler: ChromaDBHandler
    ) -> Dict[str, Any]:
        """Read input data for a step"""

        if step.input_source == "postgresql":
            # Read from PostgreSQL
            return pg_handler.read_entity_data(
                task.entity_type,
                task.entity_id
            )

        elif step.input_source == "chromadb":
            # Read from ChromaDB
            operation = step.input_field

            if operation == "semantic_search":
                # Perform semantic search
                max_results = step.input_params.get("max_results", 5) if step.input_params else 5
                format_type = step.input_params.get("format", "json") if step.input_params else "json"

                similar_records = chroma_handler.semantic_search(
                    task.entity_type,
                    task.entity_id,
                    max_results=max_results
                )

                # Format results
                formatted = chroma_handler.format_similar_results(
                    similar_records,
                    format_type
                )

                return {"similar_results": formatted}

            elif operation == "get_metadata":
                metadata = chroma_handler.get_metadata(
                    task.entity_type,
                    task.entity_id
                )
                return {"metadata": metadata}

            elif operation == "get_embedding":
                embedding = chroma_handler.get_embedding(
                    task.entity_type,
                    task.entity_id
                )
                return {"embedding": embedding}

            else:
                raise ValueError(f"Unknown ChromaDB operation: {operation}")

        else:
            raise ValueError(f"Unknown input source: {step.input_source}")

    def _write_output(
        self,
        task: Task,
        step: PipelineStep,
        output_value: str,
        pg_handler: PostgreSQLHandler,
        chroma_handler: ChromaDBHandler
    ):
        """Write output data from a step"""

        if step.output_destination == "postgresql":
            # Write to PostgreSQL
            pg_handler.write_entity_field(
                task.entity_type,
                task.entity_id,
                step.output_field,
                output_value
            )

        elif step.output_destination == "chromadb":
            operation = step.output_field

            if operation == "upsert_embedding":
                # Generate and store embedding
                chroma_handler.upsert_embedding(
                    task.entity_type,
                    task.entity_id,
                    text=output_value
                )

            elif operation == "update_metadata":
                # Update metadata
                metadata = {"step_output": output_value[:100]}
                chroma_handler.update_metadata(
                    task.entity_type,
                    task.entity_id,
                    metadata
                )

            else:
                raise ValueError(f"Unknown ChromaDB operation: {operation}")

        else:
            raise ValueError(f"Unknown output destination: {step.output_destination}")

    def _update_task_status(
        self,
        task: Task,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        last_error: Optional[str] = None
    ):
        """Update task status in database"""

        table_name = f"{task.table_prefix}_task_queue"

        updates = ["status = :status", "updated_at = NOW()"]
        params = {"task_id": task.id, "status": status}

        if started_at:
            updates.append("started_at = :started_at")
            params["started_at"] = started_at

        if completed_at:
            updates.append("completed_at = :completed_at")
            params["completed_at"] = completed_at

        if last_error:
            updates.append("last_error = :last_error")
            params["last_error"] = last_error

        sql = text(f"""
        UPDATE {table_name}
        SET {', '.join(updates)}
        WHERE id = :task_id
        """)

        with engine.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def _update_step_progress(
        self,
        task: Task,
        step: PipelineStep,
        status: str,
        api_response: Optional[Dict[str, Any]] = None,
        output_value: Optional[str] = None,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None
    ):
        """Update step progress in database"""

        table_name = f"{task.table_prefix}_step_progress"

        # Upsert step progress
        sql = text(f"""
        INSERT INTO {table_name} (
            entity_type, entity_id, step_order, step_name, status,
            api_response, output_value, error_message,
            started_at, completed_at, duration_ms
        ) VALUES (
            :entity_type, :entity_id, :step_order, :step_name, :status,
            :api_response, :output_value, :error_message,
            :started_at, :completed_at, :duration_ms
        )
        ON CONFLICT (entity_type, entity_id, step_order)
        DO UPDATE SET
            status = EXCLUDED.status,
            api_response = EXCLUDED.api_response,
            output_value = EXCLUDED.output_value,
            error_message = EXCLUDED.error_message,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            duration_ms = EXCLUDED.duration_ms,
            updated_at = NOW()
        """)

        with engine.connect() as conn:
            conn.execute(sql, {
                "entity_type": task.entity_type,
                "entity_id": task.entity_id,
                "step_order": step.step_order,
                "step_name": step.step_name,
                "status": status,
                "api_response": api_response,
                "output_value": output_value,
                "error_message": error_message,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_ms": duration_ms
            })
            conn.commit()
