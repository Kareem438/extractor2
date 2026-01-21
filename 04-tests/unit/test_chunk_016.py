"""
Unit tests for CHUNK-016: Sentence Transformer Loader

Tests sentence transformer loader functionality.

Test Coverage:
- Model loading
- Embedding generation
- Singleton pattern
- Cache directory
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestChunk016SentenceTransformerLoader:
    """Test suite for CHUNK-016: Sentence Transformer Loader"""

    def setup_method(self):
        """Reset singleton before each test"""
        from src.agents.splitter.embedding_model import EmbeddingModel
        EmbeddingModel.reset_model()

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    @patch('src.agents.splitter.embedding_model.logger')
    def test_happy_path_model_loading(self, mock_logger, mock_st):
        """Test model loading"""
        mock_model = Mock()
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        model = EmbeddingModel.get_model()

        assert model == mock_model
        mock_logger.info.assert_called()
        mock_st.assert_called_once()

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    def test_singleton_pattern(self, mock_st):
        """Test that model is loaded only once (singleton)"""
        mock_model = Mock()
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        # Call get_model twice
        model1 = EmbeddingModel.get_model()
        model2 = EmbeddingModel.get_model()

        # Should be same instance
        assert model1 is model2
        # SentenceTransformer should be called only once
        assert mock_st.call_count == 1

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    @patch('src.agents.splitter.embedding_model.settings')
    def test_cache_directory(self, mock_settings, mock_st):
        """Test that cache directory from settings is used"""
        mock_settings.MODEL_CACHE_DIR = '/test/cache/dir'
        mock_model = Mock()
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        EmbeddingModel.get_model()

        # Verify cache_folder was passed
        call_kwargs = mock_st.call_args[1]
        assert call_kwargs['cache_folder'] == '/test/cache/dir'

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    def test_embedding_generation(self, mock_st):
        """Test embedding generation"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        texts = ["Hello", "World"]
        embeddings = EmbeddingModel.encode(texts)

        assert np.array_equal(embeddings, mock_embeddings)
        mock_model.encode.assert_called_once_with(texts, show_progress_bar=False)

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    def test_model_name(self, mock_st):
        """Test that correct model name is used"""
        mock_model = Mock()
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        EmbeddingModel.get_model()

        # Verify model name
        call_args = mock_st.call_args[0]
        assert call_args[0] == 'paraphrase-multilingual-MiniLM-L12-v2'

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    def test_reset_model(self, mock_st):
        """Test that reset_model clears singleton"""
        mock_model1 = Mock()
        mock_model2 = Mock()
        mock_st.side_effect = [mock_model1, mock_model2]

        from src.agents.splitter.embedding_model import EmbeddingModel

        # Load model
        model1 = EmbeddingModel.get_model()
        assert model1 == mock_model1

        # Reset
        EmbeddingModel.reset_model()

        # Load again - should create new instance
        model2 = EmbeddingModel.get_model()
        assert model2 == mock_model2
        assert model1 is not model2
        assert mock_st.call_count == 2

    @patch('src.agents.splitter.embedding_model.SentenceTransformer')
    def test_encode_show_progress_bar_false(self, mock_st):
        """Test that progress bar is disabled"""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        mock_st.return_value = mock_model

        from src.agents.splitter.embedding_model import EmbeddingModel

        EmbeddingModel.encode(["test"])

        # Verify show_progress_bar=False
        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs['show_progress_bar'] is False
