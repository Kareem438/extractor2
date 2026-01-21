"""
Unit tests for CHUNK-027: Database Service - Processing State

Tests database service - processing state functionality.

Test Coverage:
- State updates
- Checkpoint saving
- Progress calculation
- Time estimation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestChunk027DatabaseServiceProcessingState:
    """Test suite for CHUNK-027: Database Service - Processing State"""

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_happy_path_state_updates(self, mock_get_table, mock_session_cls):
        """Test basic state updates"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock get_state to return current state
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_pages = 100
        mock_row.current_page = 0
        mock_row.avg_page_processing_time = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        updates = {
            'status': 'processing',
            'current_page': 50,
            'pages_processed': 49
        }

        success = service.update_state(book_id=1, updates=updates)

        assert success is True
        assert mock_db.execute.call_count == 2  # get_state + update
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called()

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_error_handling(self, mock_get_table, mock_session_cls):
        """Test error scenarios"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock database error during UPDATE
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        with pytest.raises(Exception, match="Database error"):
            service.update_state(book_id=1, updates={'status': 'error'})

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called()

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_edge_cases(self, mock_get_table, mock_session_cls):
        """Test boundary conditions"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock get_state to return state at 100% completion
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_pages = 100
        mock_row.current_page = 100
        mock_row.avg_page_processing_time = 2.5
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        # Test completion (100%)
        updates = {'current_page': 100}
        success = service.update_state(book_id=1, updates=updates)

        assert success is True
        # Should calculate 100% progress
        assert 'progress_percentage' in updates
        assert updates['progress_percentage'] == 100.0

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_input_validation(self, mock_get_table, mock_session_cls):
        """Test input validation"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock get_state
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_pages = 100
        mock_row.current_page = 0
        mock_row.avg_page_processing_time = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        # Empty updates should still work
        success = service.update_state(book_id=1, updates={})
        assert success is True

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_checkpoint_saving(self, mock_get_table, mock_session_cls):
        """Test checkpoint saving"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock get_state
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_pages = 100
        mock_row.current_page = 50
        mock_row.avg_page_processing_time = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        # Save checkpoint
        success = service.save_checkpoint(book_id=1, page_number=50)

        assert success is True
        mock_db.commit.assert_called_once()

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_progress_calculation(self, mock_get_table, mock_session_cls):
        """Test progress calculation"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Capture updates passed to execute
        executed_params = None
        def capture_execute(sql, params=None):
            nonlocal executed_params
            if params and 'progress_percentage' in str(sql):
                executed_params = params
            # Return mock for get_state
            mock_result = Mock()
            mock_row = Mock()
            mock_row.total_pages = 200
            mock_row.current_page = 0
            mock_row.avg_page_processing_time = None
            mock_result.fetchone.return_value = mock_row
            return mock_result

        mock_db.execute.side_effect = capture_execute

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        # Update to 50 out of 200 pages
        updates = {'current_page': 50}
        service.update_state(book_id=1, updates=updates)

        # Should calculate 25% progress
        assert 'progress_percentage' in updates
        assert updates['progress_percentage'] == 25.0

        # Update to 150 out of 200 pages
        updates = {'current_page': 150}
        service.update_state(book_id=1, updates=updates)

        # Should calculate 75% progress
        assert updates['progress_percentage'] == 75.0

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_time_estimation(self, mock_get_table, mock_session_cls):
        """Test time estimation"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock get_state with avg processing time
        mock_result = Mock()
        mock_row = Mock()
        mock_row.total_pages = 100
        mock_row.current_page = 25
        mock_row.avg_page_processing_time = 2.0  # 2 seconds per page
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        # Update with avg_page_processing_time
        updates = {
            'current_page': 25,
            'avg_page_processing_time': 2.0
        }

        service.update_state(book_id=1, updates=updates)

        # Should estimate remaining time: (100 - 25) * 2.0 = 150 seconds
        assert 'estimated_time_remaining' in updates
        assert updates['estimated_time_remaining'] == 150

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_get_state(self, mock_get_table, mock_session_cls):
        """Test retrieving processing state"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock database result with all fields
        mock_row = Mock()
        mock_row.status = 'processing'
        mock_row.current_page = 45
        mock_row.total_pages = 100
        mock_row.progress_percentage = 45.0
        mock_row.last_checkpoint_page = 40
        mock_row.checkpoint_frequency = 10
        mock_row.last_checkpoint_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.agent_states = {'reader': {'status': 'idle'}}
        mock_row.pages_processed = 44
        mock_row.knowledge_units_extracted = 132
        mock_row.images_extracted = 15
        mock_row.ocr_retry_count = 3
        mock_row.error_count = 1
        mock_row.avg_page_processing_time = 2.5
        mock_row.estimated_time_remaining = 137
        mock_row.last_error_message = None
        mock_row.last_error_at = None
        mock_row.paused_at = None
        mock_row.resumed_at = None
        mock_row.pause_count = 0
        mock_row.processing_started_at = datetime(2025, 1, 1, 10, 0, 0)
        mock_row.processing_completed_at = None
        mock_row.last_updated_at = datetime(2025, 1, 1, 12, 5, 0)

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()
        state = service.get_state(book_id=1)

        assert state['status'] == 'processing'
        assert state['current_page'] == 45
        assert state['total_pages'] == 100
        assert state['progress_percentage'] == 45.0
        assert state['pages_processed'] == 44
        assert state['knowledge_units_extracted'] == 132
        assert state['images_extracted'] == 15
        mock_db.close.assert_called_once()

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_get_state_not_found(self, mock_get_table, mock_session_cls):
        """Test get_state when state doesn't exist"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        # Mock no result
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        with pytest.raises(ValueError, match="Processing state not found"):
            service.get_state(book_id=1)

    @patch('src.database.services.processing_state_service.SessionLocal')
    @patch('src.database.services.processing_state_service.get_table_name')
    def test_increment_counters(self, mock_get_table, mock_session_cls):
        """Test atomic counter increments"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_processing_state'

        from src.database.services.processing_state_service import ProcessingStateService

        service = ProcessingStateService()

        counter_updates = {
            'pages_processed': 1,
            'knowledge_units_extracted': 3,
            'images_extracted': 2
        }

        success = service.increment_counters(book_id=1, counter_updates=counter_updates)

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
