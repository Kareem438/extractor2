"""
CHUNK-015: Image Compression (LZ4)

Compress and decompress PIL Images using LZ4 for efficient storage.
Uses PNG format internally for lossless quality preservation.
"""

try:
    import lz4.frame
except ImportError:
    # For environments where lz4 is not installed
    class _MockLZ4Frame:
        @staticmethod
        def compress(data):
            raise ImportError("lz4 library is not installed")

        @staticmethod
        def decompress(data):
            raise ImportError("lz4 library is not installed")

    class _MockLZ4:
        frame = _MockLZ4Frame()

    lz4 = _MockLZ4()

from PIL import Image
from io import BytesIO


def compress_image(image: Image.Image) -> bytes:
    """
    Compress PIL Image to LZ4-compressed bytes.

    Converts image to PNG format (lossless) and compresses with LZ4.
    Provides fast compression with good compression ratios.

    Args:
        image: PIL Image object to compress

    Returns:
        bytes: LZ4-compressed image data

    Raises:
        Exception: If compression fails

    Example:
        >>> img = Image.open('photo.jpg')
        >>> compressed = compress_image(img)
        >>> print(f"Compressed size: {len(compressed)} bytes")
    """
    # Convert image to PNG bytes (lossless format)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    # Compress with LZ4
    compressed = lz4.frame.compress(png_bytes)

    return compressed


def decompress_image(compressed_bytes: bytes) -> Image.Image:
    """
    Decompress LZ4 bytes to PIL Image.

    Decompresses LZ4 data and loads as PIL Image.

    Args:
        compressed_bytes: LZ4-compressed image data

    Returns:
        Image.Image: Decompressed PIL Image

    Raises:
        Exception: If decompression fails

    Example:
        >>> compressed = compress_image(img)
        >>> restored = decompress_image(compressed)
        >>> restored.show()
    """
    # Decompress LZ4 data
    png_bytes = lz4.frame.decompress(compressed_bytes)

    # Load as PIL Image from PNG bytes
    buffer = BytesIO(png_bytes)
    image = Image.open(buffer)

    return image
