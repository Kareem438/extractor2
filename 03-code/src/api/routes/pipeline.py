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


# =============================================================================
# Tag Mapping Models (Requirement 7A)
# =============================================================================

class TagMapping(BaseModel):
    """Model for a single tag-to-attribute mapping"""
    tag_name: str = Field(..., description="XML tag name (e.g., 'summary')")
    target_attribute: str = Field(..., description="Target attribute (e.g., 'attr_15')")
    is_required: bool = Field(default=False, description="Mark KU incomplete if missing")
    order: int = Field(default=0, description="Display order")


class TagMappingsUpdate(BaseModel):
    """Model for updating tag mappings"""
    tag_mappings: List[TagMapping] = Field(default=[], description="List of tag mappings")
    fallback_attribute: Optional[str] = Field(None, description="Attribute for unmapped tags")


class TagMappingsResponse(BaseModel):
    """Model for tag mappings response"""
    tag_mappings: List[TagMapping]
    fallback_attribute: Optional[str]


# =============================================================================
# KU Grouping Models (Requirement 7B)
# =============================================================================

class GroupingConfigUpdate(BaseModel):
    """Model for updating grouping configuration"""
    is_enabled: bool = Field(default=False, description="Enable KU grouping")
    grouping_mode: str = Field(default="ku_count", description="'ku_count' or 'token_limit'")
    max_kus_per_group: int = Field(default=5, description="Max KUs per group")
    max_tokens_per_group: int = Field(default=4000, description="Max tokens per group")
    fallback_attribute: Optional[str] = Field(None, description="Attribute for unmapped tags")


class GroupingPreviewItem(BaseModel):
    """Model for grouping preview item"""
    l1_title: str
    l2_title: str
    ku_count: int
    word_count: int
    estimated_tokens: int


class ExecutionRequest(BaseModel):
    """Model for pipeline execution request"""
    mode: str = Field(default="individual", description="'individual', 'grouped', or 'incomplete'")
    dry_run: bool = Field(default=False, description="Preview without executing")
    save_preview_to: Optional[str] = Field(None, description="Attribute to save preview")
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


# =============================================================================
# Tag Mapping Endpoints (Requirement 7A)
# =============================================================================

@router.get("/books/{book_id}/pipeline/steps/{step_id}/tag-mappings")
async def get_tag_mappings(book_id: int, step_id: int):
    """Get tag mappings for a pipeline step"""
    
    table_prefix = await _get_table_prefix(book_id)
    table_name = f"{table_prefix}_pipeline_config"
    
    sql = text(f"""
    SELECT tag_mappings, fallback_attribute
    FROM {table_name}
    WHERE id = :step_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {"step_id": step_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Pipeline step not found")
        
        tag_mappings = result[0] if result[0] else []
        fallback_attribute = result[1]
        
        return {
            "tag_mappings": tag_mappings,
            "fallback_attribute": fallback_attribute
        }


@router.put("/books/{book_id}/pipeline/steps/{step_id}/tag-mappings")
async def update_tag_mappings(book_id: int, step_id: int, request: TagMappingsUpdate):
    """Update tag mappings for a pipeline step"""
    
    table_prefix = await _get_table_prefix(book_id)
    table_name = f"{table_prefix}_pipeline_config"
    
    # Convert to JSON-serializable format
    import json
    tag_mappings_json = json.dumps([m.model_dump() for m in request.tag_mappings])
    
    sql = text(f"""
    UPDATE {table_name}
    SET tag_mappings = :tag_mappings::jsonb,
        fallback_attribute = :fallback_attribute,
        updated_at = NOW()
    WHERE id = :step_id
    RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {
            "step_id": step_id,
            "tag_mappings": tag_mappings_json,
            "fallback_attribute": request.fallback_attribute
        }).fetchone()
        conn.commit()
        
        if not result:
            raise HTTPException(status_code=404, detail="Pipeline step not found")
        
        return {"success": True, "message": "Tag mappings updated"}


# =============================================================================
# KU Grouping Endpoints (Requirement 7B)
# =============================================================================

