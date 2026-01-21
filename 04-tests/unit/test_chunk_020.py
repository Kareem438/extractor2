"""
Unit tests for CHUNK-020: Splitter Agent - Main Logic

Tests splitter agent - main logic functionality.

Test Coverage:
- Text splitting
- Knowledge unit creation
- Empty text handling
- Metadata assignment
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestChunk020SplitterAgentMainLogic:
    """Test suite for CHUNK-020: Splitter Agent - Main Logic"""

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_happy_path_text_splitting(self, mock_detect_lang, mock_split):
        """Test text splitting"""
        # Mock semantic chunker
        mock_split.return_value = [
            {'text': 'First chunk.', 'confidence': 0.8, 'line_count': 3},
            {'text': 'Second chunk.', 'confidence': 0.9, 'line_count': 4}
        ]
        mock_detect_lang.return_value = 'english'

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Sample text for splitting.", page_number=1)

        assert len(units) == 2
        assert units[0]['text_content'] == 'First chunk.'
        assert units[1]['text_content'] == 'Second chunk.'

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_knowledge_unit_creation(self, mock_detect_lang, mock_split):
        """Test knowledge unit format"""
        mock_split.return_value = [
            {'text': 'Test chunk.', 'confidence': 0.85, 'line_count': 3}
        ]
        mock_detect_lang.return_value = 'english'

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Test text.", page_number=5)

        assert len(units) == 1
        unit = units[0]

        # Verify all required fields
        assert 'text_content' in unit
        assert 'text_length' in unit
        assert 'line_count' in unit
        assert 'page_number' in unit
        assert 'confidence_score' in unit
        assert 'language' in unit

        # Verify values
        assert unit['text_content'] == 'Test chunk.'
        assert unit['text_length'] == len('Test chunk.')
        assert unit['line_count'] == 3
        assert unit['page_number'] == 5
        assert unit['confidence_score'] == 0.85
        assert unit['language'] == 'english'

    def test_empty_text_handling(self):
        """Test handling of empty text"""
        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()

        # Test empty string
        units1 = agent.split_text("", page_number=1)
        assert units1 == []

        # Test None
        units2 = agent.split_text(None, page_number=1)
        assert units2 == []

        # Test whitespace only
        units3 = agent.split_text("   \n\t  ", page_number=1)
        assert units3 == []

    def test_short_text_handling(self):
        """Test handling of very short text (< 10 chars)"""
        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Short", page_number=1)

        assert units == []

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_metadata_assignment(self, mock_detect_lang, mock_split):
        """Test that metadata is correctly assigned"""
        mock_split.return_value = [
            {'text': 'Chunk 1', 'confidence': 0.7, 'line_count': 2},
            {'text': 'Chunk 2', 'confidence': 0.9, 'line_count': 5}
        ]
        mock_detect_lang.side_effect = ['english', 'arabic']

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Test text.", page_number=10)

        # Check first unit
        assert units[0]['page_number'] == 10
        assert units[0]['confidence_score'] == 0.7
        assert units[0]['language'] == 'english'

        # Check second unit
        assert units[1]['page_number'] == 10
        assert units[1]['confidence_score'] == 0.9
        assert units[1]['language'] == 'arabic'

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_text_length_calculation(self, mock_detect_lang, mock_split):
        """Test that text_length is correctly calculated"""
        test_text = "This is a test chunk with some length."
        mock_split.return_value = [
            {'text': test_text, 'confidence': 0.8, 'line_count': 1}
        ]
        mock_detect_lang.return_value = 'english'

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Test text with enough length", page_number=1)

        assert units[0]['text_length'] == len(test_text)

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_line_count_preservation(self, mock_detect_lang, mock_split):
        """Test that line_count from chunker is preserved"""
        mock_split.return_value = [
            {'text': 'Line 1\nLine 2\nLine 3', 'confidence': 0.8, 'line_count': 3}
        ]
        mock_detect_lang.return_value = 'english'

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()
        units = agent.split_text("Test text with enough length", page_number=1)

        assert units[0]['line_count'] == 3

    @patch('src.agents.splitter.splitter_agent.split_text_semantic')
    @patch('src.agents.splitter.splitter_agent.detect_language')
    def test_multiple_chunks_different_pages(self, mock_detect_lang, mock_split):
        """Test splitting on different pages"""
        mock_split.return_value = [
            {'text': 'Chunk', 'confidence': 0.8, 'line_count': 1}
        ]
        mock_detect_lang.return_value = 'english'

        from src.agents.splitter.splitter_agent import SplitterAgent

        agent = SplitterAgent()

        # Split on page 1
        units1 = agent.split_text("Text with enough length for page 1", page_number=1)
        assert units1[0]['page_number'] == 1

        # Split on page 5
        units2 = agent.split_text("Text with enough length for page 5", page_number=5)
        assert units2[0]['page_number'] == 5
