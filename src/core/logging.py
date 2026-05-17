import logging
import sys


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(log_level: str = DEFAULT_LOG_LEVEL) -> None:
	level = getattr(logging, log_level.upper(), logging.INFO)
	logging.basicConfig(
		level=level,
		format=LOG_FORMAT,
		handlers=[
			logging.StreamHandler(sys.stdout),
		],
		force=True,
	)

	logging.getLogger("uvicorn").setLevel(level)
	logging.getLogger("uvicorn.error").setLevel(level)
	logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
	logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

	logging.getLogger(__name__).info("Logging configured", extra={"log_level": log_level.upper()})
