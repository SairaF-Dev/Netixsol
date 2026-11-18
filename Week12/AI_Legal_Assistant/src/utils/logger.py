"""
Logging utility for Khan & Associates Legal Assistant Pipeline.
"""
import logging
import sys

def setup_logger(name: str = "legal_pipeline", level: int = logging.INFO) -> logging.Logger:
    """Configures a standardized console and file logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
