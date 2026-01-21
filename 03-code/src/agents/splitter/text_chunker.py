"""
CHUNK-017: Text Chunking Algorithm

Split text into semantic chunks of 3-5 lines using embedding-based
similarity for intelligent boundary detection.
"""

import re
import numpy as np
from src.agents.splitter.embedding_model import EmbeddingModel


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Uses regex to split on sentence boundaries (. ! ?)
    while preserving the punctuation.

    Args:
        text: Text to split into sentences

    Returns:
        list[str]: List of sentences
    """
    # Split on sentence boundaries
    sentences = re.split(r'([.!?]+\s+)', text)

    # Recombine sentence text with its punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sent = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
        sent = sent.strip()
        if sent:
            result.append(sent)

    # Add last sentence if exists
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result if result else [text]


def find_split_points(embeddings: np.ndarray, threshold: float = 0.6) -> list[int]:
    """
    Find split points based on embedding similarity.

    Identifies indices where consecutive sentences have low similarity,
    indicating potential semantic boundaries.

    Args:
        embeddings: Array of sentence embeddings, shape (n_sentences, embedding_dim)
        threshold: Similarity threshold below which to split (default: 0.6)

    Returns:
        list[int]: Indices of split points
    """
    if len(embeddings) <= 1:
        return []

    split_points = []

    for i in range(len(embeddings) - 1):
        # Calculate cosine similarity between consecutive embeddings
        sim = np.dot(embeddings[i], embeddings[i + 1]) / (
            np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
        )

        # If similarity is below threshold, mark as split point
        if sim < threshold:
            split_points.append(i)

    return split_points


def calculate_confidence(text: str) -> float:
    """
    Calculate confidence score for a chunk.

    Simple heuristic based on text properties:
    - Longer text (more sentences) = higher confidence
    - Balanced line count (3-5 lines) = higher confidence

    Args:
        text: Chunk text

    Returns:
        float: Confidence score (0.0 to 1.0)
    """
    # Count lines
    line_count = text.count('\n') + 1

    # Count sentences (rough estimate)
    sentence_count = len(re.findall(r'[.!?]+', text))

    # Base confidence on line count (3-5 is ideal)
    if 3 <= line_count <= 5:
        conf = 0.8
    elif 2 <= line_count <= 6:
        conf = 0.6
    else:
        conf = 0.4

    # Boost confidence if we have multiple sentences
    if sentence_count >= 2:
        conf += 0.1

    # Clamp to [0, 1]
    return min(1.0, conf)


def split_text_semantic(text: str) -> list[dict]:
    """
    Split text into semantic chunks (3-5 lines each).

    Uses embedding-based similarity to find natural semantic boundaries.
    Returns list of chunks with text, confidence, and line count.

    Args:
        text: Text to split into chunks

    Returns:
        list[dict]: List of chunks, each with:
            - text (str): Chunk content
            - confidence (float): Confidence score (0.0-1.0)
            - line_count (int): Number of lines in chunk

    Example:
        >>> text = "First sentence. Second sentence.\\n\\nThird sentence."
        >>> chunks = split_text_semantic(text)
        >>> for chunk in chunks:
        ...     print(f"Lines: {chunk['line_count']}, Conf: {chunk['confidence']}")
    """
    if not text or not text.strip():
        return []

    # Split into paragraphs
    paragraphs = text.split('\n\n')

    chunks = []

    for para in paragraphs:
        if not para.strip():
            continue

        # Split into sentences
        sentences = split_sentences(para)

        if len(sentences) == 0:
            continue

        # Generate embeddings for semantic splitting
        if len(sentences) > 1:
            try:
                embeddings = EmbeddingModel.encode(sentences)
                split_points = find_split_points(embeddings, threshold=0.6)
            except Exception:
                # Fallback: no split points if embeddings fail
                split_points = []
        else:
            split_points = []

        # Create chunks
        current_chunk = []

        for i, sent in enumerate(sentences):
            current_chunk.append(sent)

            # Check if we should split here
            should_split = (
                i in split_points or
                len(current_chunk) >= 5  # Max 5 sentences per chunk
            )

            # If last sentence, always finish chunk
            if i == len(sentences) - 1:
                should_split = True

            if should_split and current_chunk:
                chunk_text = ' '.join(current_chunk)
                line_count = chunk_text.count('\n') + 1
                confidence = calculate_confidence(chunk_text)

                chunks.append({
                    'text': chunk_text,
                    'confidence': confidence,
                    'line_count': line_count
                })

                current_chunk = []

    return chunks
