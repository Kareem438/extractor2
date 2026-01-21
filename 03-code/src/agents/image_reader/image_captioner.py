"""
CHUNK-018: BLIP Image Captioning

Generate AI descriptions for images using BLIP model from Salesforce.
Implements singleton pattern for efficient model caching.
"""

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
except ImportError:
    # For environments where transformers is not installed
    class BlipProcessor:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            raise ImportError("transformers library is not installed")

        def __call__(self, *args, **kwargs):
            raise ImportError("transformers library is not installed")

        def decode(self, *args, **kwargs):
            raise ImportError("transformers library is not installed")

    class BlipForConditionalGeneration:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            raise ImportError("transformers library is not installed")

        def generate(self, *args, **kwargs):
            raise ImportError("transformers library is not installed")

from PIL import Image
from src.utils.logging_config import logger

# Import settings - will be mocked in tests
try:
    from src.config import settings
except Exception:
    # Allow import to succeed even if settings validation fails
    settings = None


class ImageCaptioner:
    """
    Singleton class for loading and caching BLIP image captioning model.

    Uses Salesforce BLIP (Bootstrapping Language-Image Pre-training)
    for generating natural language descriptions of images.
    """

    _processor = None
    _model = None

    @classmethod
    def get_model(cls) -> tuple:
        """
        Lazy-load BLIP model and processor (singleton pattern).

        Loads model on first call and caches for subsequent calls.
        Uses model cache directory from settings.

        Returns:
            tuple: (processor, model)
                - processor: BlipProcessor for input/output handling
                - model: BlipForConditionalGeneration for caption generation

        Example:
            >>> processor, model = ImageCaptioner.get_model()
        """
        if cls._processor is None:
            logger.info("Loading BLIP model...")

            cache_dir = settings.MODEL_CACHE_DIR if settings else None

            cls._processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                cache_dir=cache_dir
            )

            cls._model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                cache_dir=cache_dir
            )

            logger.info("BLIP model loaded.")

        return cls._processor, cls._model

    @classmethod
    def generate_caption(cls, image: Image.Image) -> tuple[str, float]:
        """
        Generate caption and confidence for an image.

        Uses BLIP model to generate a natural language description
        of the image content.

        Args:
            image: PIL Image object to caption

        Returns:
            tuple[str, float]: (caption, confidence)
                - caption: Generated text description
                - confidence: Confidence score (0-100)

        Example:
            >>> img = Image.open('photo.jpg')
            >>> caption, conf = ImageCaptioner.generate_caption(img)
            >>> print(f"{caption} (confidence: {conf}%)")
        """
        processor, model = cls.get_model()

        # Process image and generate caption
        inputs = processor(image, return_tensors="pt")
        outputs = model.generate(**inputs)

        # Decode output to text
        caption = processor.decode(outputs[0], skip_special_tokens=True)

        # Simplified confidence calculation
        # In production, this could be based on output probabilities
        confidence = 85.0

        return caption, confidence

    @classmethod
    def reset_model(cls):
        """
        Reset cached model (useful for testing).

        Clears the singleton instances, forcing reload on next get_model() call.
        """
        cls._processor = None
        cls._model = None
