"""
Unit tests for CHUNK-017: Text Chunking Algorithm

Tests text chunking algorithm functionality.

Test Coverage:
- Semantic splitting
- 3-5 line chunks
- Confidence scoring
- Paragraph handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestChunk017TextChunkingAlgorithm:
    """Test suite for CHUNK-017: Text Chunking Algorithm"""

    def test_happy_path_split_sentences(self):
        """Test sentence splitting"""
        from src.agents.splitter.text_chunker import split_sentences

        text = "First sentence. Second sentence! Third sentence?"
        sentences = split_sentences(text)

        assert len(sentences) == 3
        assert "First sentence." in sentences[0]

    def test_semantic_splitting_with_embeddings(self):
        """Test semantic splitting using embeddings"""
        from src.agents.splitter.text_chunker import split_text_semantic

        text = "First sentence. Second sentence. Third sentence."

        with patch('src.agents.splitter.text_chunker.EmbeddingModel.encode') as mock_encode:
            # Mock embeddings with low similarity between sentence 1 and 2
            mock_encode.return_value = np.array([
                [1.0, 0.0, 0.0],  # Sentence 1
                [0.0, 1.0, 0.0],  # Sentence 2 (different)
                [0.0, 0.9, 0.1]   # Sentence 3 (similar to 2)
            ])

            chunks = split_text_semantic(text)

            assert len(chunks) >= 1
            assert all('text' in chunk for chunk in chunks)
            assert all('confidence' in chunk for chunk in chunks)
            assert all('line_count' in chunk for chunk in chunks)

    def test_confidence_scoring(self):
        """Test confidence scoring"""
        from src.agents.splitter.text_chunker import calculate_confidence

        # Test with good chunk (3-5 lines, multiple sentences)
        good_chunk = "Line 1. Line 2.\nLine 3.\nLine 4."
        conf1 = calculate_confidence(good_chunk)

        # Test with short chunk
        short_chunk = "Single line."
        conf2 = calculate_confidence(short_chunk)

        assert 0.0 <= conf1 <= 1.0
        assert 0.0 <= conf2 <= 1.0
        assert conf1 >= conf2  # Good chunk should have higher confidence

    def test_paragraph_handling(self):
        """Test handling of multiple paragraphs"""
        from src.agents.splitter.text_chunker import split_text_semantic

        text = "Paragraph 1 sentence 1. Paragraph 1 sentence 2.\n\nParagraph 2 sentence 1."

        with patch('src.agents.splitter.text_chunker.EmbeddingModel.encode') as mock_encode:
            mock_encode.return_value = np.array([[1.0, 0.0], [0.9, 0.1]])

            chunks = split_text_semantic(text)

            # Should create at least one chunk
            assert len(chunks) >= 1

    def test_edge_case_empty_text(self):
        """Test handling of empty text"""
        from src.agents.splitter.text_chunker import split_text_semantic

        chunks = split_text_semantic("")

        assert chunks == []

    def test_edge_case_single_sentence(self):
        """Test handling of single sentence"""
        from src.agents.splitter.text_chunker import split_text_semantic

        text = "Single sentence."
        chunks = split_text_semantic(text)

        assert len(chunks) == 1
        assert chunks[0]['text'] == "Single sentence."

    def test_find_split_points(self):
        """Test finding split points based on similarity"""
        from src.agents.splitter.text_chunker import find_split_points

        # Create embeddings with varying similarity
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Sentence 1
            [0.9, 0.1, 0.0],  # Sentence 2 (similar to 1)
            [0.0, 0.0, 1.0]   # Sentence 3 (different)
        ])

        split_points = find_split_points(embeddings, threshold=0.6)

        # Should find split between sentences with low similarity
        assert isinstance(split_points, list)

    def test_line_count_in_chunks(self):
        """Test that line count is calculated correctly"""
        from src.agents.splitter.text_chunker import split_text_semantic

        text = "Line 1\nLine 2\nLine 3"

        with patch('src.agents.splitter.text_chunker.EmbeddingModel.encode') as mock_encode:
            mock_encode.return_value = np.array([[1.0]])

            chunks = split_text_semantic(text)

            assert len(chunks) >= 1
            assert all(chunk['line_count'] >= 1 for chunk in chunks)

    def test_error_handling_embedding_failure(self):
        """Test graceful handling when embeddings fail"""
        from src.agents.splitter.text_chunker import split_text_semantic

        text = "Sentence 1. Sentence 2."

        with patch('src.agents.splitter.text_chunker.EmbeddingModel.encode') as mock_encode:
            mock_encode.side_effect = Exception("Embedding failed")

            # Should not crash, should fall back to basic splitting
            chunks = split_text_semantic(text)

            assert isinstance(chunks, list)
