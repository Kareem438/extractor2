"""
Unit tests for CHUNK-006: Pydantic Schemas

Tests Pydantic models for API request/response validation.

Test Coverage:
- Request schema validation
- Response schema validation
- Default values
- Optional fields handling
"""

import pytest
from pydantic import ValidationError
from datetime import datetime


class TestChunk006PydanticSchemas:
    """Test suite for CHUNK-006: Pydantic Schemas"""

    def test_happy_path_book_upload_request(self):
        """Test creating a valid BookUploadRequest"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            language_setting="auto",
            extraction_sensitivity="balanced",
            image_processing="all",
            ocr_quality="balanced",
            hierarchy_detection="auto"
        )

        assert request.book_name == "Test Book"
        assert request.language_setting == "auto"
        assert request.extraction_sensitivity == "balanced"

    def test_book_upload_request_defaults(self):
        """Test default values in BookUploadRequest"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(book_name="Test Book")

        assert request.language_setting == "auto"
        assert request.extraction_sensitivity == "balanced"
        assert request.image_processing == "all"
        assert request.ocr_quality == "balanced"
        assert request.hierarchy_detection == "auto"
        assert request.partial_processing_enabled is False
        assert request.special_instructions == ""

    def test_book_upload_request_optional_fields(self):
        """Test optional fields in BookUploadRequest"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            partial_processing_enabled=True,
            partial_processing_pages=50,
            special_instructions="Custom instructions"
        )

        assert request.partial_processing_enabled is True
        assert request.partial_processing_pages == 50
        assert request.special_instructions == "Custom instructions"

    def test_book_upload_request_attribute_keys(self):
        """Test attribute_keys dict in BookUploadRequest"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            attribute_keys={
                "2": "Difficulty Level",
                "3": "Topic Category",
                "4": "Learning Objective"
            }
        )

        assert len(request.attribute_keys) == 3
        assert request.attribute_keys["2"] == "Difficulty Level"

    def test_input_validation_missing_required_field(self):
        """Test validation error when required field is missing"""
        from src.database.schemas import BookUploadRequest

        with pytest.raises(ValidationError) as exc_info:
            BookUploadRequest()

        assert 'book_name' in str(exc_info.value)

    def test_input_validation_invalid_type(self):
        """Test validation error with invalid data type"""
        from src.database.schemas import BookUploadRequest

        with pytest.raises(ValidationError):
            BookUploadRequest(
                book_name="Test Book",
                partial_processing_enabled="not_a_boolean"
            )

    def test_happy_path_book_response(self):
        """Test creating a valid BookResponse"""
        from src.database.schemas import BookResponse

        response = BookResponse(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100,
            processing_status="uploaded",
            upload_date=datetime.now()
        )

        assert response.book_id == 1
        assert response.book_name == "Test Book"
        assert response.sanitized_name == "test_book"

    def test_book_response_from_orm(self):
        """Test BookResponse from_attributes config"""
        from src.database.schemas import BookResponse

        # Mock ORM object
        class MockBook:
            book_id = 1
            book_name = "Test Book"
            sanitized_name = "test_book"
            table_prefix = "book1_test_book"
            file_type = "PDF"
            file_size_bytes = 1024000
            total_pages = 100
            processing_status = "uploaded"
            upload_date = datetime.now()

        response = BookResponse.model_validate(MockBook())

        assert response.book_id == 1
        assert response.book_name == "Test Book"

    def test_edge_case_empty_attribute_keys(self):
        """Test request with empty attribute_keys dict"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            attribute_keys={}
        )

        assert request.attribute_keys == {}

    def test_edge_case_partial_processing_pages_none(self):
        """Test partial_processing_pages as None when disabled"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            partial_processing_enabled=False,
            partial_processing_pages=None
        )

        assert request.partial_processing_pages is None

    def test_schema_serialization_to_dict(self):
        """Test serializing schema to dictionary"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Book",
            language_setting="english"
        )

        data = request.model_dump()

        assert isinstance(data, dict)
        assert data['book_name'] == "Test Book"
        assert data['language_setting'] == "english"

    def test_schema_serialization_to_json(self):
        """Test serializing schema to JSON"""
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(book_name="Test Book")

        json_str = request.model_dump_json()

        assert isinstance(json_str, str)
        assert '"book_name":"Test Book"' in json_str.replace(" ", "")
