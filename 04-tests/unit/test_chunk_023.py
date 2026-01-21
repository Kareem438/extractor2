"""
Unit tests for CHUNK-023: Agent Orchestrator - Sequential Execution

Tests agent orchestrator - sequential execution functionality.

Test Coverage:
- Page processing
- Agent coordination
- Data flow
- Error propagation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk023AgentOrchestratorSequentialExecution:
    """Test suite for CHUNK-023: Agent Orchestrator - Sequential Execution"""

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_happy_path_page_processing(self, mock_pdf_to_img, mock_img_agent_cls,
                                       mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test complete page processing through all agents"""
        # Mock agent instances
        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        # Mock agent outputs
        mock_reader.read_page.return_value = {
            'text': 'Sample text from page',
            'language': 'english',
            'confidence': 100.0,
            'extraction_method': 'native_text'
        }

        mock_splitter.split_text.return_value = [
            {'text_content': 'Sample text', 'page_number': 1, 'language': 'english'}
        ]

        mock_img_agent.extract_images.return_value = [
            {'image_id': 'IMG-001-00', 'ai_description': 'A diagram'}
        ]

        test_page_image = Image.new('RGB', (100, 100), color='white')
        mock_pdf_to_img.return_value = test_page_image

        test_marked_image = Image.new('RGB', (100, 100), color='green')
        mock_marker.create_markers.return_value = (
            test_marked_image,
            {'green_rectangles': [], 'orange_rectangles': []}
        )

        from src.agents.orchestrator import AgentOrchestrator

        # Create orchestrator
        settings = {'language_setting': 'auto', 'ocr_quality': 'balanced'}
        orchestrator = AgentOrchestrator(book_id=1, pdf_path='/path/to/file.pdf', settings=settings)

        # Process page
        result = orchestrator.process_page(page_number=1)

        # Verify result structure
        assert result['page_number'] == 1
        assert 'text_data' in result
        assert 'knowledge_units' in result
        assert 'images' in result
        assert 'page_image' in result
        assert 'marked_image' in result
        assert 'rectangle_data' in result

        # Verify agents were called
        mock_reader.read_page.assert_called_once_with(
            '/path/to/file.pdf', 1,
            language_setting='auto',
            ocr_quality='balanced'
        )
        mock_splitter.split_text.assert_called_once_with('Sample text from page', 1)
        mock_img_agent.extract_images.assert_called_once_with('/path/to/file.pdf', 1)
        mock_pdf_to_img.assert_called_once_with('/path/to/file.pdf', 1)
        mock_marker.create_markers.assert_called_once()

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_agent_coordination_order(self, mock_pdf_to_img, mock_img_agent_cls,
                                     mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test that agents are called in correct order"""
        # Track call order
        call_order = []

        def reader_read(*args, **kwargs):
            call_order.append('reader')
            return {'text': 'Text', 'language': 'english', 'confidence': 100.0, 'extraction_method': 'native'}

        def splitter_split(*args, **kwargs):
            call_order.append('splitter')
            return []

        def img_extract(*args, **kwargs):
            call_order.append('image_reader')
            return []

        def pdf_to_img(*args, **kwargs):
            call_order.append('pdf_to_image')
            return Image.new('RGB', (100, 100))

        def marker_create(*args, **kwargs):
            call_order.append('marker')
            return (Image.new('RGB', (100, 100)), {'green_rectangles': [], 'orange_rectangles': []})

        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader.read_page.side_effect = reader_read
        mock_splitter.split_text.side_effect = splitter_split
        mock_img_agent.extract_images.side_effect = img_extract
        mock_pdf_to_img.side_effect = pdf_to_img
        mock_marker.create_markers.side_effect = marker_create

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        from src.agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(1, '/path/to/file.pdf', {'language_setting': 'auto', 'ocr_quality': 'balanced'})
        orchestrator.process_page(1)

        # Verify correct order
        assert call_order == ['reader', 'splitter', 'image_reader', 'pdf_to_image', 'marker']

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_data_flow_between_agents(self, mock_pdf_to_img, mock_img_agent_cls,
                                     mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test that data flows correctly between agents"""
        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        # Reader returns text
        extracted_text = "This is extracted text from the PDF"
        mock_reader.read_page.return_value = {
            'text': extracted_text,
            'language': 'english',
            'confidence': 95.0,
            'extraction_method': 'native_text'
        }

        # Splitter returns knowledge units
        knowledge_units = [
            {'text_content': 'Unit 1', 'page_number': 5},
            {'text_content': 'Unit 2', 'page_number': 5}
        ]
        mock_splitter.split_text.return_value = knowledge_units

        # Image reader returns images
        images = [{'image_id': 'IMG-005-00'}]
        mock_img_agent.extract_images.return_value = images

        page_image = Image.new('RGB', (200, 200))
        mock_pdf_to_img.return_value = page_image

        marked_image = Image.new('RGB', (200, 200), color='blue')
        mock_marker.create_markers.return_value = (
            marked_image,
            {'green_rectangles': [{'x': 10}], 'orange_rectangles': []}
        )

        from src.agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(1, '/path/to/file.pdf', {'language_setting': 'english', 'ocr_quality': 'high'})
        result = orchestrator.process_page(5)

        # Verify splitter received reader's text
        mock_splitter.split_text.assert_called_once_with(extracted_text, 5)

        # Verify marker received knowledge units and images
        call_args = mock_marker.create_markers.call_args[0]
        assert call_args[0] == page_image
        assert call_args[1] == knowledge_units
        assert call_args[2] == images

        # Verify result contains all data
        assert result['text_data']['text'] == extracted_text
        assert result['knowledge_units'] == knowledge_units
        assert result['images'] == images
        assert result['marked_image'] == marked_image

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_settings_propagation(self, mock_pdf_to_img, mock_img_agent_cls,
                                  mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test that settings are passed correctly to agents"""
        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        mock_reader.read_page.return_value = {'text': 'Text', 'language': 'arabic', 'confidence': 90.0, 'extraction_method': 'ocr'}
        mock_splitter.split_text.return_value = []
        mock_img_agent.extract_images.return_value = []
        mock_pdf_to_img.return_value = Image.new('RGB', (100, 100))
        mock_marker.create_markers.return_value = (Image.new('RGB', (100, 100)), {'green_rectangles': [], 'orange_rectangles': []})

        from src.agents.orchestrator import AgentOrchestrator

        # Custom settings
        settings = {
            'language_setting': 'arabic',
            'ocr_quality': 'high'
        }

        orchestrator = AgentOrchestrator(1, '/path/to/file.pdf', settings)
        orchestrator.process_page(1)

        # Verify settings were passed to reader
        mock_reader.read_page.assert_called_once_with(
            '/path/to/file.pdf', 1,
            language_setting='arabic',
            ocr_quality='high'
        )

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_default_settings(self, mock_pdf_to_img, mock_img_agent_cls,
                             mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test that default settings are used when not specified"""
        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        mock_reader.read_page.return_value = {'text': 'Text', 'language': 'english', 'confidence': 100.0, 'extraction_method': 'native'}
        mock_splitter.split_text.return_value = []
        mock_img_agent.extract_images.return_value = []
        mock_pdf_to_img.return_value = Image.new('RGB', (100, 100))
        mock_marker.create_markers.return_value = (Image.new('RGB', (100, 100)), {'green_rectangles': [], 'orange_rectangles': []})

        from src.agents.orchestrator import AgentOrchestrator

        # Empty settings
        orchestrator = AgentOrchestrator(1, '/path/to/file.pdf', {})
        orchestrator.process_page(1)

        # Verify defaults were used
        mock_reader.read_page.assert_called_once_with(
            '/path/to/file.pdf', 1,
            language_setting='auto',
            ocr_quality='balanced'
        )

    @patch('src.agents.orchestrator.ReaderAgent')
    @patch('src.agents.orchestrator.SplitterAgent')
    @patch('src.agents.orchestrator.MarkerAgent')
    @patch('src.agents.orchestrator.ImageReaderAgent')
    @patch('src.agents.orchestrator.pdf_page_to_image')
    def test_multiple_pages(self, mock_pdf_to_img, mock_img_agent_cls,
                           mock_marker_cls, mock_splitter_cls, mock_reader_cls):
        """Test processing multiple pages"""
        mock_reader = Mock()
        mock_splitter = Mock()
        mock_marker = Mock()
        mock_img_agent = Mock()

        mock_reader_cls.return_value = mock_reader
        mock_splitter_cls.return_value = mock_splitter
        mock_marker_cls.return_value = mock_marker
        mock_img_agent_cls.return_value = mock_img_agent

        mock_reader.read_page.return_value = {'text': 'Text', 'language': 'english', 'confidence': 100.0, 'extraction_method': 'native'}
        mock_splitter.split_text.return_value = []
        mock_img_agent.extract_images.return_value = []
        mock_pdf_to_img.return_value = Image.new('RGB', (100, 100))
        mock_marker.create_markers.return_value = (Image.new('RGB', (100, 100)), {'green_rectangles': [], 'orange_rectangles': []})

        from src.agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(1, '/path/to/file.pdf', {'language_setting': 'auto', 'ocr_quality': 'balanced'})

        # Process multiple pages
        result1 = orchestrator.process_page(1)
        result2 = orchestrator.process_page(2)
        result3 = orchestrator.process_page(3)

        assert result1['page_number'] == 1
        assert result2['page_number'] == 2
        assert result3['page_number'] == 3

        # Each page should call agents once
        assert mock_reader.read_page.call_count == 3
        assert mock_splitter.split_text.call_count == 3
        assert mock_img_agent.extract_images.call_count == 3
