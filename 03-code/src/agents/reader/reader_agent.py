"""
CHUNK-019: Reader Agent - Main Logic

Orchestrate page reading with native text extraction and OCR fallback.
Integrates PDF reading, OCR, and language detection.
"""

from src.agents.reader.pdf_reader import extract_text_from_pdf_page
from src.agents.reader.pdf_to_image import pdf_page_to_image
from src.utils.ocr_retry import ocr_with_retry
from src.utils.language_detector import detect_language
from src.utils.logging_config import logger


class ReaderAgent:
    """
    Agent responsible for reading and extracting text from PDF pages.

    Uses native text extraction when available, with OCR fallback for
    scanned pages. Includes language detection and confidence scoring.
    """

    def read_page(self, pdf_path: str, page_number: int, language_setting: str = 'auto',
                  ocr_quality: str = 'balanced') -> dict:
        """
        Read page and extract text.

        Attempts native text extraction first. If no native text is found,
        falls back to OCR with retry logic. Detects language and provides
        confidence scores.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number to read (1-indexed)
            language_setting: Language setting ('auto', 'english', 'arabic', 'mixed')
            ocr_quality: OCR quality setting ('fast', 'balanced', 'high')

        Returns:
            dict: {
                'text': str - Extracted text content
                'blocks': list - Text blocks with coordinates (native only)
                'language': str - Detected language
                'confidence': float - Extraction confidence (0-100)
                'extraction_method': str - Method used ('native_text', 'ocr_standard', etc.)
            }

        Example:
            >>> agent = ReaderAgent()
            >>> result = agent.read_page('document.pdf', 1)
            >>> print(f"Text: {result['text']}")
            >>> print(f"Method: {result['extraction_method']}")
        """
        # Try native text extraction first
        result = extract_text_from_pdf_page(pdf_path, page_number)

        if result['has_text']:
            # Native text available
            logger.info(f"Page {page_number}: Using native text extraction")
            lang = detect_language(result['text'])

            return {
                'text': result['text'],
                'blocks': result['blocks'],
                'language': lang,
                'confidence': 100.0,
                'extraction_method': 'native_text'
            }
        else:
            # Fallback to OCR
            logger.info(f"Page {page_number}: No native text, using OCR...")

            # Convert page to image
            page_image = pdf_page_to_image(pdf_path, page_number)

            # Determine OCR language code
            if language_setting == 'english':
                ocr_lang = 'eng'
            elif language_setting == 'arabic':
                ocr_lang = 'ara'
            else:  # 'auto' or 'mixed'
                ocr_lang = 'eng'  # Default to English for auto

            # OCR with retry logic
            text, confidence, method = ocr_with_retry(
                page_image,
                language=ocr_lang
            )

            # Detect language from extracted text
            lang = detect_language(text)

            return {
                'text': text,
                'blocks': [],  # OCR doesn't provide block coordinates (simplified)
                'language': lang,
                'confidence': confidence,
                'extraction_method': method
            }