@router.get("/books/{book_id}/pipeline/grouping/config")
async def get_grouping_config(book_id: int):
    """Get KU grouping configuration for a book"""
    
    table_prefix = await _get_table_prefix(book_id)
    table_name = f"{table_prefix}_ku_grouping_config"
    
    sql = text(f"""
    SELECT is_enabled, grouping_mode, max_kus_per_group, max_tokens_per_group, fallback_attribute
    FROM {table_name}
    WHERE id = 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql).fetchone()
        
        if not result:
            return {
                "is_enabled": False,
                "grouping_mode": "ku_count",
                "max_kus_per_group": 5,
                "max_tokens_per_group": 4000,
                "fallback_attribute": None
            }
        
        return {
            "is_enabled": result[0],
            "grouping_mode": result[1],
            "max_kus_per_group": result[2],
            "max_tokens_per_group": result[3],
            "fallback_attribute": result[4]
        }


@router.put("/books/{book_id}/pipeline/grouping/config")
async def update_grouping_config(book_id: int, request: GroupingConfigUpdate):
    """Update KU grouping configuration for a book"""
    
    table_prefix = await _get_table_prefix(book_id)
    table_name = f"{table_prefix}_ku_grouping_config"
    
    sql = text(f"""
    UPDATE {table_name}
    SET is_enabled = :is_enabled,
        grouping_mode = :grouping_mode,
        max_kus_per_group = :max_kus_per_group,
        max_tokens_per_group = :max_tokens_per_group,
        fallback_attribute = :fallback_attribute,
        updated_at = NOW()
    WHERE id = 1
    RETURNING id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, request.model_dump()).fetchone()
        conn.commit()
        
        if not result:
            # Insert if not exists
            conn.execute(text(f"""
                INSERT INTO {table_name} (id, is_enabled, grouping_mode, max_kus_per_group, max_tokens_per_group, fallback_attribute)
                VALUES (1, :is_enabled, :grouping_mode, :max_kus_per_group, :max_tokens_per_group, :fallback_attribute)
            """), request.model_dump())
            conn.commit()
        
        return {"success": True, "message": "Grouping config updated"}


@router.get("/books/{book_id}/pipeline/grouping/preview")
async def get_grouping_preview(book_id: int):
    """Get preview of KU grouping by L1/L2 titles"""
    
    # V2 books don't have V1 knowledge_units table
    from src.database.utils import get_extraction_method
    if get_extraction_method(book_id) == 'v2':
        return {"preview": [], "total_groups": 0, "message": "V2 books use cloud extraction"}

    table_prefix = await _get_table_prefix(book_id)
    ku_table = f"{table_prefix}_knowledge_units"
    
    # Get KU counts and word counts grouped by L1/L2 titles
    sql = text(f"""
    SELECT 
        COALESCE(chapter, 'No Chapter') as l1_title,
        COALESCE(topic, 'No Topic') as l2_title,
        COUNT(*) as ku_count,
        SUM(LENGTH(COALESCE(text_content, ''))) as total_chars
    FROM {ku_table}
    WHERE attr8_value = 'enabled' OR attr8_value IS NULL
    GROUP BY chapter, topic
    ORDER BY chapter, topic
    """)
    
    with engine.connect() as conn:
        results = conn.execute(sql).fetchall()
        
        preview = []
        for row in results:
            total_chars = row[3] or 0
            # Estimate tokens (~4 chars per token)
            estimated_tokens = total_chars // 4
            
            preview.append({
                "l1_title": row[0],
                "l2_title": row[1],
                "ku_count": row[2],
                "word_count": total_chars // 5,  # Rough word estimate
                "estimated_tokens": estimated_tokens
            })
        
        return {"preview": preview, "total_groups": len(preview)}


@router.post("/books/{book_id}/pipeline/grouping/estimate-tokens")
async def estimate_group_tokens(book_id: int, ku_ids: List[int]):
    """Estimate tokens for a group of KUs"""
    
    # V2 books don't have V1 knowledge_units table
    from src.database.utils import get_extraction_method
    if get_extraction_method(book_id) == 'v2':
        return {"input_tokens": 0, "estimated_output_tokens": 0, "total_kus": 0, "message": "V2 books use cloud extraction"}

    from src.services.claude_batch_service import estimate_tokens
    
    table_prefix = await _get_table_prefix(book_id)
    ku_table = f"{table_prefix}_knowledge_units"
    
    if not ku_ids:
        return {"input_tokens": 0, "estimated_output_tokens": 0}
    
    sql = text(f"""
    SELECT unit_id, text_content
    FROM {ku_table}
    WHERE unit_id IN :ku_ids
    """)
    
    with engine.connect() as conn:
        results = conn.execute(sql, {"ku_ids": tuple(ku_ids)}).fetchall()
        
        total_text = ""
        for row in results:
            total_text += f"<ku_{row[0]}>{row[1] or ''}</ku_{row[0]}>\n"
        
        input_tokens = estimate_tokens(total_text)
        # Estimate output as ~50% of input for summaries
        estimated_output = input_tokens // 2
        
        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output,
            "total_kus": len(results)
        }


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
        # V2 books don't have V1 raw paragraph/diagram tables
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"success": False, "message": "V2 books use cloud extraction, not V1 KU creation", "paragraphs_created": 0, "diagrams_created": 0, "qa_pairs_created": 0, "errors": None}

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


