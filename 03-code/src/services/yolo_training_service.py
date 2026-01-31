"""
YOLO Training Service

Service for fine-tuning DocLayout-YOLO with user corrections.
Implements Requirement 7C: YOLO Fine-Tuning.

Features:
- Export training data in YOLO format
- Get training statistics
- Backup current model
- Start training process
- Track training progress
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from datetime import datetime
from pathlib import Path
import json
import shutil
import os
import logging

from src.database.connection import engine

logger = logging.getLogger(__name__)

# YOLO class mapping (from layout_detection_service)
YOLO_CLASS_MAPPING = {
    "title_level_1": 0,
    "title_level_2": 1,
    "title_level_3": 2,
    "paragraph": 3,
    "diagram": 4,
    "table": 5,
    "equation": 6,
    "list_bulleted": 7,
    "list_numbered": 8,
    "list_lettered": 9,
    "question": 10,
    "answer": 11,
    "page_header": 12,
    "page_footer": 13,
    "page_number": 14,
    "caption": 15,
    "footnote": 16,
    "sidebar": 17,
    "code_block": 18,
    "quote": 19
}


class YOLOTrainingService:
    """Service for YOLO model fine-tuning with user corrections."""
    
    def __init__(self, book_id: int, table_prefix: str):
        self.book_id = book_id
        self.table_prefix = table_prefix
        self.detections_table = f"raw_{table_prefix}_layout_detections"
        self.pages_table = f"raw_{table_prefix}_pages"
        
        # Paths
        self.base_path = Path("models")
        self.training_data_path = self.base_path / "training_data" / f"book_{book_id}"
        self.backups_path = self.base_path / "backups"
        self.model_path = self.base_path / "layout_detection"
    
    def get_correction_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about user corrections for this book.
        
        Returns:
            Dict with correction counts, class distribution, etc.
        """
        sql = text(f"""
            SELECT 
                COUNT(*) as total_regions,
                COUNT(*) FILTER (WHERE was_corrected = TRUE) as corrected_regions,
                COUNT(*) FILTER (WHERE correction_type = 'manual_adjustment') as adjusted_regions,
                COUNT(*) FILTER (WHERE correction_type = 'manually_added') as added_regions,
                COUNT(DISTINCT page_number) as total_pages,
                COUNT(DISTINCT page_number) FILTER (WHERE was_corrected = TRUE) as pages_with_corrections
            FROM {self.detections_table}
            WHERE review_status IN ('reviewed', 'finalized')
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql).fetchone()
            
            stats = {
                "total_regions": result[0] or 0,
                "corrected_regions": result[1] or 0,
                "adjusted_regions": result[2] or 0,
                "added_regions": result[3] or 0,
                "total_pages": result[4] or 0,
                "pages_with_corrections": result[5] or 0
            }
        
        # Get class distribution
        class_sql = text(f"""
            SELECT class_name, COUNT(*) as count
            FROM {self.detections_table}
            WHERE review_status IN ('reviewed', 'finalized')
            GROUP BY class_name
            ORDER BY count DESC
        """)
        
        with engine.connect() as conn:
            class_results = conn.execute(class_sql).fetchall()
            stats["class_distribution"] = {row[0]: row[1] for row in class_results}
        
        # Get correction type distribution
        correction_sql = text(f"""
            SELECT 
                COALESCE(original_class, 'N/A') as from_class,
                class_name as to_class,
                COUNT(*) as count
            FROM {self.detections_table}
            WHERE was_corrected = TRUE
            AND original_class IS NOT NULL
            AND original_class != class_name
            GROUP BY original_class, class_name
            ORDER BY count DESC
            LIMIT 20
        """)
        
        with engine.connect() as conn:
            correction_results = conn.execute(correction_sql).fetchall()
            stats["class_corrections"] = [
                {"from": row[0], "to": row[1], "count": row[2]}
                for row in correction_results
            ]
        
        # Calculate training readiness
        min_recommended = 20
        stats["training_ready"] = stats["pages_with_corrections"] >= min_recommended
        stats["min_recommended_pages"] = min_recommended
        
        if stats["pages_with_corrections"] < min_recommended:
            stats["warning"] = f"Only {stats['pages_with_corrections']} pages with corrections. Recommend at least {min_recommended} for good results."
        
        return stats

    def export_training_data(self, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export training data in YOLO format.
        
        Creates:
        - images/ folder with page images
        - labels/ folder with YOLO format annotations
        - data.yaml configuration file
        
        Returns:
            Dict with export statistics
        """
        if output_dir is None:
            output_dir = self.training_data_path
        
        output_dir = Path(output_dir)
        images_dir = output_dir / "images"
        labels_dir = output_dir / "labels"
        
        # Create directories
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all reviewed/finalized pages with their regions
        pages_sql = text(f"""
            SELECT DISTINCT page_number
            FROM {self.detections_table}
            WHERE review_status IN ('reviewed', 'finalized')
            ORDER BY page_number
        """)
        
        with engine.connect() as conn:
            pages = [row[0] for row in conn.execute(pages_sql).fetchall()]
        
        if not pages:
            return {
                "success": False,
                "error": "No reviewed pages found",
                "pages_exported": 0
            }
        
        exported_pages = 0
        exported_regions = 0
        skipped_classes = set()
        
        for page_num in pages:
            # Get page image
            image_sql = text(f"""
                SELECT original_image_data, original_format
                FROM {self.pages_table}
                WHERE page_number = :page_num
            """)
            
            with engine.connect() as conn:
                image_row = conn.execute(image_sql, {"page_num": page_num}).fetchone()
            
            if not image_row or not image_row[0]:
                logger.warning(f"No image data for page {page_num}")
                continue
            
            image_data = image_row[0]
            image_format = image_row[1] or "png"
            
            # Save image
            image_filename = f"page_{page_num:04d}.{image_format}"
            image_path = images_dir / image_filename
            
            with open(image_path, "wb") as f:
                f.write(image_data)
            
            # Get image dimensions
            try:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(image_data))
                img_width, img_height = img.size
            except Exception as e:
                logger.error(f"Error getting image dimensions for page {page_num}: {e}")
                continue
            
            # Get regions for this page
            regions_sql = text(f"""
                SELECT class_name, x, y, width, height
                FROM {self.detections_table}
                WHERE page_number = :page_num
                AND review_status IN ('reviewed', 'finalized')
                AND class_name != 'ignore'
            """)
            
            with engine.connect() as conn:
                regions = conn.execute(regions_sql, {"page_num": page_num}).fetchall()
            
            # Convert to YOLO format and save labels
            label_filename = f"page_{page_num:04d}.txt"
            label_path = labels_dir / label_filename
            
            with open(label_path, "w") as f:
                for region in regions:
                    class_name = region[0]
                    x, y, w, h = region[1], region[2], region[3], region[4]
                    
                    # Get class ID
                    class_id = YOLO_CLASS_MAPPING.get(class_name)
                    if class_id is None:
                        skipped_classes.add(class_name)
                        continue
                    
                    # Convert to YOLO format (normalized center x, center y, width, height)
                    center_x = (x + w / 2) / img_width
                    center_y = (y + h / 2) / img_height
                    norm_w = w / img_width
                    norm_h = h / img_height
                    
                    # Clamp values to [0, 1]
                    center_x = max(0, min(1, center_x))
                    center_y = max(0, min(1, center_y))
                    norm_w = max(0, min(1, norm_w))
                    norm_h = max(0, min(1, norm_h))
                    
                    f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {norm_w:.6f} {norm_h:.6f}\n")
                    exported_regions += 1
            
            exported_pages += 1
        
        # Create data.yaml
        data_yaml = {
            "path": str(output_dir.absolute()),
            "train": "images",
            "val": "images",  # Using same for now, can split later
            "names": {v: k for k, v in YOLO_CLASS_MAPPING.items()}
        }
        
        yaml_path = output_dir / "data.yaml"
        with open(yaml_path, "w") as f:
            import yaml
            yaml.dump(data_yaml, f, default_flow_style=False)
        
        result = {
            "success": True,
            "output_dir": str(output_dir),
            "pages_exported": exported_pages,
            "regions_exported": exported_regions,
            "skipped_classes": list(skipped_classes),
            "data_yaml_path": str(yaml_path)
        }
        
        logger.info(f"Exported training data: {exported_pages} pages, {exported_regions} regions")
        
        return result

    def backup_current_model(self) -> Dict[str, Any]:
        """
        Backup the current YOLO model before training.
        
        Creates a timestamped backup in models/backups/
        
        Returns:
            Dict with backup path and status
        """
        self.backups_path.mkdir(parents=True, exist_ok=True)
        
        # Find current model
        model_file = None
        for ext in [".pt", ".onnx"]:
            potential_path = self.model_path / f"doclayout_yolo{ext}"
            if potential_path.exists():
                model_file = potential_path
                break
        
        if not model_file:
            # Check for any .pt files in the model directory
            pt_files = list(self.model_path.glob("*.pt"))
            if pt_files:
                model_file = pt_files[0]
        
        if not model_file or not model_file.exists():
            return {
                "success": False,
                "error": "No model file found to backup",
                "searched_path": str(self.model_path)
            }
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"doclayout_yolo_backup_{timestamp}{model_file.suffix}"
        backup_path = self.backups_path / backup_name
        
        try:
            shutil.copy2(model_file, backup_path)
            
            # Also save metadata
            metadata = {
                "original_path": str(model_file),
                "backup_time": datetime.now().isoformat(),
                "book_id": self.book_id,
                "file_size": model_file.stat().st_size
            }
            
            metadata_path = self.backups_path / f"doclayout_yolo_backup_{timestamp}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Model backed up to {backup_path}")
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "metadata_path": str(metadata_path),
                "original_path": str(model_file),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error backing up model: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available model backups."""
        if not self.backups_path.exists():
            return []
        
        backups = []
        for json_file in sorted(self.backups_path.glob("*.json"), reverse=True):
            try:
                with open(json_file) as f:
                    metadata = json.load(f)
                
                # Check if corresponding model file exists
                model_name = json_file.stem.replace(".json", "") + ".pt"
                model_path = self.backups_path / model_name
                
                backups.append({
                    "metadata_file": json_file.name,
                    "model_exists": model_path.exists(),
                    **metadata
                })
            except Exception as e:
                logger.warning(f"Error reading backup metadata {json_file}: {e}")
        
        return backups

    def start_training(
        self,
        epochs: int = 50,
        batch_size: int = 8,
        learning_rate: float = 0.001,
        auto_backup: bool = True,
        background: bool = True
    ) -> Dict[str, Any]:
        """
        Start YOLO fine-tuning training.
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate
            auto_backup: Whether to backup model before training
            background: Whether to run in background
        
        Returns:
            Dict with training job info
        """
        # Auto-backup if requested
        if auto_backup:
            backup_result = self.backup_current_model()
            if not backup_result.get("success"):
                logger.warning(f"Model backup failed: {backup_result.get('error')}")
        
        # Export training data
        export_result = self.export_training_data()
        if not export_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to export training data: {export_result.get('error')}"
            }
        
        # Create training job record
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = self.training_data_path / "runs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save training config
        training_config = {
            "job_id": job_id,
            "book_id": self.book_id,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "data_yaml": export_result.get("data_yaml_path"),
            "started_at": datetime.now().isoformat(),
            "status": "pending",
            "background": background
        }
        
        config_path = job_dir / "training_config.json"
        with open(config_path, "w") as f:
            json.dump(training_config, f, indent=2)
        
        if background:
            # For background training, we'd typically use subprocess or a task queue
            # For now, return the job info and let the caller handle execution
            return {
                "success": True,
                "job_id": job_id,
                "job_dir": str(job_dir),
                "config_path": str(config_path),
                "status": "pending",
                "message": "Training job created. Run training script manually or via task queue.",
                "training_command": self._get_training_command(training_config)
            }
        else:
            # Synchronous training (blocking)
            return self._run_training(training_config, job_dir)
    
    def _get_training_command(self, config: Dict[str, Any]) -> str:
        """Generate the training command for manual execution."""
        data_yaml = config.get("data_yaml")
        epochs = config.get("epochs", 50)
        batch_size = config.get("batch_size", 8)
        lr = config.get("learning_rate", 0.001)
        
        # Using ultralytics YOLO training command
        cmd = f"""python -c "
