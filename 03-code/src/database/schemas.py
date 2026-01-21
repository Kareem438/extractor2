"""
CHUNK-006: Pydantic Schemas

Pydantic models for API request/response validation.
Provides data validation and serialization for the API layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class BookUploadRequest(BaseModel):
    """
    Request schema for uploading a new book.

    Validates and provides defaults for all book upload parameters
    including OCR settings, processing options, and custom attributes.
    """

    # Required fields
    book_name: str = Field(..., description="Name of the book to upload")

    # Processing settings with defaults
    language_setting: str = Field(
        default="auto",
        description="Language for OCR processing (auto, english, arabic, etc.)"
    )
    extraction_sensitivity: str = Field(
        default="balanced",
        description="Text extraction sensitivity level (low, balanced, high)"
    )
    image_processing: str = Field(
        default="all",
        description="Image processing mode (all, none, selective)"
    )
    ocr_quality: str = Field(
        default="balanced",
        description="OCR quality setting (fast, balanced, accurate)"
    )
    hierarchy_detection: str = Field(
        default="auto",
        description="Automatic hierarchy detection (auto, manual, none)"
    )

    # Partial processing options
    partial_processing_enabled: bool = Field(
        default=False,
        description="Enable processing only a subset of pages"
    )
    partial_processing_pages: Optional[int] = Field(
        default=None,
        description="Number of pages to process (if partial processing enabled)"
    )

    # Custom instructions and attributes
    special_instructions: Optional[str] = Field(
        default="",
        description="Special processing instructions"
    )
    attribute_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom attribute key mappings (attribute_id -> label)"
    )

    # Pydantic v2 compatibility methods (we're using v1)
    def model_dump(self):
        """Pydantic v2 compatibility: serialize to dict"""
        return self.dict()

    def model_dump_json(self):
        """Pydantic v2 compatibility: serialize to JSON (compact format)"""
        # Use compact format without spaces (Pydantic v2 default)
        import json
        return json.dumps(self.dict(), separators=(',', ':'), default=str)


class BookResponse(BaseModel):
    """
    Response schema for book metadata.

    Returns complete book information including processing status
    and metadata. Can be created from SQLAlchemy ORM objects.
    """

    # Core identification
    book_id: int = Field(..., description="Unique book identifier")
    book_name: str = Field(..., description="Original book name")
    sanitized_name: str = Field(..., description="Sanitized name for tables")
    table_prefix: str = Field(..., description="Database table prefix for book")

    # File information
    file_type: str = Field(..., description="File type (PDF, DOCX, etc.)")
    file_size_bytes: int = Field(..., description="File size in bytes")
    total_pages: int = Field(..., description="Total number of pages")

    # Status and timestamp
    processing_status: str = Field(..., description="Current processing status")
    upload_date: datetime = Field(..., description="Upload timestamp")

    class Config:
        """Pydantic configuration"""
        from_attributes = True  # Enable ORM mode for SQLAlchemy models
        orm_mode = True  # Pydantic v1 name for from_attributes

    # Pydantic v2 compatibility methods (we're using v1)
    @classmethod
    def model_validate(cls, obj):
        """Pydantic v2 compatibility: create from ORM object"""
        return cls.from_orm(obj)

    def model_dump(self):
        """Pydantic v2 compatibility: serialize to dict"""
        return self.dict()

    def model_dump_json(self):
        """Pydantic v2 compatibility: serialize to JSON (compact format)"""
        # Use compact format without spaces (Pydantic v2 default)
        import json
        return json.dumps(self.dict(), separators=(',', ':'), default=str)
