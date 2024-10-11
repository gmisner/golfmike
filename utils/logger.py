import sys
from loguru import logger
import logging


# Intercept standard logging and redirect it to loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the log message originated
        frame, depth = sys._getframe(6), 6
        while frame.f_code.co_filename == logging.__file__:
            frame = sys._getframe(depth)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Apply the handler to the root logger
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

# Configure the main logger
main_logger = logger
main_logger.remove()
main_logger.add(
    sys.stderr,
    format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}",
)

# Optionally, add a file handler if needed
# main_logger.add("sqlalchemy_logs.log", rotation="10 MB")