from ultralytics import YOLO
model = YOLO('models/layout_detection/doclayout_yolo.pt')
model.train(
    data='{data_yaml}',
    epochs={epochs},
    batch={batch_size},
    lr0={lr},
    project='models/training_data/book_{self.book_id}/runs',
    name='{config.get("job_id")}',
    exist_ok=True
)
"
"""
        return cmd.strip()
    
    def _run_training(self, config: Dict[str, Any], job_dir: Path) -> Dict[str, Any]:
        """Run training synchronously (blocking)."""
        try:
            from ultralytics import YOLO
            
            # Update status
            config["status"] = "running"
            with open(job_dir / "training_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            # Load model
            model_path = self.model_path / "doclayout_yolo.pt"
            if not model_path.exists():
                return {"success": False, "error": "Model file not found"}
            
            model = YOLO(str(model_path))
            
            # Run training
            results = model.train(
                data=config.get("data_yaml"),
                epochs=config.get("epochs", 50),
                batch=config.get("batch_size", 8),
                lr0=config.get("learning_rate", 0.001),
                project=str(job_dir.parent),
                name=config.get("job_id"),
                exist_ok=True
            )
            
            # Copy best.pt to book-specific location
            best_model_path = job_dir / "weights" / "best.pt"
            book_model_path = self.model_path / f"book_{self.book_id}_yolo.pt"
            
            if best_model_path.exists():
                shutil.copy2(best_model_path, book_model_path)
                logger.info(f"Copied best model to {book_model_path}")
                config["book_model_path"] = str(book_model_path)
            
            # Update status
            config["status"] = "completed"
            config["completed_at"] = datetime.now().isoformat()
            with open(job_dir / "training_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            return {
                "success": True,
                "job_id": config.get("job_id"),
                "status": "completed",
                "results_dir": str(job_dir),
                "book_model_path": str(book_model_path) if best_model_path.exists() else None
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "ultralytics package not installed. Install with: pip install ultralytics"
            }
        except Exception as e:
            logger.error(f"Training error: {e}")
            config["status"] = "failed"
            config["error"] = str(e)
            with open(job_dir / "training_config.json", "w") as f:
                json.dump(config, f, indent=2)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_training_progress(self, job_id: str) -> Dict[str, Any]:
        """
        Get progress of a training job.
        
        Args:
            job_id: The training job ID
        
        Returns:
            Dict with training progress info
        """
        job_dir = self.training_data_path / "runs" / job_id
        config_path = job_dir / "training_config.json"
        
        if not config_path.exists():
            return {
                "success": False,
                "error": f"Training job {job_id} not found"
            }
        
        with open(config_path) as f:
            config = json.load(f)
        
        # Check for results
        results_csv = job_dir / "results.csv"
        if results_csv.exists():
            # Parse training progress from results.csv
            try:
                import csv
                with open(results_csv) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                
                if rows:
                    last_row = rows[-1]
                    config["current_epoch"] = len(rows)
                    config["metrics"] = {
                        "box_loss": float(last_row.get("train/box_loss", 0)),
                        "cls_loss": float(last_row.get("train/cls_loss", 0)),
                        "mAP50": float(last_row.get("metrics/mAP50(B)", 0)),
                        "mAP50-95": float(last_row.get("metrics/mAP50-95(B)", 0))
                    }
            except Exception as e:
                logger.warning(f"Error parsing results.csv: {e}")
        
        # Check for best model
        best_model = job_dir / "weights" / "best.pt"
        config["best_model_exists"] = best_model.exists()
        if best_model.exists():
            config["best_model_path"] = str(best_model)
        
        return {
            "success": True,
            "job_id": job_id,
            **config
        }
    
    def list_training_jobs(self) -> List[Dict[str, Any]]:
        """List all training jobs for this book."""
        runs_dir = self.training_data_path / "runs"
        if not runs_dir.exists():
            return []
        
        jobs = []
        for job_dir in sorted(runs_dir.iterdir(), reverse=True):
            if job_dir.is_dir():
                config_path = job_dir / "training_config.json"
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            config = json.load(f)
                        jobs.append(config)
                    except Exception as e:
                        logger.warning(f"Error reading job config {config_path}: {e}")
        
        return jobs


    def set_book_model_path(self, model_path: Optional[str]) -> bool:
        """
        Update the book's yolo_model_path in the database.
        
        Args:
            model_path: Path to the model file, or None to use global model
            
        Returns:
            True if successful
        """
        sql = text("""
            UPDATE books_metadata 
            SET yolo_model_path = :model_path
            WHERE book_id = :book_id
        """)
        
        with engine.connect() as conn:
            conn.execute(sql, {"book_id": self.book_id, "model_path": model_path})
            conn.commit()
            logger.info(f"Updated yolo_model_path for book {self.book_id}: {model_path}")
            return True
    
    def get_book_model_info(self) -> Dict[str, Any]:
        """
        Get YOLO model info for this book.
        
        Returns:
            Dict with model type, path, existence, size, etc.
        """
        sql = text("""
            SELECT yolo_model_path
            FROM books_metadata
            WHERE book_id = :book_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql, {"book_id": self.book_id}).fetchone()
            
            if not result:
                return {"error": f"Book {self.book_id} not found"}
            
            model_path = result[0]
        
        # Check if book has a specific model
        if model_path:
            path = Path(model_path)
            model_exists = path.exists()
            model_size = path.stat().st_size if model_exists else 0
            
            # Get training info from latest job
            trained_at = None
            training_pages = 0
            jobs = self.list_training_jobs()
            if jobs:
                latest_job = jobs[0]
                trained_at = latest_job.get("completed_at")
            
            return {
                "book_id": self.book_id,
                "model_type": "book_specific",
                "model_path": model_path,
                "model_exists": model_exists,
                "model_size_bytes": model_size,
                "trained_at": trained_at,
                "training_pages": training_pages
            }
        else:
            # Using global model
            global_path = self.model_path / "doclayout_yolo.pt"
            return {
                "book_id": self.book_id,
                "model_type": "global",
                "model_path": str(global_path) if global_path.exists() else None,
                "model_exists": global_path.exists(),
                "model_size_bytes": global_path.stat().st_size if global_path.exists() else 0,
                "trained_at": None,
                "training_pages": 0
            }
    
    def copy_model_from_book(self, source_book_id: int) -> Dict[str, Any]:
        """
        Copy another book's YOLO model to use for this book.
        
        Args:
            source_book_id: The book ID to copy the model from
            
        Returns:
            Dict with copy result
        """
        # Get source book's model path
        sql = text("""
            SELECT yolo_model_path
            FROM books_metadata
            WHERE book_id = :book_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql, {"book_id": source_book_id}).fetchone()
            
            if not result or not result[0]:
                return {
                    "success": False,
                    "error": f"Source book {source_book_id} has no trained model"
                }
            
            source_path = Path(result[0])
        
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source model file not found: {source_path}"
            }
        
        # Copy to this book's model path
        target_path = self.model_path / f"book_{self.book_id}_yolo.pt"
        
        try:
            shutil.copy2(source_path, target_path)
            
            # Update this book's model path
            self.set_book_model_path(str(target_path))
            
            logger.info(f"Copied model from book {source_book_id} to book {self.book_id}")
            
            return {
                "success": True,
                "source_path": str(source_path),
                "target_path": str(target_path),
                "copied_size_bytes": target_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"Error copying model: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# =============================================================================
# Helper Functions
# =============================================================================

def get_books_with_yolo_models() -> List[Dict[str, Any]]:
    """
    Get list of books that have trained YOLO models.
    
    Returns:
        List of books with their model info
    """
    sql = text("""
        SELECT book_id, book_name, yolo_model_path
        FROM books_metadata
        WHERE yolo_model_path IS NOT NULL
        ORDER BY book_name
    """)
    
    books = []
    with engine.connect() as conn:
        results = conn.execute(sql).fetchall()
        
        for row in results:
            model_path = Path(row[2]) if row[2] else None
            if model_path and model_path.exists():
                books.append({
                    "book_id": row[0],
                    "book_name": row[1],
                    "model_path": str(model_path),
                    "model_size_bytes": model_path.stat().st_size
                })
    
    return books


def get_yolo_training_service(book_id: int) -> YOLOTrainingService:
    """
    Factory function to create a YOLOTrainingService for a book.
    
    Args:
        book_id: The book ID
    
    Returns:
        YOLOTrainingService instance
    """
    sql = text("""
        SELECT table_prefix
        FROM books_metadata
        WHERE book_id = :book_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id}).fetchone()
        
        if not result:
            raise ValueError(f"Book {book_id} not found")
        
        table_prefix = result[0]
    
    return YOLOTrainingService(book_id, table_prefix)
