"""
GPU Memory Management Service

Manages GPU memory for sequential OCR model loading/unloading.
Ensures safe model transitions and prevents OOM errors.

Aligned with sequential-ocr-svg-processing.md architecture.
"""

import gc
from typing import Optional
from src.utils.logging_config import logger

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - GPU management disabled")


class GPUMemoryManager:
    """Manage GPU memory for sequential OCR model loading"""

    @staticmethod
    def get_available_gpu_memory() -> int:
        """
        Returns available GPU memory in MB.

        Returns:
            int: Available memory in MB, or 0 if no GPU available
        """
        if not TORCH_AVAILABLE:
            return 0

        if torch.cuda.is_available():
            try:
                free_memory, total_memory = torch.cuda.mem_get_info()
                return int(free_memory / 1024 / 1024)  # Convert to MB
            except Exception as e:
                logger.error(f"Failed to get GPU memory info: {e}")
                return 0
        return 0

    @staticmethod
    def unload_model_safely(model: Optional[object], model_name: str = "Model"):
        """
        Safely unload model and clear GPU cache.

        Args:
            model: Model object to unload (can be None)
            model_name: Name of model for logging

        Returns:
            None
        """
        if model is None:
            logger.info(f"{model_name} is None, nothing to unload")
            return

        logger.info(f"Unloading {model_name} from GPU...")

        # Delete model
        del model
        gc.collect()

        # Clear GPU cache if available
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        available_after = GPUMemoryManager.get_available_gpu_memory()
        logger.info(f"{model_name} unloaded. Available GPU memory: {available_after:.0f} MB")

    @staticmethod
    def check_sufficient_memory(required_mb: int, model_name: str) -> bool:
        """
        Check if sufficient GPU memory available.

        Args:
            required_mb: Required memory in MB
            model_name: Name of model for logging

        Returns:
            bool: True if sufficient memory available
        """
        if not TORCH_AVAILABLE:
            logger.warning(f"PyTorch not available - cannot check memory for {model_name}")
            return False

        available = GPUMemoryManager.get_available_gpu_memory()

        if available < required_mb:
            logger.error(
                f"Insufficient GPU memory for {model_name}. "
                f"Required: {required_mb} MB, Available: {available:.0f} MB"
            )
            return False

        logger.info(
            f"Sufficient GPU memory for {model_name}. "
            f"Required: {required_mb} MB, Available: {available:.0f} MB"
        )
        return True

    @staticmethod
    def log_gpu_usage():
        """Log current GPU memory usage."""
        if not TORCH_AVAILABLE:
            return

        if torch.cuda.is_available():
            try:
                allocated = torch.cuda.memory_allocated() / 1024 / 1024
                reserved = torch.cuda.memory_reserved() / 1024 / 1024
                available = GPUMemoryManager.get_available_gpu_memory()

                logger.info(
                    f"GPU Memory - Allocated: {allocated:.0f} MB, "
                    f"Reserved: {reserved:.0f} MB, Available: {available:.0f} MB"
                )
            except Exception as e:
                logger.error(f"Failed to log GPU usage: {e}")

    @staticmethod
    def is_gpu_available() -> bool:
        """
        Check if GPU is available for processing.

        Returns:
            bool: True if GPU available
        """
        if not TORCH_AVAILABLE:
            return False

        return torch.cuda.is_available()

    @staticmethod
    def get_gpu_device_name() -> str:
        """
        Get GPU device name.

        Returns:
            str: GPU device name or "No GPU" if unavailable
        """
        if not TORCH_AVAILABLE:
            return "PyTorch not available"

        if torch.cuda.is_available():
            try:
                return torch.cuda.get_device_name(0)
            except Exception:
                return "GPU available (name unknown)"

        return "No GPU"


# Singleton instance
gpu_manager = GPUMemoryManager()