@router.get("/books/{book_id}/pipeline/page-status")
async def get_pipeline_page_status(book_id: int):
    """
    Get the pipeline status for all pages in a book.
    
    Returns status for each page with boolean flags for frontend compatibility:
    - layout_done: bool
    - extraction_done: bool
    - ku_created: bool
    - claude_done: bool
    """
    try:
        # V2 books don't have V1 raw paragraph/diagram tables
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"pages": []}

        # Validate book exists
        table_prefix = await _get_table_prefix(book_id)
        
        # Get page status from service
        page_status = get_page_ku_status(book_id)
        
        # Transform to frontend-expected format
        pages = []
        for status in page_status:
            pages.append({
                "page_number": status["page_number"],
                "layout_done": status["layout_status"] in ("detected", "ready"),
                "extraction_done": status["extraction_status"] == "completed",
                "ku_created": status["ku_status"] == "completed",
                "claude_done": status["claude_status"] == "completed",
                "claude_pending": status["claude_status"] == "pending" and status["ku_status"] == "completed",
                "ready_for_extraction": status.get("ready_for_extraction", False)
            })
        
        return {"pages": pages}
        
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
        
        # V2 books don't have V1 paragraph/diagram tables
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"pages": [], "message": "V2 books use cloud extraction"}

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


