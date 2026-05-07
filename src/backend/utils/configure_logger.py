"""
Logger configuration utility for TechBuddy using Loguru.
"""

import sys
from pathlib import Path
from loguru import logger


def configure_logger(
    log_level: str = "INFO",
    log_file: str = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    colorize: bool = True,
    backtrace: bool = True,
    diagnose: bool = True,
):
    """
    Configure the loguru logger with custom settings.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, only console logging is enabled.
        rotation: When to rotate log files (e.g., "10 MB", "1 day", "1 week")
        retention: How long to keep old log files (e.g., "7 days", "2 weeks")
        colorize: Whether to colorize console output
        backtrace: Whether to enable backtrace in error logs
        diagnose: Whether to enable diagnostic information in error logs

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Console handler with custom format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=colorize,
        backtrace=backtrace,
        diagnose=diagnose,
    )

    # File handler (if log_file is specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )

        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=backtrace,
            diagnose=diagnose,
        )

        logger.info(f"File logging enabled: {log_file}")

    logger.info(f"Logger configured with level: {log_level}")

    return logger
