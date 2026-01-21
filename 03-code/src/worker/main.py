"""
Worker Main Entry Point

Standalone backend worker for processing Claude API pipeline tasks.
Run this script to start the worker process.

Usage:
    python -m src.worker.main
    python -m src.worker.main --worker-id worker-002
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.worker.config import get_config
from src.worker.loop import WorkerLoop


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Setup logging configuration.

    Args:
        log_level: Logging level
        log_file: Optional log file path
    """
    logging_config = {
        "level": getattr(logging, log_level.upper()),
        "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S"
    }

    if log_file:
        logging_config["filename"] = log_file
        logging_config["filemode"] = "a"

    logging.basicConfig(**logging_config)


def main():
    """Main entry point"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Claude Pipeline Worker - Backend task processor"
    )
    parser.add_argument(
        "--worker-id",
        type=str,
        help="Worker ID (default: from config)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log file path (default: stdout)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)

    logger = logging.getLogger(__name__)

    # Load configuration
    try:
        config = get_config()
        logger.info("Configuration loaded successfully")
        logger.info(f"Database: {config.database_url.split('@')[-1] if '@' in config.database_url else 'configured'}")
        logger.info(f"Poll interval: {config.poll_interval_seconds}s")
        logger.info(f"Max parallel tasks: {config.max_parallel_tasks}")

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.error("Please ensure .env file exists with required settings")
        sys.exit(1)

    # Create and start worker
    try:
        worker_id = args.worker_id or config.worker_id

        logger.info("=" * 60)
        logger.info("Claude Pipeline Worker")
        logger.info("=" * 60)
        logger.info(f"Worker ID: {worker_id}")
        logger.info(f"Starting worker process...")
        logger.info("=" * 60)

        worker = WorkerLoop(worker_id=worker_id)
        worker.start()

    except KeyboardInterrupt:
        logger.info("\nReceived keyboard interrupt. Shutting down...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
