import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Create logger
def setup_logger(name="telegram_bot_logger", log_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Create log directory if it doesn't exist
    log_directory = Path(__file__).resolve().parent / "logging"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    
    # Create log file name with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file_name = f"app_{current_date}.log"
    
    # Create handler for file rotation
    handler = TimedRotatingFileHandler(
        filename=os.path.join(log_directory, log_file_name),
        when="midnight",
        interval=1,
        backupCount=7  # Keep logs for 7 days
    )
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger if it doesn't already have it
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger

# Create default application logger
app_logger = setup_logger()