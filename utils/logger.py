import sys
from loguru import logger
import logging


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame.f_code.co_filename == logging.__file__:
            frame = sys._getframe(depth)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Apply the InterceptHandler to the root logger
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)


# SQLAlchemy-specific handler
class SQLAlchemyLoguruHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


# Configure SQLAlchemy's logger to use the custom Loguru handler
sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.DEBUG)  # Set to desired logging level
sqlalchemy_logger.addHandler(SQLAlchemyLoguruHandler())

# Configure the main logger (loguru)
main_logger = logger
main_logger.remove()  # Remove default configuration to prevent logging to files
main_logger.add(
    sys.stderr,
    format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message}",
)
