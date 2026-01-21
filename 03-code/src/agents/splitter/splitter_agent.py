"""
CHUNK-020: Splitter Agent - Main Logic

Split extracted text into knowledge units using semantic chunking.
Converts chunks to knowledge unit format with metadata.
"""

from src.agents.splitter.text_chunker import split_text_semantic
from src.utils.language_detector import detect_language


class SplitterAgent:
    """
    Agent responsible for splitting text into knowledge units.

    Uses semantic text chunking to create intelligent 3-5 line chunks
    with appropriate metadata for database storage.
    """

    def split_text(self, text: str, page_number: int) -> list[dict]:
        """
        Split text into knowledge units.

        Uses semantic chunking to split text into meaningful segments,
        then converts to knowledge unit format with metadata.

        Args:
            text: Text content to split
            page_number: Page number where text originated

        Returns:
            list[dict]: List of knowledge unit dictionaries with:
                - text_content: Text of the unit
                - text_length: Character count
                - line_count: Number of lines
                - page_number: Source page number
                - confidence_score: Chunk quality score
                - language: Detected language

        Example:
            >>> agent = SplitterAgent()
            >>> text = "First sentence. Second sentence.\\nThird sentence."
            >>> units = agent.split_text(text, page_number=1)
            >>> for unit in units:
            ...     print(f"Page {unit['page_number']}: {unit['text_content'][:50]}")
        """
        # Handle empty or very short text
        if not text or len(text.strip()) < 10:
            return []

        # Use semantic chunker to split text
        chunks = split_text_semantic(text)

        # Convert chunks to knowledge unit format
        knowledge_units = []

        for chunk in chunks:
            # Detect language for this chunk
            lang = detect_language(chunk['text'])

            # Create knowledge unit dict
            ku = {
                'text_content': chunk['text'],
                'text_length': len(chunk['text']),
                'line_count': chunk['line_count'],
                'page_number': page_number,
                'confidence_score': chunk['confidence'],
                'language': lang,
                # Note: position fields (x0, y0, x1, y1) will be added by marker agent
            }

            knowledge_units.append(ku)

        return knowledge_units
