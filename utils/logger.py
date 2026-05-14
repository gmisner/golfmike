import sys
import logging
from loguru import logger


class InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru."""

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


# Wire root logger → loguru once (idempotent: basicConfig is a no-op if handlers exist)
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=False)

# SQLAlchemy: WARNING only, no propagation to root (avoids double-emit)
_sa_logger = logging.getLogger("sqlalchemy.engine")
_sa_logger.setLevel(logging.WARNING)
_sa_logger.propagate = False
if not _sa_logger.handlers:
    _sa_logger.addHandler(InterceptHandler())

# Loguru sink — remove default, add one structured sink (idempotent across re-imports)
main_logger = logger
main_logger.remove()
main_logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} UTC | {level:<8} | {name}:{line} | {message}",
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=False,  # keep False in prod; set True locally for stack-var dumps
)
