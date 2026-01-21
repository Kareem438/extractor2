"""
Unit Tests for Sequential OCR Routes

Tests the sequential OCR API endpoints:
- POST /api/ocr/paddleocr
- POST /api/ocr/surya
- POST /api/ocr/tesseract
- POST /api/evaluate-split-mark
- GET /api/ocr/status/{book_id}

Aligned with sequential-ocr-svg-processing.md architecture.
"""

import pytest
import inspect
from src.api.routes import ocr


class TestSequentialOCRRoutes:
    """Test suite for sequential OCR routes"""

    def test_happy_path_ocr_router_exists(self):
        """Test that OCR router exists and is properly configured"""
        assert hasattr(ocr, 'router')
        assert ocr.router is not None

    def test_happy_path_paddleocr_endpoint_exists(self):
        """Test that PaddleOCR endpoint exists"""
        assert hasattr(ocr, 'start_paddleocr')
        assert callable(ocr.start_paddleocr)

    def test_happy_path_surya_endpoint_exists(self):
        """Test that Surya OCR endpoint exists"""
        assert hasattr(ocr, 'start_surya')
        assert callable(ocr.start_surya)

    def test_happy_path_tesseract_endpoint_exists(self):
        """Test that Tesseract endpoint exists"""
        assert hasattr(ocr, 'start_tesseract')
        assert callable(ocr.start_tesseract)

    def test_happy_path_evaluate_endpoint_exists(self):
        """Test that evaluate/split/mark endpoint exists"""
        assert hasattr(ocr, 'evaluate_split_mark')
        assert callable(ocr.evaluate_split_mark)

    def test_happy_path_status_endpoint_exists(self):
        """Test that status endpoint exists"""
        assert hasattr(ocr, 'get_ocr_status')
        assert callable(ocr.get_ocr_status)

    def test_structure_ocr_request_model(self):
        """Test that OCRRequest model has required fields"""
        assert hasattr(ocr, 'OCRRequest')
        model_source = inspect.getsource(ocr.OCRRequest)
        assert 'book_id' in model_source

    def test_structure_ocr_response_model(self):
        """Test that OCRResponse model has required fields"""
        assert hasattr(ocr, 'OCRResponse')
        model_source = inspect.getsource(ocr.OCRResponse)
        assert 'book_id' in model_source
        assert 'status' in model_source
        assert 'message' in model_source

    def test_structure_paddleocr_uses_background_tasks(self):
        """Test that PaddleOCR endpoint uses background tasks"""
        source = inspect.getsource(ocr.start_paddleocr)
        assert 'BackgroundTasks' in source
        assert 'background_tasks.add_task' in source

    def test_structure_surya_uses_background_tasks(self):
        """Test that Surya endpoint uses background tasks"""
        source = inspect.getsource(ocr.start_surya)
        assert 'BackgroundTasks' in source
        assert 'background_tasks.add_task' in source

    def test_structure_tesseract_uses_background_tasks(self):
        """Test that Tesseract endpoint uses background tasks"""
        source = inspect.getsource(ocr.start_tesseract)
        assert 'BackgroundTasks' in source
        assert 'background_tasks.add_task' in source

    def test_structure_evaluate_uses_background_tasks(self):
        """Test that evaluate endpoint uses background tasks"""
        source = inspect.getsource(ocr.evaluate_split_mark)
        assert 'BackgroundTasks' in source
        assert 'background_tasks.add_task' in source

    def test_error_handling_paddleocr(self):
        """Test that PaddleOCR endpoint has error handling"""
        source = inspect.getsource(ocr.start_paddleocr)
        assert 'try:' in source or 'except' in source
        assert 'HTTPException' in source

    def test_error_handling_surya(self):
        """Test that Surya endpoint has error handling"""
        source = inspect.getsource(ocr.start_surya)
        assert 'try:' in source or 'except' in source
        assert 'HTTPException' in source

    def test_error_handling_tesseract(self):
        """Test that Tesseract endpoint has error handling"""
        source = inspect.getsource(ocr.start_tesseract)
        assert 'try:' in source or 'except' in source
        assert 'HTTPException' in source

    def test_error_handling_evaluate(self):
        """Test that evaluate endpoint has error handling"""
        source = inspect.getsource(ocr.evaluate_split_mark)
        assert 'try:' in source or 'except' in source
        assert 'HTTPException' in source

    def test_error_handling_status(self):
        """Test that status endpoint has error handling"""
        source = inspect.getsource(ocr.get_ocr_status)
        assert 'try:' in source or 'except' in source
        assert 'HTTPException' in source

    def test_endpoint_logging_paddleocr(self):
        """Test that PaddleOCR endpoint has logging"""
        source = inspect.getsource(ocr.start_paddleocr)
        assert 'logger' in source

    def test_endpoint_logging_surya(self):
        """Test that Surya endpoint has logging"""
        source = inspect.getsource(ocr.start_surya)
        assert 'logger' in source

    def test_endpoint_logging_tesseract(self):
        """Test that Tesseract endpoint has logging"""
        source = inspect.getsource(ocr.start_tesseract)
        assert 'logger' in source

    def test_endpoint_logging_evaluate(self):
        """Test that evaluate endpoint has logging"""
        source = inspect.getsource(ocr.evaluate_split_mark)
        assert 'logger' in source

    def test_endpoint_logging_status(self):
        """Test that status endpoint has logging"""
        source = inspect.getsource(ocr.get_ocr_status)
        assert 'logger' in source
