"""
Pipeline Step Data Model

Represents a single step in the pipeline configuration.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Step status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStep(BaseModel):
    """Pipeline step configuration"""

    # Identification
    id: int = Field(..., description="Step ID from database")
    step_order: int = Field(..., description="Step execution order")
    step_name: str = Field(..., description="Human-readable step name")

    # Prompt Configuration
    prompt_template: Optional[str] = Field(default=None, description="Prompt with template variables")

    # Input/Output Configuration
    input_source: str = Field(..., description="'postgresql' or 'chromadb'")
    input_field: Optional[str] = Field(default=None, description="Column name or operation")
    input_params: Optional[Dict[str, Any]] = Field(default=None, description="Additional input parameters")

    output_destination: str = Field(..., description="'postgresql' or 'chromadb'")
    output_field: Optional[str] = Field(default=None, description="Column name or operation")

    # Claude Configuration
    claude_model: Optional[str] = Field(default=None, description="Claude model or None for no API call")

    # Application Rules
    applies_to: str = Field(default="paragraphs", description="'paragraphs', 'diagrams', or 'both'")
    on_failure: str = Field(default="skip_remaining", description="'skip_remaining' or 'continue'")

    # Status
    is_active: bool = Field(default=True, description="Whether step is active")

    # Timestamps
    created_at: datetime = Field(..., description="Step creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        use_enum_values = True
        from_attributes = True


class StepProgress(BaseModel):
    """Step execution progress for a specific entity"""

    # Identification
    id: int = Field(..., description="Progress record ID")
    entity_type: str = Field(..., description="'paragraph' or 'diagram'")
    entity_id: int = Field(..., description="Entity ID")
    step_order: int = Field(..., description="Step number")
    step_name: str = Field(..., description="Step name")

    # Status
    status: StepStatus = Field(default=StepStatus.PENDING, description="Step execution status")

    # Results
    api_response: Optional[Dict[str, Any]] = Field(default=None, description="Claude API response")
    output_value: Optional[str] = Field(default=None, description="Value written to output field")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    # Timing
    started_at: Optional[datetime] = Field(default=None, description="When step started")
    completed_at: Optional[datetime] = Field(default=None, description="When step completed")
    duration_ms: Optional[int] = Field(default=None, description="Execution duration in milliseconds")

    # Timestamps
    created_at: datetime = Field(..., description="Record creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        use_enum_values = True
        from_attributes = True
