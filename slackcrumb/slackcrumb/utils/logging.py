"""Logging setup for Slackcrumb."""

import logging
import sys

from ..config import DEFAULT_CONFIG_DIR


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure file + console logging."""
    logger = logging.getLogger("slackcrumb")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    # File handler
    log_dir = DEFAULT_CONFIG_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "slackcrumb.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(file_handler)

    return logger
