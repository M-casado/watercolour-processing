"""
logging_config.py

Configures a daily rotating log file with a date in its filename,
and optional console output at INFO level.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def get_logger(name: str = "watercolour") -> logging.Logger:
    """
    Returns a logger that writes to a daily rotating file named with today's date,
    plus an optional console handler at INFO level.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        # Avoid adding duplicate handlers if logger is called multiple times
        return logger

    logger.setLevel(logging.DEBUG)  # Global level for all messages

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Daily rotating file named with current date (e.g., watercolour_2023-02-01.log)
    log_filename = os.path.join(log_dir, f"watercolour_{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when="midnight",
        interval=1,
        backupCount=20  # keep last 20 days of logs, then delete
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Optional console output (set to INFO so DEBUG logs don't spam the console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_format)
    logger.addHandler(console_handler)

    return logger