"""
Task Data Model

Represents a processing task for a single paragraph or diagram.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class Task(BaseModel):
    """Task model representing a single processing task"""

    # Identification
    id: int = Field(..., description="Task ID from database")
    entity_type: str = Field(..., description="'paragraph' or 'diagram'")
    entity_id: int = Field(..., description="ID in paragraph_images or diagram_images table")

    # Progress
    current_step: int = Field(default=1, description="Current step number (1-indexed)")
    total_steps: int = Field(..., description="Total number of steps in pipeline")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    priority: int = Field(default=0, description="Task priority (higher = first)")

    # Claude API caching
    api_response: Optional[Dict[str, Any]] = Field(default=None, description="Cached Claude response")
    api_called_at: Optional[datetime] = Field(default=None, description="When API was called")
    api_model_used: Optional[str] = Field(default=None, description="Claude model used")
    api_tokens_used: Optional[int] = Field(default=None, description="Tokens consumed")

    # Retry handling
    attempts: int = Field(default=0, description="Number of attempts made")
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    last_error: Optional[str] = Field(default=None, description="Last error message")

    # Timestamps
    created_at: datetime = Field(..., description="Task creation time")
    started_at: Optional[datetime] = Field(default=None, description="When task started")
    completed_at: Optional[datetime] = Field(default=None, description="When task completed")
    updated_at: datetime = Field(..., description="Last update time")

    # Book context
    table_prefix: str = Field(..., description="Table prefix for this book")
    book_id: int = Field(..., description="Book ID")

    class Config:
        use_enum_values = True
        from_attributes = True


class TaskProgress(BaseModel):
    """Task progress summary"""

    task_id: int
    entity_type: str
    entity_id: int
    current_step: int
    total_steps: int
    status: TaskStatus
    progress_percentage: float = Field(..., description="Progress as percentage (0-100)")
    estimated_remaining_seconds: Optional[int] = Field(default=None)

    class Config:
        use_enum_values = True
