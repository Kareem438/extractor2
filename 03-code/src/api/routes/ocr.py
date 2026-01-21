"""
Sequential OCR API Routes

Provides separate endpoints for each OCR engine (PaddleOCR, Surya, Tesseract)
and the evaluation/split/mark pipeline.

Aligned with sequential-ocr-svg-processing.md architecture.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from src.utils.logging_config import logger

router = APIRouter()


class OCRRequest(BaseModel):
    """Request model for OCR processing"""
    book_id: int
    max_pages: Optional[int] = None  # For testing: limit pages to process
    skip_existing: Optional[bool] = True  # Skip already-scanned pages (default: True for safety)


class OCRResponse(BaseModel):
    """Response model for OCR endpoints"""
    book_id: int
    status: str
    message: str


@router.post("/scan-pages", response_model=OCRResponse)
async def scan_pages(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Scan and save PDF pages as 600 DPI images.

    - Renders each page of the PDF to 600 DPI PNG
    - Saves images to raw_book..._pages table
    - Does NOT run OCR - just saves the images
    - This should be run FIRST before any OCR engine
    - Supports max_pages parameter for testing
    - skip_existing=True (default): Only scans pages not yet in database
    """
    pages_msg = f" (max {request.max_pages} pages)" if request.max_pages else ""
    skip_msg = " (skipping existing)" if request.skip_existing else " (overwriting existing)"
    logger.info(f"Starting page scan for book_id={request.book_id}{pages_msg}{skip_msg}")

    try:
        # Import here to avoid circular dependencies
        from src.services.ocr_sequential import scan_and_save_pages

        # Add to background tasks with max_pages and skip_existing parameters
        background_tasks.add_task(
            scan_and_save_pages,
            request.book_id,
            request.max_pages,
            request.skip_existing
        )

        message = f"Page scanning started in background{pages_msg}{skip_msg}"
        return OCRResponse(
            book_id=request.book_id,
            status="processing",
            message=message
        )

    except Exception as e:
        logger.error(f"Failed to start page scanning for book_id={request.book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr/easyocr", response_model=OCRResponse)
