"""
Pipeline Configuration API Routes

Endpoints for managing Claude pipeline configurations per book.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from src.database.connection import engine
from src.worker.template_engine import TemplateEngine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class PipelineStepCreate(BaseModel):
    """Model for creating a pipeline step"""
    step_order: int = Field(..., description="Step execution order")
    step_name: str = Field(..., description="Human-readable step name")
    prompt_template: Optional[str] = Field(None, description="Prompt with template variables")
    input_source: str = Field(..., description="'postgresql' or 'chromadb'")
    input_field: Optional[str] = Field(None, description="Column name or operation")
    input_params: Optional[Dict[str, Any]] = Field(None, description="Additional input parameters")
    output_destination: str = Field(..., description="'postgresql' or 'chromadb'")
    output_field: Optional[str] = Field(None, description="Column name or operation")
    claude_model: Optional[str] = Field(None, description="'sonnet-4', 'opus-4.5', 'haiku', or None")
    applies_to: str = Field(default="paragraphs", description="'paragraphs', 'diagrams', or 'both'")
    on_failure: str = Field(default="skip_remaining", description="'skip_remaining' or 'continue'")
    is_active: bool = Field(default=True, description="Whether step is active")


class PipelineStepUpdate(BaseModel):
    """Model for updating a pipeline step"""
    step_name: Optional[str] = None
    prompt_template: Optional[str] = None
    input_source: Optional[str] = None
    input_field: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    output_destination: Optional[str] = None
    output_field: Optional[str] = None
    claude_model: Optional[str] = None
    applies_to: Optional[str] = None
    on_failure: Optional[str] = None
    is_active: Optional[bool] = None


class PipelineStepResponse(BaseModel):
    """Model for pipeline step response"""
    id: int
    step_order: int
    step_name: str
    prompt_template: Optional[str]
    input_source: str
    input_field: Optional[str]
    input_params: Optional[Dict[str, Any]]
    output_destination: str
    output_field: Optional[str]
    claude_model: Optional[str]
    applies_to: str
    on_failure: str
    is_active: bool
    created_at: str
    updated_at: str


class TemplateVariablesResponse(BaseModel):
    """Model for template variables response"""
    variables: Dict[str, str] = Field(..., description="Map of variable_name -> column_name")
    count: int = Field(..., description="Number of available variables")


class TaskQueueRequest(BaseModel):
    """Model for creating tasks in queue"""
    entity_type: str = Field(..., description="'paragraph' or 'diagram'")
    entity_ids: List[int] = Field(..., description="List of entity IDs to process")
    priority: int = Field(default=0, description="Task priority")


# Pipeline Configuration Endpoints

@router.get("/books/{book_id}/pipeline/steps", response_model=List[PipelineStepResponse])
async def get_pipeline_steps(book_id: int):
    """Get all pipeline steps for a book"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    table_name = f"{table_prefix}_pipeline_config"

    sql = text(f"""
    SELECT id, step_order, step_name, prompt_template,
           input_source, input_field, input_params,
           output_destination, output_field,
           claude_model, applies_to, on_failure, is_active,
           created_at, updated_at
    FROM {table_name}
    ORDER BY step_order ASC
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)
        steps = []

        for row in result:
            step_dict = dict(row._mapping)
            step_dict['created_at'] = step_dict['created_at'].isoformat()
            step_dict['updated_at'] = step_dict['updated_at'].isoformat()
            steps.append(PipelineStepResponse(**step_dict))

        return steps


@router.post("/books/{book_id}/pipeline/steps", response_model=PipelineStepResponse)
async def create_pipeline_step(book_id: int, step: PipelineStepCreate):
    """Create a new pipeline step"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    # Validate template if provided
    if step.prompt_template:
        template_engine = TemplateEngine(table_prefix)
        is_valid, error = template_engine.validate_template(step.prompt_template)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid template: {error}")

    table_name = f"{table_prefix}_pipeline_config"

    sql = text(f"""
    INSERT INTO {table_name} (
        step_order, step_name, prompt_template,
        input_source, input_field, input_params,
        output_destination, output_field,
        claude_model, applies_to, on_failure, is_active
    ) VALUES (
        :step_order, :step_name, :prompt_template,
        :input_source, :input_field, :input_params,
        :output_destination, :output_field,
        :claude_model, :applies_to, :on_failure, :is_active
    )
    RETURNING id, step_order, step_name, prompt_template,
              input_source, input_field, input_params,
              output_destination, output_field,
              claude_model, applies_to, on_failure, is_active,
              created_at, updated_at
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, step.model_dump())
        conn.commit()
        row = result.fetchone()

        step_dict = dict(row._mapping)
        step_dict['created_at'] = step_dict['created_at'].isoformat()
        step_dict['updated_at'] = step_dict['updated_at'].isoformat()

        return PipelineStepResponse(**step_dict)


@router.put("/books/{book_id}/pipeline/steps/{step_id}", response_model=PipelineStepResponse)
async def update_pipeline_step(book_id: int, step_id: int, step: PipelineStepUpdate):
    """Update a pipeline step"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    table_name = f"{table_prefix}_pipeline_config"

    # Build update query dynamically
    updates = []
    params = {"step_id": step_id}

    for field, value in step.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = :{field}")
        params[field] = value

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")

    sql = text(f"""
    UPDATE {table_name}
    SET {', '.join(updates)}
    WHERE id = :step_id
    RETURNING id, step_order, step_name, prompt_template,
              input_source, input_field, input_params,
              output_destination, output_field,
              claude_model, applies_to, on_failure, is_active,
              created_at, updated_at
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, params)
        conn.commit()
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Pipeline step not found")

        step_dict = dict(row._mapping)
        step_dict['created_at'] = step_dict['created_at'].isoformat()
        step_dict['updated_at'] = step_dict['updated_at'].isoformat()

        return PipelineStepResponse(**step_dict)


@router.delete("/books/{book_id}/pipeline/steps/{step_id}")
async def delete_pipeline_step(book_id: int, step_id: int):
    """Delete a pipeline step"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    table_name = f"{table_prefix}_pipeline_config"

    sql = text(f"""
    DELETE FROM {table_name}
    WHERE id = :step_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"step_id": step_id})
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pipeline step not found")

        return {"success": True, "message": "Pipeline step deleted"}


@router.get("/books/{book_id}/pipeline/variables", response_model=TemplateVariablesResponse)
async def get_template_variables(book_id: int):
    """Get available template variables for a book"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    # Load template engine
    template_engine = TemplateEngine(table_prefix)
    variables = template_engine.get_available_variables()

    return TemplateVariablesResponse(
        variables=variables,
        count=len(variables)
    )


@router.post("/books/{book_id}/pipeline/validate-template")
async def validate_template(book_id: int, template: str = Query(..., description="Template to validate")):
    """Validate a template string"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    template_engine = TemplateEngine(table_prefix)
    is_valid, error = template_engine.validate_template(template)

    return {
        "valid": is_valid,
        "error": error,
        "variables_found": template_engine.find_variables(template) if is_valid else []
    }


# Task Queue Endpoints

@router.post("/books/{book_id}/pipeline/queue")
async def create_tasks(book_id: int, request: TaskQueueRequest):
    """Create tasks in the queue for processing"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    # Count active steps for this entity type
    total_steps = await _count_active_steps(table_prefix, request.entity_type)

    if total_steps == 0:
        raise HTTPException(
            status_code=400,
            detail=f"No active pipeline steps configured for {request.entity_type}"
        )

    # Create tasks
    table_name = f"{table_prefix}_task_queue"

    tasks_created = []

    with engine.connect() as conn:
        for entity_id in request.entity_ids:
            sql = text(f"""
            INSERT INTO {table_name} (
                entity_type, entity_id, total_steps, status, priority
            ) VALUES (
                :entity_type, :entity_id, :total_steps, 'pending', :priority
            )
            ON CONFLICT (entity_type, entity_id)
            DO UPDATE SET
                status = 'pending',
                priority = EXCLUDED.priority,
                current_step = 1,
                updated_at = NOW()
            RETURNING id, entity_type, entity_id
            """)

            result = conn.execute(sql, {
                "entity_type": request.entity_type,
                "entity_id": entity_id,
                "total_steps": total_steps,
                "priority": request.priority
            })

            row = result.fetchone()
            tasks_created.append(dict(row._mapping))

        conn.commit()

    return {
        "success": True,
        "tasks_created": len(tasks_created),
        "tasks": tasks_created
    }


@router.get("/books/{book_id}/pipeline/queue/status")
async def get_queue_status(book_id: int):
    """Get status of task queue for a book"""

    # Get table prefix for book
    table_prefix = await _get_table_prefix(book_id)

    table_name = f"{table_prefix}_task_queue"

    sql = text(f"""
    SELECT
        status,
        COUNT(*) as count
    FROM {table_name}
    GROUP BY status
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)

        status_counts = {}
        for row in result:
            status_counts[row[0]] = row[1]

        return {
            "pending": status_counts.get("pending", 0),
            "running": status_counts.get("running", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "paused": status_counts.get("paused", 0),
            "total": sum(status_counts.values())
        }


# Helper Functions

async def _get_table_prefix(book_id: int) -> str:
    """Get table prefix for a book ID"""

    sql = text("""
    SELECT table_prefix
    FROM books_metadata
    WHERE book_id = :book_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        return row[0]


async def _count_active_steps(table_prefix: str, entity_type: str) -> int:
    """Count active pipeline steps for an entity type"""

    table_name = f"{table_prefix}_pipeline_config"

    # Map entity_type to applies_to value
    applies_to_value = entity_type + "s"  # "paragraph" -> "paragraphs"

    sql = text(f"""
    SELECT COUNT(*)
    FROM {table_name}
    WHERE is_active = true
      AND (applies_to = :applies_to OR applies_to = 'both')
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"applies_to": applies_to_value})
        return result.scalar()


# =============================================================================
# Knowledge Unit Creation Endpoints (Phase 3B Enhancement)
# =============================================================================

from src.services.ku_creation_service import (
    create_knowledge_units_for_pages,
    get_page_ku_status
)


class CreateKURequest(BaseModel):
    """Request model for creating knowledge units"""
    page_numbers: List[int] = Field(..., description="List of page numbers to process")


class PageStatusResponse(BaseModel):
    """Response model for page status"""
    page_number: int
    layout_status: str  # pending, detected, ready
    extraction_status: str  # pending, completed
    ku_status: str  # pending, completed
    claude_status: str  # pending, completed
    ready_for_extraction: bool


@router.post("/books/{book_id}/pipeline/create-knowledge-units")
async def create_knowledge_units(book_id: int, request: CreateKURequest):
    """
    Create knowledge units from extracted raw records.
    
    This endpoint:
    1. Gets all paragraphs and diagrams from raw tables for specified pages
    2. Creates KU for each paragraph (direct OCR text copy)
    3. Creates KU for each diagram/table/equation/list (skeleton with image reference)
    4. Merges Q&A pairs into single KU (both image references in JSON)
    5. Updates bidirectional links
    
    Prerequisites:
    - Pages must have been extracted (records exist in raw_paragraph_images or raw_diagram_images)
    """
    try:
        # Validate book exists
        table_prefix = await _get_table_prefix(book_id)
        
        if not request.page_numbers:
            raise HTTPException(status_code=400, detail="No page numbers provided")
        
        # Call the service function
        result = create_knowledge_units_for_pages(book_id, request.page_numbers)
        
        if not result["success"] and not result["paragraphs_created"] and not result["diagrams_created"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create knowledge units: {', '.join(result['errors'])}"
            )
        
        return {
            "success": result["success"],
            "message": f"Created {result['paragraphs_created']} paragraph KUs, {result['diagrams_created']} diagram KUs, {result['qa_pairs_created']} Q&A pair KUs",
            "paragraphs_created": result["paragraphs_created"],
            "diagrams_created": result["diagrams_created"],
            "qa_pairs_created": result["qa_pairs_created"],
            "errors": result["errors"] if result["errors"] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge units: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books/{book_id}/pipeline/page-status", response_model=List[PageStatusResponse])
async def get_pipeline_page_status(book_id: int):
    """
    Get the pipeline status for all pages in a book.
    
    Returns status for each page:
    - layout_status: pending, detected, ready
    - extraction_status: pending, completed
    - ku_status: pending, completed
    - claude_status: pending, completed
    """
    try:
        # Validate book exists
        await _get_table_prefix(book_id)
        
        # Get page status from service
        page_status = get_page_ku_status(book_id)
        
        return [PageStatusResponse(**status) for status in page_status]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books/{book_id}/pipeline/pages-ready-for-ku")
async def get_pages_ready_for_ku(book_id: int):
    """
    Get list of pages that are ready for KU creation.
    
    A page is ready if:
    - It has records in raw_paragraph_images or raw_diagram_images
    - Those records don't have linked_knowledge_unit_id set yet
    """
    try:
        table_prefix = await _get_table_prefix(book_id)
        
        # Get pages with unlinked paragraphs
        para_sql = text(f"""
            SELECT DISTINCT page_number 
            FROM raw_{table_prefix}_paragraph_images
            WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NULL
        """)
        
        # Get pages with unlinked diagrams
        diag_sql = text(f"""
            SELECT DISTINCT page_number 
            FROM raw_{table_prefix}_diagram_images
            WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NULL
        """)
        
        with engine.connect() as conn:
            para_pages = {row[0] for row in conn.execute(para_sql).fetchall()}
            diag_pages = {row[0] for row in conn.execute(diag_sql).fetchall()}
        
        ready_pages = sorted(para_pages | diag_pages)
        
        return {
            "success": True,
            "ready_pages": ready_pages,
            "count": len(ready_pages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pages ready for KU: {e}")
        raise HTTPException(status_code=500, detail=str(e))
