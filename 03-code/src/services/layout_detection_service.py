"""
Layout Detection Service

Provides DocLayout-YOLO based layout detection for the Automatic Boundaries feature.
Manages model loading, inference, and GPU memory.

Key Features:
- DocLayout-YOLO model loading with GPU management
- Batch page processing with progress callbacks
- Region detection with 14+ classes
- Model unloading to free VRAM for OCR

Phase: 1.2 of Automatic Boundaries Implementation
Author: Claude Code
Date: 2026-01-14
"""

import os
import gc
import json
import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from src.utils.logging_config import logger
from src.services.gpu_manager import gpu_manager, GPUMemoryManager

# Try to import required libraries
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - layout detection disabled")

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/numpy not available - layout detection disabled")

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("Ultralytics not available - install with: pip install ultralytics")

try:
    from doclayout_yolo import YOLOv10
    DOCLAYOUT_YOLO_AVAILABLE = True
except ImportError:
    DOCLAYOUT_YOLO_AVAILABLE = False
    logger.warning("DocLayout-YOLO not available - install with: pip install doclayout-yolo")


# =============================================================================
# Configuration
# =============================================================================

# Model paths
BASE_MODEL_DIR = Path("models/layout_detection/base")
FINE_TUNED_MODEL_DIR = Path("models/layout_detection/fine_tuned")

# Default model filename (DocLayout-YOLO)
DEFAULT_MODEL_NAME = "doclayout_yolo_docstructbench_imgsz1024.pt"

# Memory requirements (in MB)
YOLO_VRAM_REQUIRED = 2500  # ~2.5 GB for inference
YOLO_TRAINING_VRAM_REQUIRED = 6000  # ~6 GB for training

# Detection classes mapping (DocLayout-YOLO default classes)
DEFAULT_CLASS_MAPPING = {
    0: "title",
    1: "paragraph",
    2: "figure",
    3: "table",
    4: "caption",
    5: "footer",
    6: "header",
    7: "list",
    8: "equation",
    9: "reference",
    10: "page_number"
}

# Extended class mapping for our system
EXTENDED_CLASS_MAPPING = {
    "title_level_1": {"id": 0, "color": "#FF0000", "display": "Title L1"},
    "title_level_2": {"id": 1, "color": "#FF6600", "display": "Title L2"},
    "title_level_3": {"id": 2, "color": "#FFCC00", "display": "Title L3"},
    "paragraph": {"id": 3, "color": "#00FF00", "display": "Paragraph"},
    "diagram": {"id": 4, "color": "#0066FF", "display": "Diagram"},
    "table": {"id": 5, "color": "#9900FF", "display": "Table"},
    "equation": {"id": 6, "color": "#FF00FF", "display": "Equation"},
    "list_bulleted": {"id": 7, "color": "#00FFFF", "display": "Bullet List"},
    "list_numbered": {"id": 8, "color": "#00CCCC", "display": "Numbered List"},
    "list_lettered": {"id": 9, "color": "#009999", "display": "Lettered List"},
    "list_item": {"id": 10, "color": "#006666", "display": "List Item"},
    "header": {"id": 11, "color": "#999999", "display": "Header"},
    "footer": {"id": 12, "color": "#666666", "display": "Footer"},
    "reference": {"id": 13, "color": "#CC9900", "display": "Reference"},
    "caption": {"id": 14, "color": "#99CC00", "display": "Caption"},
    "question": {"id": 15, "color": "#9C27B0", "display": "Question"},
    "answer": {"id": 16, "color": "#E91E63", "display": "Answer"}
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DetectedRegion:
    """Represents a detected region on a page."""
    class_name: str
    class_id: int
    x: int
    y: int
    width: int
    height: int
    confidence: float
    page_number: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) format."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class DetectionResult:
    """Result of detection on a single page."""
    page_number: int
    regions: List[DetectedRegion]
    processing_time_ms: float
    model_version: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "regions": [r.to_dict() for r in self.regions],
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version,
            "timestamp": self.timestamp
        }


@dataclass
class DetectionProgress:
    """Progress information for batch detection."""
    current_page: int
    total_pages: int
    pages_processed: int
    regions_detected: int
    status: str
    thumbnail_base64: Optional[str] = None


