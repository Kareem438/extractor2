"""
CHUNK-005: File Type Detection

Detects file type using python-magic library based on file content.
Falls back to extension-based detection if python-magic is not available.
"""

import os

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


def detect_file_type(file_path: str) -> str:
    """
    Detect file type from file content using MIME type detection.

    Uses python-magic library to read file content and determine actual
    file type, regardless of file extension. Falls back to extension-based
    detection if python-magic is not available.

    Args:
        file_path: Path to the file to detect

    Returns:
        File type as string (e.g., 'PDF', 'DOCX', 'PNG', 'UNKNOWN')

    Raises:
        ValueError: If file_path is empty
        TypeError: If file_path is None

    Examples:
        >>> detect_file_type('/path/to/document.pdf')
        'PDF'
        >>> detect_file_type('/path/to/image.png')
        'PNG'
        >>> detect_file_type('/path/to/unknown.xyz')
        'UNKNOWN'
    """
    # Input validation
    if file_path is None:
        raise TypeError("file_path cannot be None")

    if not file_path or file_path == '':
        raise ValueError("file_path cannot be empty")

    # Try python-magic first if available
    if MAGIC_AVAILABLE:
        try:
            mime = magic.from_file(file_path, mime=True)

            # Map MIME types to file type labels
            mime_to_ext = {
                'application/pdf': 'PDF',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
                'text/plain': 'TXT',
                'text/html': 'HTML',
                'application/epub+zip': 'EPUB',
                'image/png': 'PNG',
                'image/jpeg': 'JPEG'
            }

            detected = mime_to_ext.get(mime, 'UNKNOWN')
            if detected != 'UNKNOWN':
                return detected
        except Exception:
            # Fall through to extension-based detection
            pass

    # Fallback to extension-based detection
    _, ext = os.path.splitext(file_path)
    ext = ext.lower().lstrip('.')

    ext_map = {
        'pdf': 'PDF',
        'docx': 'DOCX',
        'doc': 'DOC',
        'txt': 'TXT',
        'html': 'HTML',
        'htm': 'HTML',
        'epub': 'EPUB',
        'png': 'PNG',
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'gif': 'GIF',
        'bmp': 'BMP',
        'tiff': 'TIFF',
        'tif': 'TIFF'
    }

    return ext_map.get(ext, 'UNKNOWN')
