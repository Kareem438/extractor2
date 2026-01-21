"""
Text Splitter Service

Splits long text into semantic chunks of 3-5 lines for better readability
and processing in the verification interface.
"""

import re
from typing import List


class TextSplitter:
    """
    Splits text into semantic chunks based on natural breaks.

    Prioritizes splitting at:
    1. Double line breaks (paragraphs)
    2. Single line breaks after sentences
    3. Sentence boundaries
    """

    def __init__(self, min_lines: int = 3, max_lines: int = 5):
        """
        Initialize splitter.

        Args:
            min_lines: Minimum lines per chunk
            max_lines: Maximum lines per chunk
        """
        self.min_lines = min_lines
        self.max_lines = max_lines

    def split_text(self, text: str) -> List[dict]:
        """
        Split text into semantic chunks.

        Args:
            text: Input text to split

        Returns:
            List of chunk dictionaries with 'text' and 'line_count'
        """
        if not text or not text.strip():
            return []

        # Split into lines
        lines = text.split('\n')

        chunks = []
        current_chunk = []
        current_line_count = 0

        for line in lines:
            stripped_line = line.strip()

            # Skip empty lines at chunk boundaries
            if not stripped_line and current_line_count == 0:
                continue

            current_chunk.append(line)
            if stripped_line:  # Only count non-empty lines
                current_line_count += 1

            # Check if we should create a chunk
            should_split = False

            # Split at paragraph breaks (empty line after reaching min lines)
            if not stripped_line and current_line_count >= self.min_lines:
                should_split = True

            # Split at max lines
            elif current_line_count >= self.max_lines:
                should_split = True

            # Split at section headers (lines ending with :)
            elif stripped_line.endswith(':') and current_line_count >= self.min_lines:
                should_split = True

            if should_split:
                chunk_text = '\n'.join(current_chunk).strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'line_count': current_line_count,
                        'char_count': len(chunk_text)
                    })
                current_chunk = []
                current_line_count = 0

        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'line_count': current_line_count,
                    'char_count': len(chunk_text)
                })

        return chunks

    def split_by_sentences(self, text: str, sentences_per_chunk: int = 3) -> List[dict]:
        """
        Alternative splitting method based on sentences.

        Args:
            text: Input text
            sentences_per_chunk: Number of sentences per chunk

        Returns:
            List of chunk dictionaries
        """
        # Split into sentences (basic regex)
        sentence_endings = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_endings, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i+sentences_per_chunk]
            chunk_text = '. '.join(chunk_sentences)
            if not chunk_text.endswith(('.', '!', '?')):
                chunk_text += '.'

            line_count = chunk_text.count('\n') + 1
            chunks.append({
                'text': chunk_text,
                'line_count': line_count,
                'char_count': len(chunk_text),
                'sentence_count': len(chunk_sentences)
            })

        return chunks


# Singleton instance
_splitter_instance = None


def get_text_splitter() -> TextSplitter:
    """Get singleton TextSplitter instance."""
    global _splitter_instance
    if _splitter_instance is None:
        _splitter_instance = TextSplitter(min_lines=3, max_lines=5)
    return _splitter_instance
