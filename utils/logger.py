"logger.py import to other python files"
import sys
from loguru import logger

# Configure the main logger
logger.remove(0)
logger.add(
    sys.stderr, format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}"
)

main_logger = logger
