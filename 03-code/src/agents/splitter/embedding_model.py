"""
CHUNK-016: Sentence Transformer Loader

Lazy-load and cache SBERT model for text embedding generation.
Implements singleton pattern for efficient model reuse.
"""

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    # For environments where sentence-transformers is not installed
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise ImportError("sentence-transformers library is not installed")

        def encode(self, *args, **kwargs):
            raise ImportError("sentence-transformers library is not installed")

import numpy as np
from src.utils.logging_config import logger

# Import settings - will be mocked in tests
try:
    from src.config import settings
except Exception:
    # Allow import to succeed even if settings validation fails
    settings = None


class EmbeddingModel:
    """
    Singleton class for loading and caching SBERT embedding model.

    Uses paraphrase-multilingual-MiniLM-L12-v2 for multilingual support.
    Model is loaded once and cached for all subsequent uses.
    """

    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """
        Lazy-load SBERT model (singleton pattern).

        Loads model on first call and caches for subsequent calls.
        Uses model cache directory from settings.

        Returns:
            SentenceTransformer: Loaded SBERT model

        Example:
            >>> model = EmbeddingModel.get_model()
            >>> embeddings = model.encode(["Hello world"])
        """
        if cls._model is None:
            logger.info("Loading SBERT model...")

            cache_dir = settings.MODEL_CACHE_DIR if settings else None

            cls._model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2',
                cache_folder=cache_dir
            )

            logger.info("SBERT model loaded.")

        return cls._model

    @classmethod
    def encode(cls, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Uses the cached SBERT model to generate 384-dimensional embeddings.

        Args:
            texts: List of text strings to encode

        Returns:
            np.ndarray: Array of embeddings, shape (len(texts), 384)

        Example:
            >>> embeddings = EmbeddingModel.encode(["Hello", "World"])
            >>> print(embeddings.shape)  # (2, 384)
        """
        model = cls.get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings

    @classmethod
    def reset_model(cls):
        """
        Reset cached model (useful for testing).

        Clears the singleton instance, forcing reload on next get_model() call.
        """
        cls._model = None