@router.get("/books/{book_id}/pipeline/ku-statistics")
async def get_ku_statistics(book_id: int):
    """
    Get statistics on items NOT yet created as Knowledge Units.
    
    Returns counts by type:
    - paragraphs: count of paragraphs without linked KU
    - diagrams: count of diagrams without linked KU
    - tables: count of tables without linked KU
    - equations: count of equations without linked KU
    - lists: count of lists (all types) without linked KU
    - questions: count of questions without linked KU
    - answers: count of answers without linked KU
    - total: total count of all items without linked KU
    """
    try:
        # V2 books don't have V1 raw paragraph/diagram tables
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"success": True, "statistics": {"paragraphs": 0, "diagrams": 0, "tables": 0, "equations": 0, "lists": 0, "questions": 0, "answers": 0, "captions": 0, "references": 0, "total": 0}, "has_items_to_process": False, "message": "V2 books use cloud extraction"}

        table_prefix = await _get_table_prefix(book_id)
        
        # Count unlinked paragraphs
        para_sql = text(f"""
            SELECT COUNT(*) 
            FROM raw_{table_prefix}_paragraph_images
            WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NULL
        """)
        
        # Count unlinked diagrams by type
        diag_sql = text(f"""
            SELECT 
                COALESCE(diagram_type, 'diagram') as dtype,
                COUNT(*) as cnt
            FROM raw_{table_prefix}_diagram_images
            WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NULL
            GROUP BY COALESCE(diagram_type, 'diagram')
        """)
        
        with engine.connect() as conn:
            para_count = conn.execute(para_sql).scalar() or 0
            
            diag_counts = {}
            for row in conn.execute(diag_sql).fetchall():
                dtype = row[0]
                cnt = row[1]
                diag_counts[dtype] = cnt
        
        # Aggregate list types
        list_count = sum(diag_counts.get(lt, 0) for lt in ['list_bulleted', 'list_numbered', 'list_lettered', 'list_item'])
        
        stats = {
            "paragraphs": para_count,
            "diagrams": diag_counts.get('diagram', 0),
            "tables": diag_counts.get('table', 0),
            "equations": diag_counts.get('equation', 0),
            "lists": list_count,
            "questions": diag_counts.get('question', 0),
            "answers": diag_counts.get('answer', 0),
            "captions": diag_counts.get('caption', 0),
            "references": diag_counts.get('reference', 0),
            "total": para_count + sum(diag_counts.values())
        }
        
        return {
            "success": True,
            "statistics": stats,
            "has_items_to_process": stats["total"] > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting KU statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books/{book_id}/pipeline/claude-analysis-statistics")
async def get_claude_analysis_statistics(book_id: int):
    """
    Get statistics on items that require Claude analysis.
    
    Items requiring Claude analysis are Knowledge Units where:
    - attr9_value (class type) is NOT 'paragraph' (paragraphs don't need Claude)
    - text_content is empty or NULL (Claude hasn't processed it yet)
    
    Returns counts by type:
    - diagrams: count needing analysis
    - tables: count needing analysis
    - equations: count needing analysis
    - lists: count needing analysis
    - questions: count needing analysis (Q&A pairs)
    - total: total count needing analysis
    """
    try:
        table_prefix = await _get_table_prefix(book_id)
        
        # V2 books don't have V1 knowledge_units table
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"types": {}, "total": 0, "message": "V2 books use cloud extraction"}

        # Count KUs by class type that need Claude analysis
        # These are non-paragraph KUs where text_content is empty/null
        sql = text(f"""
            SELECT 
                COALESCE(attr9_value, 'unknown') as class_type,
                COUNT(*) as cnt
            FROM {table_prefix}_knowledge_units
            WHERE attr9_value != 'paragraph'
            AND attr9_value IS NOT NULL
            AND (text_content IS NULL OR text_content = '')
            GROUP BY attr9_value
        """)
        
        with engine.connect() as conn:
            type_counts = {}
            for row in conn.execute(sql).fetchall():
                class_type = row[0]
                cnt = row[1]
                type_counts[class_type] = cnt
        
        # Aggregate list types
        list_count = sum(type_counts.get(lt, 0) for lt in ['list_bulleted', 'list_numbered', 'list_lettered', 'list_item'])
        
        stats = {
            "diagrams": type_counts.get('diagram', 0),
            "tables": type_counts.get('table', 0),
            "equations": type_counts.get('equation', 0),
            "lists": list_count,
            "question_answer": type_counts.get('question_answer', 0),
            "captions": type_counts.get('caption', 0),
            "references": type_counts.get('reference', 0),
            "total": sum(type_counts.values())
        }
        
        return {
            "success": True,
            "statistics": stats,
            "has_items_to_process": stats["total"] > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Claude analysis statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Execution Mode Endpoint (Requirement 7B)
# =============================================================================

@router.post("/books/{book_id}/pipeline/execute")
async def execute_pipeline(book_id: int, request: ExecutionRequest):
    """
    Execute pipeline with specified mode.
    
    Modes:
    - individual: Process each KU separately (default)
    - grouped: Process KUs in groups by L1/L2 title
    - incomplete: Retry only incomplete KUs
    
    Options:
    - dry_run: Preview without executing
    - save_preview_to: Attribute to save preview (for dry run)
    """
    try:
        # V2 books don't have V1 knowledge_units table
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"success": False, "message": "V2 books use cloud extraction, not V1 pipeline execution"}

        from src.services.ku_grouper_service import execute_grouped_pipeline
        
        result = execute_grouped_pipeline(
            book_id=book_id,
            step_id=1,  # TODO: Allow specifying step_id
            execution_mode=request.mode,
            dry_run=request.dry_run,
            save_preview_to=request.save_preview_to
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books/{book_id}/pipeline/incomplete-kus")
async def get_incomplete_kus(book_id: int):
    """
    Get list of incomplete KUs for retry.
    """
    try:
        # V2 books don't have V1 knowledge_units table
        from src.database.utils import get_extraction_method
        if get_extraction_method(book_id) == 'v2':
            return {"success": True, "incomplete_kus": [], "count": 0, "message": "V2 books use cloud extraction"}

        table_prefix = await _get_table_prefix(book_id)
        ku_table = f"{table_prefix}_knowledge_units"
        
        sql = text(f"""
            SELECT unit_id, chapter, topic, incomplete_reason
            FROM {ku_table}
            WHERE is_complete = FALSE
            ORDER BY chapter, topic, unit_id
        """)
        
        with engine.connect() as conn:
            results = conn.execute(sql).fetchall()
            
            kus = [
                {
                    "unit_id": row[0],
                    "chapter": row[1],
                    "topic": row[2],
                    "incomplete_reason": row[3]
                }
                for row in results
            ]
        
        return {
            "success": True,
            "incomplete_kus": kus,
            "count": len(kus)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incomplete KUs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
