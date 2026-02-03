"""Utility functions."""

import logging
from typing import Optional


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("forge")
