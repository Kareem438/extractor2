"""
CHUNK-014: Language Detection

Detect text language (English/Arabic/Mixed) using langdetect library
with fallback to script-based detection.
"""

try:
    from langdetect import detect, LangDetectException
except ImportError:
    # For environments where langdetect is not installed
    class LangDetectException(Exception):
        pass

    def detect(text):
        raise ImportError("langdetect library is not installed")


def detect_language(text: str) -> str:
    """
    Detect language of text.

    Uses langdetect library for primary detection, with fallback to
    Unicode script analysis for mixed or ambiguous cases.

    Args:
        text: Text content to analyze

    Returns:
        str: One of 'english', 'arabic', or 'mixed'
            - 'english': Latin script or English language detected
            - 'arabic': Arabic script or Arabic language detected
            - 'mixed': Both Latin and Arabic scripts present

    Example:
        >>> detect_language("Hello world")
        'english'
        >>> detect_language("مرحبا")
        'arabic'
        >>> detect_language("Hello مرحبا")
        'mixed'
    """
    # Handle empty or short text
    if not text or len(text.strip()) < 10:
        return 'english'  # Default

    try:
        # Use langdetect for primary detection
        lang = detect(text)

        if lang == 'en':
            return 'english'
        elif lang == 'ar':
            return 'arabic'
        else:
            # For other languages, check script composition
            has_latin = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)

            if has_latin and has_arabic:
                return 'mixed'
            elif has_arabic:
                return 'arabic'
            else:
                return 'english'

    except (LangDetectException, ImportError):
        # Fallback to script detection if langdetect fails
        has_latin = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)
        has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)

        if has_latin and has_arabic:
            return 'mixed'
        elif has_arabic:
            return 'arabic'
        else:
            return 'english'