async def start_easyocr(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Start EasyOCR processing for a book.

    - Renders pages to 300 DPI images
    - Runs EasyOCR on each image
    - Stores results in attr2_value (text) and attr5_value (confidence)
    - On FIRST OCR run: Extracts and stores embedded images
    - Supports max_pages parameter for testing (e.g., first 5 pages)
    """
    pages_msg = f" (max {request.max_pages} pages)" if request.max_pages else ""
    logger.info(f"Starting EasyOCR for book_id={request.book_id}{pages_msg}")

    try:
        # Import here to avoid circular dependencies
        from src.services.ocr_sequential import run_easyocr_sequential

        # Add to background tasks with max_pages parameter
        background_tasks.add_task(run_easyocr_sequential, request.book_id, request.max_pages)

        message = f"EasyOCR processing started in background{pages_msg}"
        return OCRResponse(
            book_id=request.book_id,
            status="processing",
            message=message
        )

    except Exception as e:
        logger.error(f"Failed to start EasyOCR for book_id={request.book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/load-surya")
async def load_surya_ocr():
    """
    Load Surya OCR models into GPU memory.

    - Loads Foundation, Detection, and Recognition predictors
    - Caches models in memory for faster subsequent use
    - Returns success status and message
    """
    logger.info("API request to load Surya OCR models")

    try:
        from src.services.ocr_sequential import load_surya_models

        result = load_surya_models()

        if result['success']:
            return {
                "status": "success",
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    except Exception as e:
        logger.error(f"Failed to load Surya OCR models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/unload-surya")
async def unload_surya_ocr():
    """
    Unload Surya OCR models from GPU memory to free VRAM.

    - Clears model references
    - Runs garbage collection
    - Clears CUDA cache
    - Returns success status and message
    """
    logger.info("API request to unload Surya OCR models")

    try:
        from src.services.ocr_sequential import unload_surya_models

        result = unload_surya_models()

        if result['success']:
            return {
                "status": "success",
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    except Exception as e:
        logger.error(f"Failed to unload Surya OCR models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/check-surya-status")
async def check_surya_status():
    """
    Check if Surya OCR models are currently loaded in GPU memory.

    - Returns loaded status (true/false)
    - Returns message describing current state
    """
    logger.info("API request to check Surya OCR status")

    try:
        from src.services.ocr_sequential import check_surya_models_status

        result = check_surya_models_status()

        if result['success']:
            return {
                "status": "success",
                "loaded": result['loaded'],
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    except Exception as e:
        logger.error(f"Failed to check Surya OCR status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EasyOCR GPU Management Endpoints
# ============================================================================

@router.get("/ocr/load-easyocr")
async def load_easyocr():
    """
    Load EasyOCR models into GPU memory.

    - Loads Arabic + English language models
    - Caches reader in memory for faster subsequent use
    - Returns success status and message
    """
    logger.info("API request to load EasyOCR models")

    try:
        global _easyocr_reader, _easyocr_loading

        if _easyocr_reader is not None:
            return {
                "status": "success",
                "message": "EasyOCR models already loaded in GPU"
            }

        if _easyocr_loading:
            return {
                "status": "loading",
                "message": "EasyOCR models are currently loading..."
            }

        # Load EasyOCR
        reader = get_easyocr_reader()

        if reader is not None:
            return {
                "status": "success",
                "message": "EasyOCR models loaded successfully (Arabic + English, GPU)"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to load EasyOCR models")

    except Exception as e:
        logger.error(f"Failed to load EasyOCR models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/unload-easyocr")
async def unload_easyocr():
    """
    Unload EasyOCR models from GPU memory to free VRAM.

    - Clears model references
    - Runs garbage collection
    - Clears CUDA cache
    - Returns success status and message
    """
    logger.info("API request to unload EasyOCR models")

    try:
        global _easyocr_reader

        if _easyocr_reader is None:
            return {
                "status": "success",
                "message": "EasyOCR models not loaded"
            }

        # Clear the reader
        _easyocr_reader = None

        # Force garbage collection and clear CUDA cache
        import gc
        gc.collect()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared after unloading EasyOCR")
        except ImportError:
            pass

        return {
            "status": "success",
            "message": "EasyOCR models unloaded from GPU"
        }

    except Exception as e:
        logger.error(f"Failed to unload EasyOCR models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/check-easyocr-status")
async def check_easyocr_status():
    """
    Check if EasyOCR models are currently loaded in GPU memory.

    - Returns loaded status (true/false)
    - Returns message describing current state
    """
    logger.info("API request to check EasyOCR status")

    try:
        global _easyocr_reader, _easyocr_loading

        if _easyocr_loading:
            return {
                "status": "success",
                "loaded": False,
                "loading": True,
                "message": "EasyOCR models are currently loading..."
            }

        if _easyocr_reader is not None:
            return {
                "status": "success",
                "loaded": True,
                "loading": False,
                "message": "EasyOCR models loaded (Arabic + English, GPU)"
            }
        else:
            return {
                "status": "success",
                "loaded": False,
                "loading": False,
                "message": "EasyOCR models not loaded"
            }

    except Exception as e:
        logger.error(f"Failed to check EasyOCR status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Combined OCR GPU Management Endpoints
# ============================================================================

@router.get("/ocr/load-all")
async def load_all_ocr():
    """
    Load Surya OCR, EasyOCR, and YOLO models into GPU memory.

    - Loads Surya OCR (Foundation, Detection, Recognition)
    - Loads EasyOCR (Arabic + English)
    - Loads YOLO (DocLayout-YOLO for layout detection)
    - Returns status for each engine
    """
    logger.info("API request to load all OCR/ML models")

    results = {
        "surya": {"loaded": False, "message": ""},
        "easyocr": {"loaded": False, "message": ""},
        "yolo": {"loaded": False, "message": ""}
    }

    # Load Surya
    try:
        from src.services.ocr_sequential import load_surya_models
        surya_result = load_surya_models()
        results["surya"]["loaded"] = surya_result.get('success', False)
        results["surya"]["message"] = surya_result.get('message', 'Unknown')
    except Exception as e:
        results["surya"]["message"] = f"Error: {str(e)}"

    # Load EasyOCR
    try:
        reader = get_easyocr_reader()
        if reader is not None:
            results["easyocr"]["loaded"] = True
            results["easyocr"]["message"] = "EasyOCR loaded (Arabic + English, GPU)"
        else:
            results["easyocr"]["message"] = "Failed to load EasyOCR"
    except Exception as e:
        results["easyocr"]["message"] = f"Error: {str(e)}"

    # Load YOLO
    try:
        from src.services.layout_detection_service import layout_detection_service, check_model_exists
        model_exists, model_msg = check_model_exists()
        if model_exists:
            success = layout_detection_service.load_model()
            results["yolo"]["loaded"] = success
            results["yolo"]["message"] = "YOLO loaded on GPU" if success else "Failed to load YOLO"
        else:
            results["yolo"]["message"] = model_msg
    except Exception as e:
        results["yolo"]["message"] = f"Error: {str(e)}"

    all_loaded = results["surya"]["loaded"] and results["easyocr"]["loaded"] and results["yolo"]["loaded"]

    return {
        "status": "success" if all_loaded else "partial",
        "all_loaded": all_loaded,
        "engines": results,
        "message": "All models loaded" if all_loaded else "Some models failed to load"
    }


@router.get("/ocr/unload-all")
async def unload_all_ocr():
    """
    Unload Surya OCR, EasyOCR, and YOLO models from GPU memory.

    - Clears all model references
    - Runs garbage collection
    - Clears CUDA cache
    - Returns status for each engine
    """
    logger.info("API request to unload all OCR/ML models")

    results = {
        "surya": {"unloaded": False, "message": ""},
        "easyocr": {"unloaded": False, "message": ""},
        "yolo": {"unloaded": False, "message": ""}
    }

    # Unload Surya
    try:
        from src.services.ocr_sequential import unload_surya_models
        surya_result = unload_surya_models()
        results["surya"]["unloaded"] = surya_result.get('success', False)
        results["surya"]["message"] = surya_result.get('message', 'Unknown')
    except Exception as e:
        results["surya"]["message"] = f"Error: {str(e)}"

    # Unload EasyOCR
    try:
        global _easyocr_reader
        _easyocr_reader = None
        results["easyocr"]["unloaded"] = True
        results["easyocr"]["message"] = "EasyOCR unloaded"
    except Exception as e:
        results["easyocr"]["message"] = f"Error: {str(e)}"

    # Unload YOLO
    try:
        from src.services.layout_detection_service import layout_detection_service
        layout_detection_service.unload_model()
        results["yolo"]["unloaded"] = True
        results["yolo"]["message"] = "YOLO unloaded"
    except Exception as e:
        results["yolo"]["message"] = f"Error: {str(e)}"

    # Force garbage collection and clear CUDA cache
    import gc
    gc.collect()

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("CUDA cache cleared after unloading all models")
    except ImportError:
        pass

    all_unloaded = results["surya"]["unloaded"] and results["easyocr"]["unloaded"] and results["yolo"]["unloaded"]

    return {
        "status": "success" if all_unloaded else "partial",
        "all_unloaded": all_unloaded,
        "engines": results,
        "message": "All models unloaded" if all_unloaded else "Some models failed to unload"
    }


@router.get("/ocr/check-all-status")
async def check_all_ocr_status():
    """
    Check status of all OCR/ML engines (Surya, EasyOCR, YOLO).

    - Returns loaded status for each engine
    - Returns overall status
    """
    logger.info("API request to check all OCR status")

    results = {
        "surya": {"loaded": False, "message": ""},
        "easyocr": {"loaded": False, "message": ""},
        "yolo": {"loaded": False, "message": "", "model_exists": False}
    }

    # Check Surya status
    try:
        from src.services.ocr_sequential import check_surya_models_status
        surya_result = check_surya_models_status()
        results["surya"]["loaded"] = surya_result.get('loaded', False)
        results["surya"]["message"] = surya_result.get('message', 'Unknown')
    except Exception as e:
        results["surya"]["message"] = f"Error: {str(e)}"

    # Check EasyOCR status
    try:
        global _easyocr_reader, _easyocr_loading
        if _easyocr_loading:
            results["easyocr"]["loaded"] = False
            results["easyocr"]["loading"] = True
            results["easyocr"]["message"] = "Loading..."
        elif _easyocr_reader is not None:
            results["easyocr"]["loaded"] = True
            results["easyocr"]["loading"] = False
            results["easyocr"]["message"] = "Loaded (Arabic + English, GPU)"
        else:
            results["easyocr"]["loaded"] = False
            results["easyocr"]["loading"] = False
            results["easyocr"]["message"] = "Not loaded"
    except Exception as e:
        results["easyocr"]["message"] = f"Error: {str(e)}"

    # Check YOLO status
    try:
        from src.services.layout_detection_service import layout_detection_service, check_model_exists
        model_exists, model_msg = check_model_exists()
        results["yolo"]["loaded"] = layout_detection_service.is_loaded
        results["yolo"]["model_exists"] = model_exists
        results["yolo"]["message"] = "Loaded on GPU" if layout_detection_service.is_loaded else ("Not loaded" if model_exists else model_msg)
    except Exception as e:
        results["yolo"]["message"] = f"Error: {str(e)}"

    all_loaded = results["surya"]["loaded"] and results["easyocr"]["loaded"] and results["yolo"]["loaded"]
    any_loaded = results["surya"]["loaded"] or results["easyocr"]["loaded"] or results["yolo"]["loaded"]

    return {
        "status": "success",
        "all_loaded": all_loaded,
        "any_loaded": any_loaded,
        "engines": results
    }


# ============================================================================
# YOLO Layout Detection GPU Management Endpoints
# ============================================================================

@router.get("/ocr/load-yolo")
async def load_yolo_model():
    """
    Load YOLO layout detection model into GPU memory.

    - Loads DocLayout-YOLO model for layout detection
    - Requires ~2.5 GB VRAM
    - Returns success status and message
    """
    logger.info("API request to load YOLO layout detection model")

    try:
        from src.services.layout_detection_service import layout_detection_service, check_model_exists

        # Check if model file exists
        model_exists, model_msg = check_model_exists()
        if not model_exists:
            return {
                "status": "error",
                "loaded": False,
                "message": model_msg
            }

        # Load model
        success = layout_detection_service.load_model()

        if success:
            return {
                "status": "success",
                "loaded": True,
                "message": "YOLO layout detection model loaded on GPU"
            }
        else:
            return {
                "status": "error",
                "loaded": False,
                "message": "Failed to load YOLO model"
            }

    except Exception as e:
        logger.error(f"Failed to load YOLO model: {e}")
        return {
            "status": "error",
            "loaded": False,
            "message": f"Error: {str(e)}"
        }


@router.get("/ocr/unload-yolo")
async def unload_yolo_model():
    """
    Unload YOLO layout detection model from GPU memory.

    - Clears model reference
    - Runs garbage collection
    - Clears CUDA cache
    - Returns success status
    """
    logger.info("API request to unload YOLO layout detection model")

    try:
        from src.services.layout_detection_service import layout_detection_service

        layout_detection_service.unload_model()

        return {
            "status": "success",
            "unloaded": True,
            "message": "YOLO model unloaded from GPU"
        }

    except Exception as e:
        logger.error(f"Failed to unload YOLO model: {e}")
        return {
            "status": "error",
            "unloaded": False,
            "message": f"Error: {str(e)}"
        }


@router.get("/ocr/check-yolo-status")
async def check_yolo_status():
    """
    Check if YOLO layout detection model is loaded.

    - Returns loaded status
    - Returns model info if loaded
    """
    logger.info("API request to check YOLO model status")

    try:
        from src.services.layout_detection_service import layout_detection_service, check_model_exists

        model_exists, model_msg = check_model_exists()

        return {
            "status": "success",
            "loaded": layout_detection_service.is_loaded,
            "model_exists": model_exists,
            "device": layout_detection_service.device if layout_detection_service.is_loaded else None,
            "message": "YOLO model loaded on GPU" if layout_detection_service.is_loaded else "YOLO model not loaded"
        }

    except Exception as e:
        logger.error(f"Failed to check YOLO status: {e}")
        return {
            "status": "error",
            "loaded": False,
            "message": f"Error: {str(e)}"
        }


@router.post("/ocr/surya", response_model=OCRResponse)
async def start_surya(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Start Surya OCR processing for a book.

    - Loads Surya OCR into GPU (2GB+ VRAM)
    - Processes all pages sequentially
    - Stores results in attr3_value (text) and attr6_value (confidence)
    - Image analysis SKIPPED (already done during first OCR)
    - Unloads Surya from GPU when complete
    - Supports max_pages parameter for testing (e.g., first 5 pages)
    """
    pages_msg = f" (max {request.max_pages} pages)" if request.max_pages else ""
    logger.info(f"Starting Surya OCR for book_id={request.book_id}{pages_msg}")

    try:
        # Import here to avoid circular dependencies
        from src.services.ocr_sequential import run_surya_sequential

        # Add to background tasks with max_pages parameter
        background_tasks.add_task(run_surya_sequential, request.book_id, request.max_pages)

        message = f"Surya OCR processing started in background{pages_msg}"
        return OCRResponse(
            book_id=request.book_id,
            status="processing",
            message=message
        )

    except Exception as e:
        logger.error(f"Failed to start Surya OCR for book_id={request.book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr/tesseract", response_model=OCRResponse)
async def start_tesseract(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Start Tesseract OCR processing for a book.

    - Runs Tesseract (CPU-based, no GPU)
    - Processes all pages sequentially
    - Stores results in attr4_value (text) and attr7_value (confidence)
    - Image analysis SKIPPED (already done during first OCR)
    """
    logger.info(f"Starting Tesseract for book_id={request.book_id}")

    try:
        # Import here to avoid circular dependencies
        from src.services.ocr_sequential import run_tesseract_sequential

        # Add to background tasks
        background_tasks.add_task(run_tesseract_sequential, request.book_id)

        return OCRResponse(
            book_id=request.book_id,
            status="processing",
            message="Tesseract processing started in background"
        )

    except Exception as e:
        logger.error(f"Failed to start Tesseract for book_id={request.book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-split-mark", response_model=OCRResponse)
async def evaluate_split_mark(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    Evaluate OCR results, select best, run splitter and marker agents.

    Process:
    1. Evaluation: Compare confidence scores (attr5, attr6, attr7)
    2. Select best OCR result per page
    3. Copy winning text to main text_content field
    4. Run Splitter Agent (semantic 3-5 line chunks)
    5. Run Marker Agent (green/orange rectangles)
    6. Update status to "ready for verification"
    """
    logger.info(f"Starting Evaluate/Split/Mark for book_id={request.book_id}")

    try:
        # Import here to avoid circular dependencies
        from src.services.ocr_sequential import run_evaluate_split_mark

        # Add to background tasks
        background_tasks.add_task(run_evaluate_split_mark, request.book_id)

        return OCRResponse(
            book_id=request.book_id,
            status="processing",
            message="Evaluation and processing started in background"
        )

    except Exception as e:
        logger.error(f"Failed to start Evaluate/Split/Mark for book_id={request.book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/status/{book_id}")
async def get_ocr_status(book_id: int):
    """
    Get OCR processing status for a book.

    Returns completion flags for:
    - EasyOCR
    - Surya OCR
    - Tesseract
    - Image processing
    - Evaluation
    - Splitter
    - Marker
    """
    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get processing state
            state = db.execute(
                text(f"""
                SELECT easyocr_complete, surya_ocr_complete, tesseract_complete,
                       images_processed, evaluation_complete, splitter_complete,
                       marker_complete, current_agent, status
                FROM {table_prefix}_processing_state
                WHERE id = 1
                """)
            ).first()

            if not state:
                raise HTTPException(status_code=404, detail="Processing state not found")

            return {
                "book_id": book_id,
                "easyocr_complete": state[0],
                "surya_ocr_complete": state[1],
                "tesseract_complete": state[2],
                "images_processed": state[3],
                "evaluation_complete": state[4],
                "splitter_complete": state[5],
                "marker_complete": state[6],
                "current_agent": state[7],
                "status": state[8]
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to get OCR status for book_id={book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Interactive Clip OCR Endpoints (for Clip+OCR mode on verify-pages)
# ============================================================================

class ClipOCRRequest(BaseModel):
    """Request model for interactive clip OCR"""
    book_id: int
    page_number: int
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int
    image_data_base64: str  # Base64 encoded cropped image
    level: Optional[str] = "Level 1"


class ClipOCRResponse(BaseModel):
    """Response model for clip OCR"""
    success: bool
    ocr_text: str
    confidence: float
    language: str
    knowledge_unit_id: int
    clip_id: int
    message: str


class UpdateClipTextRequest(BaseModel):
    """Request model for updating clip text"""
    book_id: int
    knowledge_unit_id: int
    text: str


@router.post("/ocr/surya-clip", response_model=ClipOCRResponse)
async def run_surya_ocr_on_clip(request: ClipOCRRequest):
    """
    Run Surya OCR on a user-selected image clip.

    This endpoint is used in "Clip+OCR" mode on the verify-pages UI.
    It performs the following steps:
    1. Saves the cropped image to paragraph_images table
    2. Runs Surya OCR on the cropped image
    3. Creates a knowledge_unit record with the OCR text
    4. Returns the OCR result for display in the UI

    Unlike full-page OCR, this processes a single clip immediately (synchronous).
    """
    logger.info(f"Running Surya OCR on clip for book_id={request.book_id}, page={request.page_number}")

    try:
        from src.services.ocr_sequential import run_surya_on_single_image
        from src.database.connection import SessionLocal, engine
        from sqlalchemy import text
        import base64

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get raw_page_id for this page
            raw_page_result = db.execute(
                text(f"SELECT id FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
                {"page_num": request.page_number}
            ).first()

            if not raw_page_result:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} not found in raw_pages")

            raw_page_id = raw_page_result[0]

            # Decode base64 image
            # Remove data URL prefix if present
            image_data_str = request.image_data_base64
            if ',' in image_data_str:
                image_data_str = image_data_str.split(',')[1]

            image_bytes = base64.b64decode(image_data_str)
            image_size = len(image_bytes)

            # Step 1: Save cropped image to paragraph_images table (initially without OCR text)
            insert_clip_sql = text(f"""
                INSERT INTO raw_{table_prefix}_paragraph_images (
                    raw_page_id, page_number,
                    selection_x, selection_y, selection_width, selection_height,
                    image_data, image_format,
                    image_width, image_height, image_size_bytes,
                    level, approval_status, display_order, is_enabled
                ) VALUES (
                    :raw_page_id, :page_number,
                    :selection_x, :selection_y, :selection_width, :selection_height,
                    :image_data, 'png',
                    :selection_width, :selection_height, :image_size_bytes,
                    :level, 'pending', 0, true
                )
                RETURNING id
            """)

            clip_result = db.execute(insert_clip_sql, {
                "raw_page_id": raw_page_id,
                "page_number": request.page_number,
                "selection_x": request.selection_x,
                "selection_y": request.selection_y,
                "selection_width": request.selection_width,
                "selection_height": request.selection_height,
                "image_data": image_bytes,
                "image_size_bytes": image_size,
                "level": request.level
            })
            clip_id = clip_result.fetchone()[0]
            db.commit()

            logger.info(f"Saved clip {clip_id} to paragraph_images")

            # Step 2: Run Surya OCR on the image
            ocr_result = run_surya_on_single_image(image_bytes)

            if not ocr_result['success']:
                raise HTTPException(status_code=500, detail=f"OCR failed: {ocr_result.get('error', 'Unknown error')}")

            ocr_text = ocr_result['text']
            confidence = ocr_result['confidence']
            language = ocr_result.get('language', 'auto')

            # Step 3: Create knowledge_unit record with OCR text
            insert_ku_sql = text(f"""
                INSERT INTO {table_prefix}_knowledge_units (
                    page_number,
                    text_content,
                    ocr_method,
                    confidence_score,
                    language,
                    position_x, position_y,
                    attr1_value,
                    attr3_value,
                    attr6_value,
                    attr8_value,
                    verified
                ) VALUES (
                    :page_number,
                    :text_content,
                    'surya',
                    :confidence_score,
                    :language,
                    :position_x, :position_y,
                    :clip_reference,
                    :surya_text,
                    :surya_confidence,
                    'enabled',
                    false
                )
                RETURNING unit_id
            """)

            ku_result = db.execute(insert_ku_sql, {
                "page_number": request.page_number,
                "text_content": ocr_text,
                "confidence_score": confidence,
                "language": language,
                "position_x": request.selection_x,
                "position_y": request.selection_y,
                "clip_reference": f"paragraph_image:{clip_id}",
                "surya_text": ocr_text,
                "surya_confidence": str(confidence)
            })
            knowledge_unit_id = ku_result.fetchone()[0]
            db.commit()

            logger.info(f"Created knowledge_unit {knowledge_unit_id} with OCR text")

            # Step 4: Update paragraph_images with OCR text and linked KU ID
            update_clip_sql = text(f"""
                UPDATE raw_{table_prefix}_paragraph_images
                SET extracted_text = :extracted_text,
                    ocr_confidence = :ocr_confidence,
                    linked_knowledge_unit_id = :linked_ku_id
                WHERE id = :clip_id
            """)

            db.execute(update_clip_sql, {
                "extracted_text": ocr_text,
                "ocr_confidence": confidence,
                "linked_ku_id": knowledge_unit_id,
                "clip_id": clip_id
            })
            db.commit()

            logger.info(f"Updated paragraph_images clip {clip_id} with OCR text and linked KU {knowledge_unit_id}")

            return ClipOCRResponse(
                success=True,
                ocr_text=ocr_text,
                confidence=confidence,
                language=language,
                knowledge_unit_id=knowledge_unit_id,
                clip_id=clip_id,
                message="OCR completed successfully"
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run Surya OCR on clip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/ocr/update-clip-text")
async def update_clip_text(request: UpdateClipTextRequest):
    """
    Update the OCR text for a knowledge unit (after user edits).

    Used when user modifies the OCR text in the UI and clicks Save.
    """
    logger.info(f"Updating text for knowledge_unit {request.knowledge_unit_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Update the knowledge unit
            update_sql = text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET text_content = :text,
                    attr3_value = :text,
                    updated_at = NOW()
                WHERE unit_id = :unit_id
            """)

            result = db.execute(update_sql, {
                "text": request.text,
                "unit_id": request.knowledge_unit_id
            })
            db.commit()

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Knowledge unit not found")

            return {
                "success": True,
                "message": "Text updated successfully",
                "knowledge_unit_id": request.knowledge_unit_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update clip text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Diagram Analysis Endpoints
# ============================================================================

class DiagramAnalysisRequest(BaseModel):
    """Request model for diagram analysis"""
    book_id: int
    page_number: int
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int
    image_data_base64: str
    level: Optional[str] = "Level 1"
    use_claude: Optional[bool] = True
    use_surya: Optional[bool] = True
    prompt_type: Optional[str] = "diagram"  # "diagram", "equation", or "table"


class DiagramAnalysisResponse(BaseModel):
    """Response model for diagram analysis"""
    success: bool
    diagram_id: int
    knowledge_unit_id: int
    description: str
    diagram_type: str
    extracted_text: str
    ai_model: str
    message: str


class UpdateDiagramDescriptionRequest(BaseModel):
    """Request model for updating diagram description"""
    book_id: int
    diagram_id: int
    description: str


class SaveDiagramLinkRequest(BaseModel):
    """Request model for linking diagram to knowledge unit"""
    book_id: int
    diagram_id: int
    knowledge_unit_id: Optional[int] = None  # None means unlink


@router.post("/ocr/analyze-diagram", response_model=DiagramAnalysisResponse)
async def analyze_diagram(request: DiagramAnalysisRequest):
    """
    Analyze a user-selected diagram image.

    This endpoint performs the full diagram analysis workflow:
    1. Saves the cropped diagram image to diagram_images table
    2. Runs Surya OCR to extract text labels
    3. Runs Claude Vision for comprehensive diagram analysis
    4. Creates a knowledge_unit record linked to the diagram
    5. Returns the analysis for display in the UI

    The analysis includes:
    - Diagram type classification
    - Component identification
    - Relationship mapping
    - Text label extraction
    - Comprehensive description
    """
    logger.info(f"Analyzing diagram for book_id={request.book_id}, page={request.page_number}")

    try:
        from src.services.diagram_analyzer import analyze_diagram_full, format_diagram_description
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        import base64
        import json

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get raw_page_id for this page
            raw_page_result = db.execute(
                text(f"SELECT id FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
                {"page_num": request.page_number}
            ).first()

            if not raw_page_result:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} not found in raw_pages")

            raw_page_id = raw_page_result[0]

            # Decode base64 image
            image_data_str = request.image_data_base64
            if ',' in image_data_str:
                image_data_str = image_data_str.split(',')[1]

            image_bytes = base64.b64decode(image_data_str)
            image_size = len(image_bytes)

            # Step 1: Save diagram image to diagram_images table
            logger.info("Step 1: Saving diagram image to database...")
            insert_diagram_sql = text(f"""
                INSERT INTO raw_{table_prefix}_diagram_images (
                    raw_page_id, page_number,
                    selection_x, selection_y, selection_width, selection_height,
                    image_data, image_format,
                    image_width, image_height, image_size_bytes,
                    level, approval_status, display_order, is_enabled
                ) VALUES (
                    :raw_page_id, :page_number,
                    :selection_x, :selection_y, :selection_width, :selection_height,
                    :image_data, 'png',
                    :selection_width, :selection_height, :image_size_bytes,
                    :level, 'pending', 0, true
                )
                RETURNING id
            """)

            diagram_result = db.execute(insert_diagram_sql, {
                "raw_page_id": raw_page_id,
                "page_number": request.page_number,
                "selection_x": request.selection_x,
                "selection_y": request.selection_y,
                "selection_width": request.selection_width,
                "selection_height": request.selection_height,
                "image_data": image_bytes,
                "image_size_bytes": image_size,
                "level": request.level
            })
            diagram_id = diagram_result.fetchone()[0]
            db.commit()
            logger.info(f"Saved diagram {diagram_id} to diagram_images")

            # Get book settings to retrieve custom prompts
            logger.info("Step 2a: Fetching book settings for custom prompts...")
            from src.database.services.book_settings_service import BookSettingsService
            settings_service = BookSettingsService()
            
            custom_prompt = None
            try:
                book_settings = settings_service.get_settings(request.book_id)
                
                # Select prompt based on prompt_type
                if request.prompt_type == 'diagram':
                    custom_prompt = book_settings.get('diagram_prompt')
                elif request.prompt_type == 'equation':
                    custom_prompt = book_settings.get('equation_prompt')
                elif request.prompt_type == 'table':
                    custom_prompt = book_settings.get('table_prompt')
                
                if custom_prompt:
                    logger.info(f"Using custom {request.prompt_type} prompt from book settings")
                else:
                    logger.info(f"No custom prompt found for {request.prompt_type}, using default")
            except Exception as e:
                logger.warning(f"Failed to get custom prompt: {e}, using default")
                custom_prompt = None

            # Step 2: Run full diagram analysis (OCR + Claude Vision)
            logger.info("Step 2b: Running diagram analysis...")
            analysis_result = analyze_diagram_full(
                image_bytes,
                use_claude=request.use_claude,
                use_surya=request.use_surya,
                custom_prompt=custom_prompt
            )

            # Get formatted description
            description = analysis_result.get('description', '')
            if not description and analysis_result.get('extracted_text'):
                description = f"Extracted text: {analysis_result['extracted_text']}"

            diagram_type = analysis_result.get('diagram_type', 'unknown')
            extracted_text = analysis_result.get('extracted_text', '')
            ai_model = analysis_result.get('ai_model', 'none')
            structured_json = analysis_result.get('structured_json', {})
            ocr_confidence = analysis_result.get('ocr_confidence', 0.0)

            # Step 3: Update diagram record with analysis results
            logger.info("Step 3: Updating diagram with analysis results...")
            update_diagram_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET description = :description,
                    extracted_text = :extracted_text,
                    diagram_type = :diagram_type,
                    structured_json = :structured_json,
                    ai_model = :ai_model,
                    ai_confidence = :ai_confidence,
                    analyzed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            db.execute(update_diagram_sql, {
                "description": description,
                "extracted_text": extracted_text,
                "diagram_type": diagram_type,
                "structured_json": json.dumps(structured_json) if structured_json else None,
                "ai_model": ai_model,
                "ai_confidence": ocr_confidence,
                "diagram_id": diagram_id
            })
            db.commit()

            # Step 4: Create knowledge_unit record linked to diagram
            logger.info("Step 4: Creating knowledge unit...")
            insert_ku_sql = text(f"""
                INSERT INTO {table_prefix}_knowledge_units (
                    page_number,
                    text_content,
                    ocr_method,
                    confidence_score,
                    language,
                    position_x, position_y,
                    attr1_value,
                    attr3_value,
                    attr8_value,
                    verified
                ) VALUES (
                    :page_number,
                    :text_content,
                    'diagram_analysis',
                    :confidence_score,
                    'auto',
                    :position_x, :position_y,
                    :diagram_reference,
                    :extracted_text,
                    'enabled',
                    false
                )
                RETURNING unit_id
            """)

            ku_result = db.execute(insert_ku_sql, {
                "page_number": request.page_number,
                "text_content": description,
                "confidence_score": ocr_confidence,
                "position_x": request.selection_x,
                "position_y": request.selection_y,
                "diagram_reference": f"diagram_image:{diagram_id}",
                "extracted_text": extracted_text
            })
            knowledge_unit_id = ku_result.fetchone()[0]
            db.commit()

            logger.info(f"Created knowledge_unit {knowledge_unit_id} for diagram {diagram_id}")

            return DiagramAnalysisResponse(
                success=True,
                diagram_id=diagram_id,
                knowledge_unit_id=knowledge_unit_id,
                description=description,
                diagram_type=diagram_type,
                extracted_text=extracted_text,
                ai_model=ai_model,
                message="Diagram analysis completed successfully"
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze diagram: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/diagrams/update-description")
async def update_diagram_description(request: UpdateDiagramDescriptionRequest):
    """
    Update the description of a diagram (after user edits).
    Also updates the linked knowledge_unit if it exists.
    """
    logger.info(f"Updating description for diagram {request.diagram_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Update diagram description
            update_diagram_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET description = :description,
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            result = db.execute(update_diagram_sql, {
                "description": request.description,
                "diagram_id": request.diagram_id
            })

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Diagram not found")

            # Also update the linked knowledge_unit if exists
            update_ku_sql = text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET text_content = :description,
                    updated_at = NOW()
                WHERE attr1_value = :diagram_reference
            """)

            db.execute(update_ku_sql, {
                "description": request.description,
                "diagram_reference": f"diagram_image:{request.diagram_id}"
            })

            db.commit()

            return {
                "success": True,
                "message": "Diagram description updated successfully",
                "diagram_id": request.diagram_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update diagram description: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/diagrams/save-link")
async def save_diagram_link(request: SaveDiagramLinkRequest):
    """
    Link or unlink a diagram to/from a knowledge unit.

    This allows users to associate diagrams with related text paragraphs.
    Pass knowledge_unit_id=null to unlink.
    """
    logger.info(f"Saving link for diagram {request.diagram_id} -> KU {request.knowledge_unit_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Verify diagram exists
            diagram_check = db.execute(
                text(f"SELECT id FROM raw_{table_prefix}_diagram_images WHERE id = :diagram_id"),
                {"diagram_id": request.diagram_id}
            ).first()

            if not diagram_check:
                raise HTTPException(status_code=404, detail="Diagram not found")

            # If linking, verify knowledge unit exists
            if request.knowledge_unit_id is not None:
                ku_check = db.execute(
                    text(f"SELECT unit_id FROM {table_prefix}_knowledge_units WHERE unit_id = :ku_id"),
                    {"ku_id": request.knowledge_unit_id}
                ).first()

                if not ku_check:
                    raise HTTPException(status_code=404, detail="Knowledge unit not found")

            # Update the link
            update_link_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET linked_knowledge_unit_id = :ku_id,
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            db.execute(update_link_sql, {
                "ku_id": request.knowledge_unit_id,
                "diagram_id": request.diagram_id
            })

            db.commit()

            action = "linked" if request.knowledge_unit_id else "unlinked"
            return {
                "success": True,
                "message": f"Diagram {action} successfully",
                "diagram_id": request.diagram_id,
                "linked_knowledge_unit_id": request.knowledge_unit_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save diagram link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SaveDiagramAllRequest(BaseModel):
    """Request model for saving all diagram data including level titles"""
    book_id: int
    diagram_id: int
    level_1_title: Optional[str] = None
    level_2_title: Optional[str] = None
    level_3_title: Optional[str] = None
    level_4_title: Optional[str] = None
    level_5_title: Optional[str] = None
    linked_knowledge_unit_id: Optional[int] = None
    description: Optional[str] = None
    selected_level_number: Optional[int] = None
    selected_level_text: Optional[str] = None
    prompt_type: Optional[str] = None  # 'diagram', 'equation', or 'table'


@router.patch("/diagrams/save-all")
async def save_diagram_all(request: SaveDiagramAllRequest):
    """
    Save all diagram data including level titles, linked KU, and description.

    This endpoint updates:
    - level_1_title through level_5_title
    - linked_knowledge_unit_id
    - description
    """
    logger.info(f"Saving all data for diagram {request.diagram_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Verify diagram exists
            diagram_check = db.execute(
                text(f"SELECT id FROM raw_{table_prefix}_diagram_images WHERE id = :diagram_id"),
                {"diagram_id": request.diagram_id}
            ).first()

            if not diagram_check:
                raise HTTPException(status_code=404, detail="Diagram not found")

            # If linking, verify knowledge unit exists
            if request.linked_knowledge_unit_id is not None:
                ku_check = db.execute(
                    text(f"SELECT unit_id FROM {table_prefix}_knowledge_units WHERE unit_id = :ku_id"),
                    {"ku_id": request.linked_knowledge_unit_id}
                ).first()

                if not ku_check:
                    raise HTTPException(status_code=404, detail="Knowledge unit not found")

            # Update diagram with all data
            update_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET level_1_title = :level_1_title,
                    level_2_title = :level_2_title,
                    level_3_title = :level_3_title,
                    level_4_title = :level_4_title,
                    level_5_title = :level_5_title,
                    linked_knowledge_unit_id = :linked_ku_id,
                    description = :description,
                    selected_level_number = :selected_level_number,
                    selected_level_text = :selected_level_text,
                    prompt_type = :prompt_type,
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            db.execute(update_sql, {
                "level_1_title": request.level_1_title,
                "level_2_title": request.level_2_title,
                "level_3_title": request.level_3_title,
                "level_4_title": request.level_4_title,
                "level_5_title": request.level_5_title,
                "linked_ku_id": request.linked_knowledge_unit_id,
                "description": request.description,
                "selected_level_number": request.selected_level_number,
                "selected_level_text": request.selected_level_text,
                "prompt_type": request.prompt_type,
                "diagram_id": request.diagram_id
            })

            # Also update linked knowledge_unit if exists
            update_ku_sql = text(f"""
                UPDATE {table_prefix}_knowledge_units
                SET text_content = :description,
                    updated_at = NOW()
                WHERE attr1_value = :diagram_reference
            """)

            db.execute(update_ku_sql, {
                "description": request.description,
                "diagram_reference": f"diagram_image:{request.diagram_id}"
            })

            db.commit()

            return {
                "success": True,
                "message": "Diagram data saved successfully",
                "diagram_id": request.diagram_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save diagram data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagrams/{book_id}/knowledge-units-for-page/{page_number}")
async def get_knowledge_units_for_page(book_id: int, page_number: int):
    """
    Get all knowledge units for a specific page.

    Used to populate the dropdown for linking diagrams to paragraphs.
    """
    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get knowledge units for this page (excluding diagrams)
            select_sql = text(f"""
                SELECT unit_id, text_content, attr1_value
                FROM {table_prefix}_knowledge_units
                WHERE page_number = :page_number
                  AND (attr1_value IS NULL OR attr1_value NOT LIKE 'diagram_image:%')
                  AND attr8_value = 'enabled'
                ORDER BY position_y, position_x
            """)

            rows = db.execute(select_sql, {"page_number": page_number}).fetchall()

            knowledge_units = []
            for row in rows:
                # Truncate text for dropdown display
                text_preview = row[1][:100] if row[1] else ""
                if len(row[1] or "") > 100:
                    text_preview += "..."

                knowledge_units.append({
                    "unit_id": row[0],
                    "text_preview": text_preview,
                    "is_paragraph": row[2] and row[2].startswith("paragraph_image:")
                })

            return {
                "success": True,
                "page_number": page_number,
                "knowledge_units": knowledge_units
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge units for page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Multi-OCR Comparison Endpoints
# ============================================================================

class MultiOcrRequest(BaseModel):
    """Request model for multi-OCR comparison"""
    book_id: int
    page_number: int
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int
    image_data_base64: str
    level: Optional[str] = "Level 1"


class MultiOcrResponse(BaseModel):
    """Response model for multi-OCR"""
    success: bool
    ocr_text: str
    confidence: float
    ocr_engine: str
    message: str


@router.post("/ocr/multi-surya-600", response_model=MultiOcrResponse)
async def multi_surya_600(request: MultiOcrRequest):
    """
    Run Surya OCR at full 600 DPI resolution.
    Does NOT save to database - just returns OCR result for comparison.
    """
    logger.info(f"Running Surya OCR (600 DPI) for book_id={request.book_id}, page={request.page_number}")

    try:
        from src.services.ocr_sequential import run_surya_on_single_image
        import base64

        # Decode base64 image
        image_data_str = request.image_data_base64
        if ',' in image_data_str:
            image_data_str = image_data_str.split(',')[1]
        image_bytes = base64.b64decode(image_data_str)

        # Run Surya OCR at full resolution
        ocr_result = run_surya_on_single_image(image_bytes)

        if not ocr_result['success']:
            return MultiOcrResponse(
                success=False,
                ocr_text="",
                confidence=0,
                ocr_engine="surya-600",
                message=f"OCR failed: {ocr_result.get('error', 'Unknown error')}"
            )

        return MultiOcrResponse(
            success=True,
            ocr_text=ocr_result['text'],
            confidence=ocr_result['confidence'],
            ocr_engine="surya-600",
            message="Surya OCR (600 DPI) completed"
        )

    except Exception as e:
        logger.error(f"Surya 600 DPI OCR error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr/multi-surya-downsampled", response_model=MultiOcrResponse)
async def multi_surya_downsampled(request: MultiOcrRequest):
    """
    Run Surya OCR with image downsampled to ~2048px width (Surya recommended).
    Does NOT save to database - just returns OCR result for comparison.
    """
    logger.info(f"Running Surya OCR (downsampled) for book_id={request.book_id}, page={request.page_number}")

    try:
        from src.services.ocr_sequential import run_surya_on_single_image
        from PIL import Image
        import base64
        import io

        # Decode base64 image
        image_data_str = request.image_data_base64
        if ',' in image_data_str:
            image_data_str = image_data_str.split(',')[1]
        image_bytes = base64.b64decode(image_data_str)

        # Load and downsample image if needed
        img = Image.open(io.BytesIO(image_bytes))
        original_width, original_height = img.size

        # Downsample to ~2048px width if larger
        max_width = 2048
        if original_width > max_width:
            scale_factor = max_width / original_width
            new_width = max_width
            new_height = int(original_height * scale_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            logger.info(f"Downsampled from {original_width}x{original_height} to {new_width}x{new_height}")

        # Convert back to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        downsampled_bytes = buffer.getvalue()

        # Run Surya OCR on downsampled image
        ocr_result = run_surya_on_single_image(downsampled_bytes)

        if not ocr_result['success']:
            return MultiOcrResponse(
                success=False,
                ocr_text="",
                confidence=0,
                ocr_engine="surya-ds",
                message=f"OCR failed: {ocr_result.get('error', 'Unknown error')}"
            )

        return MultiOcrResponse(
            success=True,
            ocr_text=ocr_result['text'],
            confidence=ocr_result['confidence'],
            ocr_engine="surya-ds",
            message=f"Surya OCR (downsampled to {img.size[0]}px) completed"
        )

    except Exception as e:
        logger.error(f"Surya downsampled OCR error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr/multi-tesseract-arabic", response_model=MultiOcrResponse)
async def multi_tesseract_arabic(request: MultiOcrRequest):
    """
    Run Tesseract OCR with Arabic+English language pack.
    Does NOT save to database - just returns OCR result for comparison.
    """
    logger.info(f"Running Tesseract Arabic OCR for book_id={request.book_id}, page={request.page_number}")

    try:
        import pytesseract
        from PIL import Image
        import base64
        import io

        # Decode base64 image
        image_data_str = request.image_data_base64
        if ',' in image_data_str:
            image_data_str = image_data_str.split(',')[1]
        image_bytes = base64.b64decode(image_data_str)

        # Load image
        img = Image.open(io.BytesIO(image_bytes))

        # Run Tesseract with Arabic + English
        # Use ara+eng for Arabic with English fallback
        ocr_text = pytesseract.image_to_string(img, lang='ara+eng')

        # Get confidence data
        data = pytesseract.image_to_data(img, lang='ara+eng', output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data['conf'] if c != '-1' and str(c).isdigit()]
        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5

        return MultiOcrResponse(
            success=True,
            ocr_text=ocr_text.strip(),
            confidence=avg_confidence,
            ocr_engine="tesseract",
            message="Tesseract Arabic OCR completed"
        )

    except Exception as e:
        logger.error(f"Tesseract Arabic OCR error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Global EasyOCR reader cache (loaded once, reused for all requests)
_easyocr_reader = None
_easyocr_loading = False

def get_easyocr_reader():
    """Get or create cached EasyOCR reader with GPU support."""
    global _easyocr_reader, _easyocr_loading
    import sys
    import io as stdio
    import os

    if _easyocr_reader is None and not _easyocr_loading:
        _easyocr_loading = True
        try:
            import easyocr
            from src.utils.logging_config import logger
            logger.info("Loading EasyOCR reader with GPU support (Arabic + English)...")

            # Suppress EasyOCR's progress bar output on Windows (charmap encoding issue)
            # The progress bar uses Unicode block characters that Windows cp1252 can't encode
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            if os.name == 'nt':  # Windows
                sys.stdout = stdio.TextIOWrapper(stdio.BytesIO(), encoding='utf-8')
                sys.stderr = stdio.TextIOWrapper(stdio.BytesIO(), encoding='utf-8')

            try:
                _easyocr_reader = easyocr.Reader(['ar', 'en'], gpu=True, verbose=False)
            finally:
                if os.name == 'nt':
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

            logger.info("EasyOCR reader loaded successfully on GPU")
        except Exception as e:
            from src.utils.logging_config import logger
            logger.warning(f"Failed to load EasyOCR with GPU, trying CPU: {e}")
            try:
                import easyocr

                # Same suppression for CPU fallback
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                if os.name == 'nt':
                    sys.stdout = stdio.TextIOWrapper(stdio.BytesIO(), encoding='utf-8')
                    sys.stderr = stdio.TextIOWrapper(stdio.BytesIO(), encoding='utf-8')

                try:
                    _easyocr_reader = easyocr.Reader(['ar', 'en'], gpu=False, verbose=False)
                finally:
                    if os.name == 'nt':
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr

                logger.info("EasyOCR reader loaded on CPU")
            except Exception as e2:
                logger.error(f"Failed to load EasyOCR: {e2}")
                _easyocr_loading = False
                raise
        finally:
            _easyocr_loading = False

    return _easyocr_reader


@router.post("/ocr/multi-easyocr", response_model=MultiOcrResponse)
async def multi_easyocr(request: MultiOcrRequest):
    """
    Run EasyOCR with Arabic+English support (GPU accelerated).
    Does NOT save to database - just returns OCR result for comparison.
    """
    logger.info(f"Running EasyOCR for book_id={request.book_id}, page={request.page_number}")

    try:
        from PIL import Image
        import base64
        import io
        import numpy as np

        # Decode base64 image
        image_data_str = request.image_data_base64
        if ',' in image_data_str:
            image_data_str = image_data_str.split(',')[1]
        image_bytes = base64.b64decode(image_data_str)

        # Load image and convert to numpy array
        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img)

        # Get cached EasyOCR reader (GPU accelerated)
        reader = get_easyocr_reader()

        # Run OCR
        results = reader.readtext(img_array)

        # Extract text and confidence
        texts = []
        confidences = []
        for (bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)

        ocr_text = ' '.join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        return MultiOcrResponse(
            success=True,
            ocr_text=ocr_text,
            confidence=avg_confidence,
            ocr_engine="easyocr",
            message="EasyOCR completed (GPU)"
        )

    except Exception as e:
        logger.error(f"EasyOCR error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SaveMultiOcrRequest(BaseModel):
    """Request model for saving selected multi-OCR result"""
    book_id: int
    page_number: int
    selection_x: int
    selection_y: int
    selection_width: int
    selection_height: int
    image_data_base64: str
    ocr_text: str
    confidence: float
    ocr_engine: str
    level: Optional[str] = "Level 1"
    selected_level_number: Optional[int] = None
    selected_level_text: Optional[str] = None
    # Additional OCR texts (from Area 1, 2, 3)
    ocr_text_1: Optional[str] = None
    ocr_text_2: Optional[str] = None
    ocr_text_3: Optional[str] = None
    # Manual texts (from Manual 1, 2, 3)
    manual_text_1: Optional[str] = None
    manual_text_2: Optional[str] = None
    manual_text_3: Optional[str] = None


@router.post("/ocr/save-multi-ocr-result")
async def save_multi_ocr_result(request: SaveMultiOcrRequest):
    """
    Save the selected OCR result from multi-OCR comparison.
    Creates paragraph_image record, knowledge_unit, and links them.
    """
    logger.info(f"Saving multi-OCR result for book_id={request.book_id}, engine={request.ocr_engine}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        import base64

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get raw_page_id for this page
            raw_page_result = db.execute(
                text(f"SELECT id FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
                {"page_num": request.page_number}
            ).first()

            if not raw_page_result:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} not found")

            raw_page_id = raw_page_result[0]

            # Decode base64 image
            image_data_str = request.image_data_base64
            if ',' in image_data_str:
                image_data_str = image_data_str.split(',')[1]
            image_bytes = base64.b64decode(image_data_str)
            image_size = len(image_bytes)

            # Save to paragraph_images
            insert_clip_sql = text(f"""
                INSERT INTO raw_{table_prefix}_paragraph_images (
                    raw_page_id, page_number,
                    selection_x, selection_y, selection_width, selection_height,
                    image_data, image_format,
                    image_width, image_height, image_size_bytes,
                    extracted_text, ocr_confidence,
                    level, approval_status, display_order, is_enabled,
                    selected_level_number, selected_level_text
                ) VALUES (
                    :raw_page_id, :page_number,
                    :selection_x, :selection_y, :selection_width, :selection_height,
                    :image_data, 'png',
                    :selection_width, :selection_height, :image_size_bytes,
                    :extracted_text, :ocr_confidence,
                    :level, 'pending', 0, true,
                    :selected_level_number, :selected_level_text
                )
                RETURNING id
            """)

            clip_result = db.execute(insert_clip_sql, {
                "raw_page_id": raw_page_id,
                "page_number": request.page_number,
                "selection_x": request.selection_x,
                "selection_y": request.selection_y,
                "selection_width": request.selection_width,
                "selection_height": request.selection_height,
                "image_data": image_bytes,
                "image_size_bytes": image_size,
                "extracted_text": request.ocr_text,
                "ocr_confidence": request.confidence,
                "level": request.level,
                "selected_level_number": request.selected_level_number,
                "selected_level_text": request.selected_level_text
            })
            clip_id = clip_result.fetchone()[0]
            db.commit()

            logger.info(f"Saved paragraph_image clip {clip_id}")

            # Create knowledge_unit
            insert_ku_sql = text(f"""
                INSERT INTO {table_prefix}_knowledge_units (
                    page_number,
                    text_content,
                    ocr_method,
                    confidence_score,
                    language,
                    position_x, position_y,
                    attr1_value,
                    attr3_value,
                    attr6_value,
                    attr8_value,
                    verified
                ) VALUES (
                    :page_number,
                    :text_content,
                    :ocr_method,
                    :confidence_score,
                    'auto',
                    :position_x, :position_y,
                    :clip_reference,
                    :ocr_text,
                    :confidence_str,
                    'enabled',
                    false
                )
                RETURNING unit_id
            """)

            ku_result = db.execute(insert_ku_sql, {
                "page_number": request.page_number,
                "text_content": request.ocr_text,
                "ocr_method": request.ocr_engine,
                "confidence_score": request.confidence,
                "position_x": request.selection_x,
                "position_y": request.selection_y,
                "clip_reference": f"paragraph_image:{clip_id}",
                "ocr_text": request.ocr_text,
                "confidence_str": str(request.confidence)
            })
            knowledge_unit_id = ku_result.fetchone()[0]
            db.commit()

            logger.info(f"Created knowledge_unit {knowledge_unit_id}")

            # Link clip to knowledge unit
            update_clip_sql = text(f"""
                UPDATE raw_{table_prefix}_paragraph_images
                SET linked_knowledge_unit_id = :ku_id
                WHERE id = :clip_id
            """)

            db.execute(update_clip_sql, {
                "ku_id": knowledge_unit_id,
                "clip_id": clip_id
            })
            db.commit()

            # Save additional OCR and manual texts if provided
            additional_texts_saved = False
            if any([request.ocr_text_1, request.ocr_text_2, request.ocr_text_3,
                    request.manual_text_1, request.manual_text_2, request.manual_text_3]):

                # Get book settings to find attribute IDs
                settings_result = db.execute(
                    text(f"""SELECT ocr_attr1_id, ocr_attr2_id, ocr_attr3_id,
                                    manual_attr1_id, manual_attr2_id, manual_attr3_id
                             FROM {table_prefix}_settings LIMIT 1""")
                ).first()

                if settings_result:
                    ocr_attr1_id, ocr_attr2_id, ocr_attr3_id, \
                    manual_attr1_id, manual_attr2_id, manual_attr3_id = settings_result

                    # Build dynamic UPDATE for additional texts
                    update_parts = []
                    update_params = {"ku_id": knowledge_unit_id}

                    # Map OCR texts to their attribute columns
                    if request.ocr_text_1 and ocr_attr1_id:
                        update_parts.append(f"attr{ocr_attr1_id}_value = :ocr_text_1")
                        update_params["ocr_text_1"] = request.ocr_text_1
                    if request.ocr_text_2 and ocr_attr2_id:
                        update_parts.append(f"attr{ocr_attr2_id}_value = :ocr_text_2")
                        update_params["ocr_text_2"] = request.ocr_text_2
                    if request.ocr_text_3 and ocr_attr3_id:
                        update_parts.append(f"attr{ocr_attr3_id}_value = :ocr_text_3")
                        update_params["ocr_text_3"] = request.ocr_text_3

                    # Map manual texts to their attribute columns
                    if request.manual_text_1 and manual_attr1_id:
                        update_parts.append(f"attr{manual_attr1_id}_value = :manual_text_1")
                        update_params["manual_text_1"] = request.manual_text_1
                    if request.manual_text_2 and manual_attr2_id:
                        update_parts.append(f"attr{manual_attr2_id}_value = :manual_text_2")
                        update_params["manual_text_2"] = request.manual_text_2
                    if request.manual_text_3 and manual_attr3_id:
                        update_parts.append(f"attr{manual_attr3_id}_value = :manual_text_3")
                        update_params["manual_text_3"] = request.manual_text_3

                    if update_parts:
                        update_ku_additional_sql = text(f"""
                            UPDATE {table_prefix}_knowledge_units
                            SET {', '.join(update_parts)}
                            WHERE unit_id = :ku_id
                        """)
                        db.execute(update_ku_additional_sql, update_params)
                        db.commit()
                        additional_texts_saved = True
                        logger.info(f"Saved {len(update_parts)} additional text fields to knowledge_unit {knowledge_unit_id}")

            return {
                "success": True,
                "clip_id": clip_id,
                "knowledge_unit_id": knowledge_unit_id,
                "ocr_engine": request.ocr_engine,
                "additional_texts_saved": additional_texts_saved,
                "message": f"Saved with {request.ocr_engine} OCR"
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save multi-OCR result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Sequential OCR Extraction Endpoints (Phase 4 Enhancement)
# ============================================================================

class RectangleCoordinates(BaseModel):
    """Rectangle coordinates for sequential OCR extraction"""
    x: int
    y: int
    width: int
    height: int


class ExtractSequentialRequest(BaseModel):
    """Request model for sequential OCR extraction from rectangles"""
    book_id: int
    page_number: int
    rectangles: List[RectangleCoordinates]  # Up to 3 rectangles


class ExtractSequentialResponse(BaseModel):
    """Response model for sequential OCR extraction"""
    success: bool
    ocr_results: List[dict]  # List of {text: str, confidence: float, index: int}
    message: str


@router.post("/ocr/extract-sequential", response_model=ExtractSequentialResponse)
async def extract_sequential_ocr(request: ExtractSequentialRequest):
    """
    Extract OCR text from up to 3 user-drawn rectangles sequentially.

    This endpoint is used in the Verify Pages UI (Phase 4 enhancement) to extract
    OCR text from diagram regions selected by the user. The extracted text is used
    to populate the 3 sequential OCR text areas.

    Process:
    1. Load the raw page image from database
    2. For each rectangle:
       - Crop the image to rectangle bounds
       - Run Surya OCR on the cropped region
       - Return extracted text and confidence
    3. Return all OCR results in order

    Args:
        request: Contains book_id, page_number, and list of rectangles

    Returns:
        ExtractSequentialResponse with OCR results for each rectangle
    """
    logger.info(f"Extracting sequential OCR for book_id={request.book_id}, page={request.page_number}, rectangles={len(request.rectangles)}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        from PIL import Image
        import io
        from src.services.ocr_sequential import run_surya_on_single_image

        # Validate rectangles count
        if len(request.rectangles) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 rectangles allowed")

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get raw page image
            page_query = text(f"""
                SELECT original_image_data
                FROM raw_{table_prefix}_pages
                WHERE page_number = :page_number
            """)
            page_result = db.execute(page_query, {"page_number": request.page_number}).first()

            if not page_result or not page_result[0]:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} image not found")

            page_image_bytes = bytes(page_result[0])

            # Load image
            page_image = Image.open(io.BytesIO(page_image_bytes))

            # Extract OCR for each rectangle
            ocr_results = []
            for idx, rect in enumerate(request.rectangles):
                logger.info(f"Processing rectangle {idx + 1}: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")

                # Crop image to rectangle
                cropped_image = page_image.crop((
                    rect.x,
                    rect.y,
                    rect.x + rect.width,
                    rect.y + rect.height
                ))

                # Convert to bytes
                buffer = io.BytesIO()
                cropped_image.save(buffer, format='PNG')
                cropped_bytes = buffer.getvalue()

                # Run Surya OCR
                ocr_result = run_surya_on_single_image(cropped_bytes)

                if ocr_result.get('success'):
                    ocr_results.append({
                        "index": idx + 1,
                        "text": ocr_result.get('text', ''),
                        "confidence": ocr_result.get('confidence', 0.0),
                        "rectangle": {
                            "x": rect.x,
                            "y": rect.y,
                            "width": rect.width,
                            "height": rect.height
                        }
                    })
                    logger.info(f"Rectangle {idx + 1}: Extracted {len(ocr_result.get('text', ''))} chars, confidence={ocr_result.get('confidence', 0.0):.2f}")
                else:
                    # OCR failed for this rectangle
                    error_msg = ocr_result.get('error', 'Unknown error')
                    logger.warning(f"Rectangle {idx + 1}: OCR failed - {error_msg}")
                    ocr_results.append({
                        "index": idx + 1,
                        "text": "",
                        "confidence": 0.0,
                        "rectangle": {
                            "x": rect.x,
                            "y": rect.y,
                            "width": rect.width,
                            "height": rect.height
                        },
                        "error": error_msg
                    })

            return ExtractSequentialResponse(
                success=True,
                ocr_results=ocr_results,
                message=f"Extracted OCR from {len(ocr_results)} rectangles"
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract sequential OCR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SaveSequentialTextsRequest(BaseModel):
    """Request model for saving sequential texts to diagram"""
    book_id: int
    diagram_id: int
    ocr_text_1: Optional[str] = None
    ocr_text_2: Optional[str] = None
    ocr_text_3: Optional[str] = None
    manual_text_1: Optional[str] = None
    manual_text_2: Optional[str] = None
    manual_text_3: Optional[str] = None


@router.post("/sequential-texts/save")
async def save_sequential_texts(request: SaveSequentialTextsRequest):
    """
    Save all 6 sequential texts (3 OCR + 3 manual) to diagram record.

    This endpoint is used in the Verify Pages UI (Phase 4 enhancement) to persist
    the extracted OCR texts and manually typed texts to the diagram_images table.

    The texts are stored in:
    - ocr_text_1, ocr_text_2, ocr_text_3: OCR-extracted texts from rectangles
    - manual_text_1, manual_text_2, manual_text_3: User-typed texts

    Args:
        request: Contains diagram_id and 6 text fields

    Returns:
        Success response with updated diagram_id
    """
    logger.info(f"Saving sequential texts for diagram {request.diagram_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Update diagram with all 6 texts
            update_sql = text(f"""
                UPDATE raw_{table_prefix}_diagram_images
                SET ocr_text_1 = :ocr_text_1,
                    ocr_text_2 = :ocr_text_2,
                    ocr_text_3 = :ocr_text_3,
                    manual_text_1 = :manual_text_1,
                    manual_text_2 = :manual_text_2,
                    manual_text_3 = :manual_text_3,
                    updated_at = NOW()
                WHERE id = :diagram_id
            """)

            result = db.execute(update_sql, {
                "ocr_text_1": request.ocr_text_1,
                "ocr_text_2": request.ocr_text_2,
                "ocr_text_3": request.ocr_text_3,
                "manual_text_1": request.manual_text_1,
                "manual_text_2": request.manual_text_2,
                "manual_text_3": request.manual_text_3,
                "diagram_id": request.diagram_id
            })

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Diagram not found")

            db.commit()

            return {
                "success": True,
                "message": "Sequential texts saved successfully",
                "diagram_id": request.diagram_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save sequential texts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Claude Diagram Analysis Endpoint
# ============================================================================

class ContextText(BaseModel):
    """Context text item"""
    type: str
    text: str


class ClaudeAnalysisRequest(BaseModel):
    """Request model for Claude diagram analysis"""
    book_id: int
    page_number: int
    image_data_base64: str
    prompt: str
    context_texts: Optional[List[ContextText]] = []
    model: Optional[str] = "sonnet"  # 'sonnet' or 'opus'
    diagram_type: Optional[str] = "diagram"  # 'diagram', 'equation', or 'table'


@router.post("/ocr/analyze-diagram-claude")
async def analyze_diagram_with_claude(request: ClaudeAnalysisRequest):
    """
    Analyze a diagram image using Claude Vision API.

    This endpoint:
    1. Takes the cropped diagram image
    2. Constructs a prompt with optional context texts
    3. Sends to Claude Vision API (Sonnet or Opus)
    4. Returns the analysis result

    The result is NOT saved to database - it's just returned for preview.
    The user can then save it when clicking "Save Diagram".
    """
    logger.info(f"Claude analysis request: book_id={request.book_id}, page={request.page_number}, model={request.model}, type={request.diagram_type}")

    try:
        import anthropic
        import base64
        from src.config import settings

        # Get API key from settings (loaded from .env)
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key or api_key == 'your-api-key-here':
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured. Please add your API key to .env file.")

        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)

        # Select model based on request
        model_id = "claude-sonnet-4-20250514" if request.model == "sonnet" else "claude-opus-4-20250514"

        # Extract base64 image data (remove data URL prefix if present)
        image_data = request.image_data_base64
        if image_data.startswith("data:"):
            # Extract just the base64 part
            image_data = image_data.split(",", 1)[1] if "," in image_data else image_data

        # Determine media type
        media_type = "image/png"
        if "data:image/jpeg" in request.image_data_base64:
            media_type = "image/jpeg"
        elif "data:image/webp" in request.image_data_base64:
            media_type = "image/webp"

        # Build the full prompt with context texts
        full_prompt = request.prompt

        if request.context_texts:
            context_section = "\n\n--- Additional Context ---\n"
            for ctx in request.context_texts:
                if ctx.text.strip():
                    context_section += f"\n{ctx.type}:\n{ctx.text}\n"
            full_prompt += context_section

        logger.info(f"Sending to Claude {request.model}: prompt length={len(full_prompt)}, context items={len(request.context_texts)}")

        # Call Claude Vision API
        message = client.messages.create(
            model=model_id,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": full_prompt
                        }
                    ]
                }
            ]
        )

        # Extract response text
        analysis_text = ""
        if message.content:
            for block in message.content:
                if hasattr(block, "text"):
                    analysis_text += block.text

        logger.info(f"Claude analysis complete: response length={len(analysis_text)}")

        return {
            "success": True,
            "analysis": analysis_text,
            "model": request.model,
            "diagram_type": request.diagram_type,
            "prompt_length": len(full_prompt),
            "context_items": len(request.context_texts)
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Diagram-Paragraph Linking Endpoints
# ============================================================================

class LinkDiagramToParagraphRequest(BaseModel):
    """Request model for linking a diagram to a paragraph"""
    book_id: int
    diagram_id: int
    paragraph_id: int
    slot: Optional[int] = None  # 1-5 for paragraph's child slot, auto-assign if None


class UnlinkDiagramFromParagraphRequest(BaseModel):
    """Request model for unlinking a diagram from a paragraph"""
    book_id: int
    diagram_id: int
    paragraph_id: int


@router.post("/diagrams/link-to-paragraph")
async def link_diagram_to_paragraph(request: LinkDiagramToParagraphRequest):
    """
    Link a diagram to a paragraph as a child.

    - Stores paragraph_id in diagram's attr17_value (parent reference)
    - Stores diagram_id in paragraph's attr17-21 (child references, slots 1-5)
    - If diagram already has a parent, requires confirmation (handled by frontend)
    - Auto-assigns to first available slot if slot not specified
    """
    logger.info(f"Linking diagram {request.diagram_id} to paragraph {request.paragraph_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Check if diagram exists
            diagram = db.execute(
                text(f"SELECT id, attr17_value FROM raw_{table_prefix}_diagram_images WHERE id = :diagram_id"),
                {"diagram_id": request.diagram_id}
            ).first()

            if not diagram:
                raise HTTPException(status_code=404, detail="Diagram not found")

            # Check if diagram already has a parent
            existing_parent = diagram[1]
            if existing_parent and str(existing_parent) != str(request.paragraph_id):
                return {
                    "success": False,
                    "needs_confirmation": True,
                    "existing_parent_id": existing_parent,
                    "message": f"Diagram already linked to paragraph {existing_parent}"
                }

            # Check if paragraph exists
            paragraph = db.execute(
                text(f"""SELECT unit_id, attr17_value, attr18_value, attr19_value, attr20_value, attr21_value
                         FROM {table_prefix}_knowledge_units WHERE unit_id = :paragraph_id"""),
                {"paragraph_id": request.paragraph_id}
            ).first()

            if not paragraph:
                raise HTTPException(status_code=404, detail="Paragraph not found")

            # Find available slot (attr17-21 map to slots 1-5)
            slots = [paragraph[1], paragraph[2], paragraph[3], paragraph[4], paragraph[5]]
            slot_to_use = request.slot

            if slot_to_use is None:
                # Auto-assign to first empty slot
                for i, slot_val in enumerate(slots):
                    if not slot_val:
                        slot_to_use = i + 1
                        break

                if slot_to_use is None:
                    raise HTTPException(status_code=400, detail="Paragraph already has 5 linked diagrams (maximum reached)")
            else:
                # Validate slot number
                if slot_to_use < 1 or slot_to_use > 5:
                    raise HTTPException(status_code=400, detail="Slot must be between 1 and 5")

                # Check if slot is already occupied by a different diagram
                current_slot_value = slots[slot_to_use - 1]
                if current_slot_value and str(current_slot_value) != str(request.diagram_id):
                    raise HTTPException(status_code=400, detail=f"Slot {slot_to_use} already contains diagram {current_slot_value}")

            # Map slot 1-5 to attr17-21
            slot_attr = f"attr{16 + slot_to_use}_value"

            # Update paragraph's child diagram slot
            db.execute(
                text(f"""UPDATE {table_prefix}_knowledge_units
                         SET {slot_attr} = :diagram_id, updated_at = NOW()
                         WHERE unit_id = :paragraph_id"""),
                {"diagram_id": str(request.diagram_id), "paragraph_id": request.paragraph_id}
            )

            # Update diagram's parent paragraph reference
            db.execute(
                text(f"""UPDATE raw_{table_prefix}_diagram_images
                         SET attr17_value = :paragraph_id, updated_at = NOW()
                         WHERE id = :diagram_id"""),
                {"paragraph_id": str(request.paragraph_id), "diagram_id": request.diagram_id}
            )

            db.commit()

            logger.info(f"Successfully linked diagram {request.diagram_id} to paragraph {request.paragraph_id} in slot {slot_to_use}")

            return {
                "success": True,
                "message": f"Diagram linked to paragraph in slot {slot_to_use}",
                "diagram_id": request.diagram_id,
                "paragraph_id": request.paragraph_id,
                "slot": slot_to_use
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to link diagram to paragraph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagrams/unlink-from-paragraph")
async def unlink_diagram_from_paragraph(request: UnlinkDiagramFromParagraphRequest):
    """
    Unlink a diagram from a paragraph (bidirectional).

    - Clears paragraph_id from diagram's attr17_value
    - Clears diagram_id from paragraph's attr17-21
    """
    logger.info(f"Unlinking diagram {request.diagram_id} from paragraph {request.paragraph_id} in book {request.book_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Clear diagram's parent reference
            db.execute(
                text(f"""UPDATE raw_{table_prefix}_diagram_images
                         SET attr17_value = NULL, updated_at = NOW()
                         WHERE id = :diagram_id"""),
                {"diagram_id": request.diagram_id}
            )

            # Find and clear paragraph's child slot that contains this diagram
            for slot in range(1, 6):
                slot_attr = f"attr{16 + slot}_value"
                db.execute(
                    text(f"""UPDATE {table_prefix}_knowledge_units
                             SET {slot_attr} = NULL, updated_at = NOW()
                             WHERE unit_id = :paragraph_id AND {slot_attr} = :diagram_id"""),
                    {"paragraph_id": request.paragraph_id, "diagram_id": str(request.diagram_id)}
                )

            db.commit()

            logger.info(f"Successfully unlinked diagram {request.diagram_id} from paragraph {request.paragraph_id}")

            return {
                "success": True,
                "message": "Diagram unlinked from paragraph",
                "diagram_id": request.diagram_id,
                "paragraph_id": request.paragraph_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlink diagram from paragraph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagrams/{book_id}/recent-paragraphs")
async def get_recent_paragraphs_for_linking(book_id: int, limit: int = 5):
    """
    Get the most recent paragraphs for linking to a diagram.
    Returns paragraph thumbnails and basic info.
    """
    logger.info(f"Getting recent paragraphs for book {book_id}, limit={limit}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        import base64

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get recent paragraphs (knowledge units that have paragraph images)
            # Join with paragraph_images to only get actual paragraphs (not diagrams)
            paragraphs = db.execute(
                text(f"""SELECT ku.unit_id, ku.page_number, ku.text_content,
                                ku.attr17_value, ku.attr18_value, ku.attr19_value, ku.attr20_value, ku.attr21_value,
                                pi.image_data
                         FROM {table_prefix}_knowledge_units ku
                         INNER JOIN raw_{table_prefix}_paragraph_images pi ON pi.knowledge_unit_id = ku.unit_id
                         ORDER BY ku.created_at DESC
                         LIMIT :limit"""),
                {"limit": limit}
            ).fetchall()

            result_list = []
            for p in paragraphs:
                # Count linked diagrams
                linked_count = sum(1 for i in range(3, 8) if p[i])

                # Get thumbnail (small version of image)
                thumbnail_b64 = None
                if p[8]:  # image_data
                    thumbnail_b64 = base64.b64encode(p[8]).decode('utf-8')

                result_list.append({
                    "paragraph_id": p[0],
                    "page_number": p[1],
                    "text_preview": (p[2] or "")[:100] + ("..." if len(p[2] or "") > 100 else ""),
                    "linked_diagrams_count": linked_count,
                    "thumbnail_base64": thumbnail_b64
                })

            return {
                "success": True,
                "paragraphs": result_list
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent paragraphs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paragraphs/{book_id}/recent-diagrams")
async def get_recent_diagrams_for_linking(book_id: int, limit: int = 5):
    """
    Get the most recent diagrams for linking to a paragraph.
    Returns diagram thumbnails and basic info.
    """
    logger.info(f"Getting recent diagrams for book {book_id}, limit={limit}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text
        import base64

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get recent diagrams
            diagrams = db.execute(
                text(f"""SELECT id, page_number, description, attr17_value, image_data
                         FROM raw_{table_prefix}_diagram_images
                         ORDER BY created_at DESC
                         LIMIT :limit"""),
                {"limit": limit}
            ).fetchall()

            result_list = []
            for d in diagrams:
                # Get thumbnail
                thumbnail_b64 = None
                if d[4]:  # image_data
                    thumbnail_b64 = base64.b64encode(d[4]).decode('utf-8')

                result_list.append({
                    "diagram_id": d[0],
                    "page_number": d[1],
                    "description_preview": (d[2] or "")[:100] + ("..." if len(d[2] or "") > 100 else ""),
                    "parent_paragraph_id": d[3],
                    "thumbnail_base64": thumbnail_b64
                })

            return {
                "success": True,
                "diagrams": result_list
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent diagrams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagrams/link-to-paragraph-force")
async def link_diagram_to_paragraph_force(request: LinkDiagramToParagraphRequest):
    """
    Force link a diagram to a paragraph, replacing any existing parent link.
    Used after user confirms they want to replace existing link.
    """
    logger.info(f"Force linking diagram {request.diagram_id} to paragraph {request.paragraph_id}")

    try:
        from src.database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # Get book metadata
            result = db.execute(
                text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
                {"book_id": request.book_id}
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail="Book not found")

            table_prefix = result[0]

            # Get diagram's current parent
            diagram = db.execute(
                text(f"SELECT id, attr17_value FROM raw_{table_prefix}_diagram_images WHERE id = :diagram_id"),
                {"diagram_id": request.diagram_id}
            ).first()

            if not diagram:
                raise HTTPException(status_code=404, detail="Diagram not found")

            old_parent_id = diagram[1]

            # If there's an old parent, clear the reference from it
            if old_parent_id:
                for slot in range(1, 6):
                    slot_attr = f"attr{16 + slot}_value"
                    db.execute(
                        text(f"""UPDATE {table_prefix}_knowledge_units
                                 SET {slot_attr} = NULL, updated_at = NOW()
                                 WHERE unit_id = :old_parent_id AND {slot_attr} = :diagram_id"""),
                        {"old_parent_id": old_parent_id, "diagram_id": str(request.diagram_id)}
                    )

            # Now link to new parent - find first available slot
            paragraph = db.execute(
                text(f"""SELECT unit_id, attr17_value, attr18_value, attr19_value, attr20_value, attr21_value
                         FROM {table_prefix}_knowledge_units WHERE unit_id = :paragraph_id"""),
                {"paragraph_id": request.paragraph_id}
            ).first()

            if not paragraph:
                raise HTTPException(status_code=404, detail="Paragraph not found")

            slots = [paragraph[1], paragraph[2], paragraph[3], paragraph[4], paragraph[5]]
            slot_to_use = request.slot

            if slot_to_use is None:
                for i, slot_val in enumerate(slots):
                    if not slot_val:
                        slot_to_use = i + 1
                        break

                if slot_to_use is None:
                    raise HTTPException(status_code=400, detail="Paragraph already has 5 linked diagrams")

            slot_attr = f"attr{16 + slot_to_use}_value"

            # Update paragraph's child diagram slot
            db.execute(
                text(f"""UPDATE {table_prefix}_knowledge_units
                         SET {slot_attr} = :diagram_id, updated_at = NOW()
                         WHERE unit_id = :paragraph_id"""),
                {"diagram_id": str(request.diagram_id), "paragraph_id": request.paragraph_id}
            )

            # Update diagram's parent paragraph reference
            db.execute(
                text(f"""UPDATE raw_{table_prefix}_diagram_images
                         SET attr17_value = :paragraph_id, updated_at = NOW()
                         WHERE id = :diagram_id"""),
                {"paragraph_id": str(request.paragraph_id), "diagram_id": request.diagram_id}
            )

            db.commit()

            return {
                "success": True,
                "message": f"Diagram linked to paragraph in slot {slot_to_use}",
                "diagram_id": request.diagram_id,
                "paragraph_id": request.paragraph_id,
                "slot": slot_to_use,
                "old_parent_id": old_parent_id
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force link diagram to paragraph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ExtractRegionRequest(BaseModel):
    """Request for extracting text from a page region."""
    book_id: int
    page_number: int
    x: int
    y: int
    width: int
    height: int


@router.post("/ocr/extract-region")
async def extract_region_text(request: ExtractRegionRequest):
    """
    Extract text from a specific region of a page using Surya OCR.

    This endpoint is used by the Auto-slicer page viewer to extract
    text from selected regions for title configuration.

    Args:
        book_id: Book ID
        page_number: Page number (1-indexed)
        x, y, width, height: Region coordinates in image pixels

    Returns:
        dict: {'text': str, 'confidence': float, 'success': bool}
    """
    from src.services.auto_slicer_service import (
        get_book_info, crop_image, run_surya_ocr
    )
    from src.database.connection import SessionLocal
    from sqlalchemy import text

    try:
        # Get book info
        book_info = get_book_info(request.book_id)
        if not book_info:
            raise HTTPException(status_code=404, detail="Book not found")

        table_prefix = book_info["table_prefix"]

        # Get page image from raw_pages table
        db = SessionLocal()
        try:
            result = db.execute(
                text(f"SELECT original_image_data FROM raw_{table_prefix}_pages WHERE page_number = :page_num"),
                {"page_num": request.page_number}
            ).first()

            if not result or not result[0]:
                raise HTTPException(status_code=404, detail=f"Page {request.page_number} image not found")

            image_data = bytes(result[0])

        finally:
            db.close()

        # Crop the image to the specified region
        cropped = crop_image(image_data, request.x, request.y, request.width, request.height)
        if not cropped:
            raise HTTPException(status_code=500, detail="Failed to crop image region")

        # Run Surya OCR on cropped region
        ocr_result = run_surya_ocr(cropped)

        if ocr_result.get('success'):
            return {
                "success": True,
                "text": ocr_result.get('text', ''),
                "confidence": ocr_result.get('confidence', 0.0)
            }
        else:
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "error": ocr_result.get('error', 'OCR failed')
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract text from region: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