# =============================================================================
# Layout Detection Service
# =============================================================================

class LayoutDetectionService:
    """
    Service for detecting document layout regions using DocLayout-YOLO.

    Usage:
        service = LayoutDetectionService()
        service.load_model()

        results = service.detect_pages(page_images, progress_callback)

        service.unload_model()  # Free VRAM for OCR
    """

    def __init__(self):
        self.model: Optional[Any] = None
        self.model_path: Optional[str] = None
        self.model_version: str = "base"
        self.is_loaded: bool = False
        self.device: str = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        self.gpu_error_message: Optional[str] = None  # Set when GPU load fails

        # Class configuration (can be customized per book)
        self.enabled_classes: List[str] = list(EXTENDED_CLASS_MAPPING.keys())
        self.class_mapping = EXTENDED_CLASS_MAPPING.copy()

        # Detection parameters
        self.confidence_threshold: float = 0.25
        self.iou_threshold: float = 0.45
        self.image_size: int = 1024  # Match model's trained image size

        logger.info(f"LayoutDetectionService initialized. Device: {self.device}")

    def is_available(self) -> bool:
        """Check if all dependencies are available."""
        return TORCH_AVAILABLE and PIL_AVAILABLE and (DOCLAYOUT_YOLO_AVAILABLE or ULTRALYTICS_AVAILABLE)

    def get_model_path(self, book_id: Optional[int] = None,
                       model_version: Optional[int] = None) -> Path:
        """
        Get the model path for a given book.

        Args:
            book_id: Optional book ID for fine-tuned model
            model_version: Optional specific version

        Returns:
            Path to model file
        """
        if book_id and model_version:
            # Fine-tuned model
            model_filename = f"book_{book_id}_v{model_version}.pt"
            model_path = FINE_TUNED_MODEL_DIR / model_filename
            if model_path.exists():
                return model_path
            logger.warning(f"Fine-tuned model not found: {model_path}, using base model")

        # Base model
        base_path = BASE_MODEL_DIR / DEFAULT_MODEL_NAME
        return base_path

    def load_model(self, model_path: Optional[str] = None,
                   book_id: Optional[int] = None,
                   model_version: Optional[int] = None) -> bool:
        """
        Load the YOLO model into GPU memory.

        Args:
            model_path: Optional explicit path to model
            book_id: Optional book ID for book-specific model
            model_version: Optional specific version

        Returns:
            True if model loaded successfully
        """
        if not self.is_available():
            logger.error("Layout detection dependencies not available")
            return False

        if self.is_loaded:
            logger.info("Model already loaded, skipping")
            return True

        # Check GPU memory - YOLO MUST run on GPU, no CPU fallback
        if self.device != "cuda":
            logger.error("GPU-Only YOLO: CUDA not available. YOLO requires GPU.")
            self.gpu_error_message = "GPU not available. YOLO detection requires CUDA-enabled GPU."
            return False

        if not gpu_manager.check_sufficient_memory(YOLO_VRAM_REQUIRED, "DocLayout-YOLO"):
            logger.error("GPU-Only YOLO: Insufficient GPU memory")
            self.gpu_error_message = (
                "GPU memory insufficient. Please unload other models (Surya OCR, EasyOCR) "
                "from the GPU Management section in Library page or Auto-Slicer page."
            )
            return False

        # Determine model path - check for book-specific model first
        if model_path:
            path = Path(model_path)
        elif book_id:
            # Check if book has a specific model in database
            path = self._get_book_model_path(book_id)
            if path is None:
                path = self.get_model_path(book_id, model_version)
        else:
            path = self.get_model_path(book_id, model_version)

        if not path.exists():
            logger.error(f"Model file not found: {path}")
            logger.info("Please download DocLayout-YOLO model to: " + str(path))
            return False

        try:
            logger.info(f"Loading YOLO model from: {path}")
            gpu_manager.log_gpu_usage()

            # Load model using doclayout_yolo's YOLOv10 for proper compatibility
            if DOCLAYOUT_YOLO_AVAILABLE:
                self.model = YOLOv10(str(path))
            else:
                # Fallback to ultralytics YOLO
                self.model = YOLO(str(path))

            # Move to device
            if self.device == "cuda":
                self.model.to(self.device)

            self.model_path = str(path)
            self.is_loaded = True

            # Determine version from filename
            if "book_" in path.name and "_v" in path.name:
                self.model_version = path.stem.split("_v")[-1]
            elif "book_" in path.name:
                self.model_version = "book_specific"
            else:
                self.model_version = "base"

            logger.info(f"Model loaded successfully. Version: {self.model_version}")
            gpu_manager.log_gpu_usage()

            return True

        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}", exc_info=True)
            self.model = None
            self.is_loaded = False
            return False
    
    def _get_book_model_path(self, book_id: int) -> Optional[Path]:
        """
        Get the model path for a book from the database.
        
        Args:
            book_id: The book ID
            
        Returns:
            Path to book-specific model, or None to use global
        """
        from sqlalchemy import text
        from src.database.connection import engine
        
        sql = text("""
            SELECT yolo_model_path
            FROM books_metadata
            WHERE book_id = :book_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql, {"book_id": book_id}).fetchone()
            
            if result and result[0]:
                path = Path(result[0])
                if path.exists():
                    logger.info(f"Using book-specific model for book {book_id}: {path}")
                    return path
                else:
                    logger.warning(f"Book {book_id} model path set but file missing: {path}, falling back to global")
        
        # Return None to indicate use global model
        return None

    def unload_model(self):
        """Unload model and free GPU memory."""
        if self.model is not None:
            gpu_manager.unload_model_safely(self.model, "DocLayout-YOLO")
            self.model = None
            self.is_loaded = False
            logger.info("YOLO model unloaded")

    def detect_single_page(self, image: Image.Image,
                           page_number: int) -> DetectionResult:
        """
        Detect layout regions on a single page.

        Args:
            image: PIL Image of the page
            page_number: Page number for tracking

        Returns:
            DetectionResult with detected regions
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        import time
        start_time = time.time()

        # Run inference
        results = self.model(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.image_size,
            verbose=False
        )

        # Parse results
        regions = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes

            for i in range(len(boxes)):
                # Get box coordinates (xyxy format)
                box = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = map(int, box)

                # Get class and confidence
                class_id = int(boxes.cls[i].cpu().numpy())
                confidence = float(boxes.conf[i].cpu().numpy())

                # Map class ID to name (remapping happens inside _get_class_name)
                class_name = self._get_class_name(class_id)

                # Skip if class not enabled
                if class_name not in self.enabled_classes:
                    continue

                region = DetectedRegion(
                    class_name=class_name,
                    class_id=class_id,
                    x=x1,
                    y=y1,
                    width=x2 - x1,
                    height=y2 - y1,
                    confidence=confidence,
                    page_number=page_number
                )
                regions.append(region)

        processing_time_ms = (time.time() - start_time) * 1000

        return DetectionResult(
            page_number=page_number,
            regions=regions,
            processing_time_ms=processing_time_ms,
            model_version=self.model_version,
            timestamp=datetime.now().isoformat()
        )

    def detect_pages(self, page_images: List[Tuple[int, Image.Image]],
                     progress_callback: Optional[Callable[[DetectionProgress], None]] = None,
                     generate_thumbnails: bool = True) -> List[DetectionResult]:
        """
        Detect layout regions on multiple pages.

        Args:
            page_images: List of (page_number, PIL Image) tuples
            progress_callback: Optional callback for progress updates
            generate_thumbnails: Whether to generate preview thumbnails

        Returns:
            List of DetectionResult objects
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        results = []
        total_pages = len(page_images)
        total_regions = 0

        for idx, (page_number, image) in enumerate(page_images):
            try:
                # Detect regions
                result = self.detect_single_page(image, page_number)
                results.append(result)
                total_regions += len(result.regions)

                # Generate progress update
                if progress_callback:
                    thumbnail_b64 = None
                    if generate_thumbnails:
                        thumbnail_b64 = self._generate_thumbnail(image, result.regions)

                    progress = DetectionProgress(
                        current_page=page_number,
                        total_pages=total_pages,
                        pages_processed=idx + 1,
                        regions_detected=total_regions,
                        status="processing",
                        thumbnail_base64=thumbnail_b64
                    )
                    progress_callback(progress)

            except Exception as e:
                logger.error(f"Error detecting page {page_number}: {e}")
                # Continue with next page
                continue

        # Final progress update
        if progress_callback:
            progress = DetectionProgress(
                current_page=page_images[-1][0] if page_images else 0,
                total_pages=total_pages,
                pages_processed=total_pages,
                regions_detected=total_regions,
                status="completed"
            )
            progress_callback(progress)

        return results

    def _get_class_name(self, class_id: int) -> str:
        """Map class ID to class name."""
        # First try default mapping
        if class_id in DEFAULT_CLASS_MAPPING:
            base_name = DEFAULT_CLASS_MAPPING[class_id]
            # Map base names to extended names
            # NOTE: "table" is remapped to "diagram" per user request
            mapping = {
                "title": "title_level_1",
                "paragraph": "paragraph",
                "figure": "diagram",
                "table": "diagram",  # Tables treated as diagrams
                "caption": "caption",
                "footer": "footer",
                "header": "header",
                "list": "list_bulleted",
                "equation": "equation",
                "reference": "reference",
                "page_number": "footer"
            }
            return mapping.get(base_name, base_name)
        return f"unknown_{class_id}"

    def _generate_thumbnail(self, image: Image.Image,
                            regions: List[DetectedRegion],
                            max_size: int = 200) -> str:
        """
        Generate a thumbnail with detected boxes drawn.

        Args:
            image: Original page image
            regions: Detected regions to draw
            max_size: Maximum dimension for thumbnail

        Returns:
            Base64 encoded PNG thumbnail
        """
        try:
            from PIL import ImageDraw

            # Create thumbnail
            thumb = image.copy()
            thumb.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Calculate scale factor
            scale_x = thumb.width / image.width
            scale_y = thumb.height / image.height

            # Draw boxes
            draw = ImageDraw.Draw(thumb)
            for region in regions:
                # Scale coordinates
                x1 = int(region.x * scale_x)
                y1 = int(region.y * scale_y)
                x2 = int((region.x + region.width) * scale_x)
                y2 = int((region.y + region.height) * scale_y)

                # Get color for class
                color = self.class_mapping.get(
                    region.class_name, {}
                ).get("color", "#FF0000")

                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            # Convert to base64
            buffer = BytesIO()
            thumb.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return ""

    def set_enabled_classes(self, classes: List[str]):
        """Set which classes to detect."""
        self.enabled_classes = [c for c in classes if c in self.class_mapping]
        logger.info(f"Enabled classes: {self.enabled_classes}")

    def set_confidence_threshold(self, threshold: float):
        """Set minimum confidence threshold for detections."""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Confidence threshold set to: {self.confidence_threshold}")

    def get_class_config(self) -> Dict[str, Any]:
        """Get the class configuration for UI."""
        return {
            class_name: {
                "id": config["id"],
                "color": config["color"],
                "display": config["display"],
                "enabled": class_name in self.enabled_classes
            }
            for class_name, config in self.class_mapping.items()
        }


# =============================================================================
# Singleton Instance
# =============================================================================

layout_detection_service = LayoutDetectionService()


# =============================================================================
# Helper Functions
# =============================================================================

def check_model_exists() -> Tuple[bool, str]:
    """
    Check if the base model exists.

    Returns:
        Tuple of (exists, message)
    """
    base_path = BASE_MODEL_DIR / DEFAULT_MODEL_NAME

    if base_path.exists():
        return True, f"Model found at: {base_path}"

    return False, (
        f"Model not found. Please download DocLayout-YOLO model to:\n"
        f"  {base_path}\n\n"
        f"Download from: https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench\n"
        f"Or run: pip install huggingface-hub && huggingface-cli download "
        f"juliozhao/DocLayout-YOLO-DocStructBench doclayout_yolo_docsynth300k.pt "
        f"--local-dir {BASE_MODEL_DIR}"
    )


def ensure_model_directories():
    """Create model directories if they don't exist."""
    BASE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    FINE_TUNED_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Model directories ensured: {BASE_MODEL_DIR}, {FINE_TUNED_MODEL_DIR}")
