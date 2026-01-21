"""
GPU Management API Routes

Provides endpoints for:
- GPU status and VRAM usage
- Model loading/unloading for OCR models
"""

from fastapi import APIRouter, HTTPException
from src.utils.logging_config import logger

router = APIRouter()

# Track loaded models globally
_loaded_models = set()

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def get_gpu_info():
    """Get GPU status information."""
    if not TORCH_AVAILABLE:
        return {
            "gpu_available": False,
            "vram_used_mb": 0,
            "vram_total_mb": 0,
            "vram_free_mb": 0,
            "device_name": "PyTorch not available"
        }

    if not torch.cuda.is_available():
        return {
            "gpu_available": False,
            "vram_used_mb": 0,
            "vram_total_mb": 0,
            "vram_free_mb": 0,
            "device_name": "No GPU"
        }

    try:
        free_memory, total_memory = torch.cuda.mem_get_info()
        used_memory = total_memory - free_memory

        return {
            "gpu_available": True,
            "vram_used_mb": used_memory / 1024 / 1024,
            "vram_total_mb": total_memory / 1024 / 1024,
            "vram_free_mb": free_memory / 1024 / 1024,
            "device_name": torch.cuda.get_device_name(0)
        }
    except Exception as e:
        logger.error(f"Error getting GPU info: {e}")
        return {
            "gpu_available": True,
            "vram_used_mb": 0,
            "vram_total_mb": 0,
            "vram_free_mb": 0,
            "device_name": "Error getting info"
        }


@router.get("/gpu/status")
async def get_gpu_status():
    """Get GPU status including VRAM usage and loaded models."""
    info = get_gpu_info()

    # Check which models are actually loaded by checking services
    loaded_models = list(_loaded_models)

    # Check Surya status from ocr_sequential service
    try:
        from src.services.ocr_sequential import check_surya_models_status
        surya_status = check_surya_models_status()
        if surya_status.get('loaded') and 'surya' not in loaded_models:
            loaded_models.append('surya')
    except Exception:
        pass

    # Also check layout detection service for YOLO
    try:
        from src.services.layout_detection_service import layout_service
        if layout_service and layout_service.model is not None:
            if 'yolo' not in loaded_models and 'DocLayout-YOLO' not in loaded_models:
                loaded_models.append('DocLayout-YOLO')
    except Exception:
        pass

    return {
        **info,
        "loaded_models": loaded_models
    }


@router.post("/gpu/load/{model}")
async def load_model(model: str):
    """Load a model to GPU."""
    global _loaded_models

    model = model.lower()

    if model == "surya":
        try:
            from src.services.ocr_sequential import load_surya_models

            result = load_surya_models()

            if result.get('success'):
                _loaded_models.add('surya')
                return {"status": "ok", "message": result.get('message', 'Surya loaded to GPU')}
            else:
                raise HTTPException(status_code=500, detail=result.get('message', 'Failed to load Surya'))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading Surya: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load Surya: {str(e)}")

    elif model == "easyocr":
        try:
            import easyocr

            logger.info("Loading EasyOCR to GPU...")
            _easyocr_reader = easyocr.Reader(['ar', 'en'], gpu=True)

            _loaded_models.add('easyocr')
            logger.info("EasyOCR loaded successfully")

            return {"status": "ok", "message": "EasyOCR loaded to GPU"}

        except Exception as e:
            logger.error(f"Error loading EasyOCR: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load EasyOCR: {str(e)}")

    elif model == "yolo":
        try:
            from src.services.layout_detection_service import layout_service

            logger.info("Loading DocLayout-YOLO to GPU...")
            success = layout_service.load_model()

            if success:
                _loaded_models.add('yolo')
                return {"status": "ok", "message": "DocLayout-YOLO loaded to GPU"}
            else:
                raise HTTPException(status_code=500, detail="Failed to load YOLO model")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading YOLO: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load YOLO: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")


@router.post("/gpu/unload/{model}")
async def unload_model(model: str):
    """Unload a model from GPU."""
    global _loaded_models

    model = model.lower()

    if model == "surya":
        try:
            from src.services.ocr_sequential import unload_surya_models

            result = unload_surya_models()

            _loaded_models.discard('surya')
            return {"status": "ok", "message": result.get('message', 'Surya unloaded')}

        except Exception as e:
            logger.error(f"Error unloading Surya: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unload Surya: {str(e)}")

    elif model == "easyocr":
        try:
            import gc
            if TORCH_AVAILABLE:
                torch.cuda.empty_cache()
            gc.collect()

            _loaded_models.discard('easyocr')
            logger.info("EasyOCR unloaded (cache cleared)")

            return {"status": "ok", "message": "EasyOCR unloaded"}

        except Exception as e:
            logger.error(f"Error unloading EasyOCR: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unload EasyOCR: {str(e)}")

    elif model == "yolo":
        try:
            from src.services.layout_detection_service import layout_service

            logger.info("Unloading DocLayout-YOLO from GPU...")
            layout_service.unload_model()

            _loaded_models.discard('yolo')
            return {"status": "ok", "message": "DocLayout-YOLO unloaded"}

        except Exception as e:
            logger.error(f"Error unloading YOLO: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unload YOLO: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
