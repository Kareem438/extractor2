"""
Unit tests for CHUNK-030: Background Processing Task

Tests background processing task functionality.

Test Coverage:
- Background execution
- Page processing
- Pause/resume
- Checkpoint logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio


class TestChunk030BackgroundProcessingTask:
    """Test suite for CHUNK-030: Background Processing Task"""

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    @patch('src.api.background_processor.KnowledgeUnitService')
    @patch('src.api.background_processor.ImageService')
    @patch('src.api.background_processor.PageService')
    async def test_happy_path_background_execution(
        self, mock_page_svc, mock_img_svc, mock_ku_svc, mock_orchestrator,
        mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test background execution"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 3
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_instance.get_state.return_value = {'status': 'processing'}
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator
        mock_orch_instance = Mock()
        mock_orch_instance.process_page.return_value = {
            'knowledge_units': [{'text_content': 'test'}],
            'images': [],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }
        mock_orchestrator.return_value = mock_orch_instance

        # Mock services
        mock_ku_svc.return_value.insert_knowledge_units.return_value = None
        mock_img_svc.return_value.insert_images.return_value = None
        mock_page_svc.return_value.insert_page.return_value = None

        from src.api.background_processor import process_book_background

        # Run background processor
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        assert result is True
        assert mock_book.processing_status == 'completed'
        assert mock_orch_instance.process_page.call_count == 3
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    async def test_error_handling(
        self, mock_orchestrator, mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test error scenarios"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 3
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_instance.get_state.return_value = {'status': 'processing'}
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator to raise error
        mock_orchestrator.return_value.process_page.side_effect = Exception("Processing error")

        from src.api.background_processor import process_book_background

        # Run background processor - should handle error gracefully
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        assert result is False
        assert mock_book.processing_status == 'error'
        mock_state_instance.update_state.assert_called()

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    async def test_edge_cases(self, mock_settings_svc, mock_session_cls):
        """Test boundary conditions"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from src.api.background_processor import process_book_background

        # Should handle book not found
        result = await process_book_background(book_id=999, pdf_path='/test/book.pdf')
        assert result is False

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    async def test_input_validation(
        self, mock_orchestrator, mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test input validation"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book with 0 pages (edge case)
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 0
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_svc.return_value = mock_state_instance

        from src.api.background_processor import process_book_background

        # Should handle 0 pages gracefully
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        # Should complete successfully without processing any pages
        assert result is True
        assert mock_book.processing_status == 'completed'

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    @patch('src.api.background_processor.KnowledgeUnitService')
    @patch('src.api.background_processor.ImageService')
    @patch('src.api.background_processor.PageService')
    async def test_page_processing(
        self, mock_page_svc, mock_img_svc, mock_ku_svc, mock_orchestrator,
        mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test page processing"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 2
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_instance.get_state.return_value = {'status': 'processing'}
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator with different page data
        mock_orch_instance = Mock()
        page1_data = {
            'knowledge_units': [{'id': 1, 'text_content': 'Page 1 KU'}],
            'images': [{'image_id': 'IMG-001-00'}],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [{}], 'orange_rectangles': [{}]}
        }
        page2_data = {
            'knowledge_units': [{'id': 2, 'text_content': 'Page 2 KU'}],
            'images': [],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }
        mock_orch_instance.process_page.side_effect = [page1_data, page2_data]
        mock_orchestrator.return_value = mock_orch_instance

        # Mock services
        mock_ku_instance = Mock()
        mock_ku_svc.return_value = mock_ku_instance
        mock_img_instance = Mock()
        mock_img_svc.return_value = mock_img_instance
        mock_page_instance = Mock()
        mock_page_svc.return_value = mock_page_instance

        from src.api.background_processor import process_book_background

        # Run background processor
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        assert result is True
        # Should process both pages
        assert mock_orch_instance.process_page.call_count == 2
        # Should save KUs for both pages
        assert mock_ku_instance.insert_knowledge_units.call_count == 2
        # Should save images only for page 1
        assert mock_img_instance.insert_images.call_count == 1
        # Should save page data for both pages
        assert mock_page_instance.insert_page.call_count == 2

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    @patch('src.api.background_processor.KnowledgeUnitService')
    @patch('src.api.background_processor.ImageService')
    @patch('src.api.background_processor.PageService')
    async def test_pause_resume(
        self, mock_page_svc, mock_img_svc, mock_ku_svc, mock_orchestrator,
        mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test pause/resume"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 5
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service - return 'paused' after 2 pages
        mock_state_instance = Mock()
        mock_state_instance.get_state.side_effect = [
            {'status': 'processing'},
            {'status': 'processing'},
            {'status': 'paused'},  # Pause signal
        ]
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator
        mock_orch_instance = Mock()
        mock_orch_instance.process_page.return_value = {
            'knowledge_units': [],
            'images': [],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }
        mock_orchestrator.return_value = mock_orch_instance

        # Mock services
        mock_ku_svc.return_value.insert_knowledge_units.return_value = None
        mock_img_svc.return_value.insert_images.return_value = None
        mock_page_svc.return_value.insert_page.return_value = None

        from src.api.background_processor import process_book_background

        # Run background processor
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        # Should return False (paused, not completed)
        assert result is False
        # Should have processed only 2 pages before pausing
        assert mock_orch_instance.process_page.call_count == 2
        # Status should be paused
        assert mock_book.processing_status == 'paused'

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    @patch('src.api.background_processor.KnowledgeUnitService')
    @patch('src.api.background_processor.ImageService')
    @patch('src.api.background_processor.PageService')
    async def test_checkpoint_logic(
        self, mock_page_svc, mock_img_svc, mock_ku_svc, mock_orchestrator,
        mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test checkpoint logic"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 25
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings with checkpoint_frequency = 10
        mock_settings = {
            'partial_processing_enabled': False,
            'partial_processing_pages': None,
            'checkpoint_frequency': 10  # Save checkpoint every 10 pages
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_instance.get_state.return_value = {'status': 'processing'}
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator
        mock_orch_instance = Mock()
        mock_orch_instance.process_page.return_value = {
            'knowledge_units': [],
            'images': [],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }
        mock_orchestrator.return_value = mock_orch_instance

        # Mock services
        mock_ku_svc.return_value.insert_knowledge_units.return_value = None
        mock_img_svc.return_value.insert_images.return_value = None
        mock_page_svc.return_value.insert_page.return_value = None

        from src.api.background_processor import process_book_background

        # Run background processor
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        assert result is True
        # Should process all 25 pages
        assert mock_orch_instance.process_page.call_count == 25
        # Should save checkpoints at pages 10 and 20 (2 checkpoints total)
        assert mock_state_instance.save_checkpoint.call_count == 2
        # Verify checkpoint calls at correct pages
        checkpoint_calls = [call[0][1] for call in mock_state_instance.save_checkpoint.call_args_list]
        assert 10 in checkpoint_calls
        assert 20 in checkpoint_calls

    @pytest.mark.asyncio
    @patch('src.api.background_processor.SessionLocal')
    @patch('src.api.background_processor.BookSettingsService')
    @patch('src.api.background_processor.ProcessingStateService')
    @patch('src.api.background_processor.AgentOrchestrator')
    @patch('src.api.background_processor.KnowledgeUnitService')
    @patch('src.api.background_processor.ImageService')
    @patch('src.api.background_processor.PageService')
    async def test_partial_processing(
        self, mock_page_svc, mock_img_svc, mock_ku_svc, mock_orchestrator,
        mock_state_svc, mock_settings_svc, mock_session_cls
    ):
        """Test partial processing (first N pages only)"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db

        # Mock book metadata with 100 pages
        mock_book = Mock()
        mock_book.book_id = 1
        mock_book.total_pages = 100
        mock_book.processing_status = 'uploaded'
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        # Mock settings with partial processing enabled (first 10 pages only)
        mock_settings = {
            'partial_processing_enabled': True,
            'partial_processing_pages': 10,
            'checkpoint_frequency': 50
        }
        mock_settings_svc.return_value.get_settings.return_value = mock_settings

        # Mock state service
        mock_state_instance = Mock()
        mock_state_instance.get_state.return_value = {'status': 'processing'}
        mock_state_svc.return_value = mock_state_instance

        # Mock orchestrator
        mock_orch_instance = Mock()
        mock_orch_instance.process_page.return_value = {
            'knowledge_units': [],
            'images': [],
            'page_image': Mock(),
            'marked_image': Mock(),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }
        mock_orchestrator.return_value = mock_orch_instance

        # Mock services
        mock_ku_svc.return_value.insert_knowledge_units.return_value = None
        mock_img_svc.return_value.insert_images.return_value = None
        mock_page_svc.return_value.insert_page.return_value = None

        from src.api.background_processor import process_book_background

        # Run background processor
        result = await process_book_background(book_id=1, pdf_path='/test/book.pdf')

        assert result is True
        # Should process only 10 pages (not all 100)
        assert mock_orch_instance.process_page.call_count == 10
