import logging
import structlog
from config import settings


def setup_logger():
    # setup logger
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_warning = False
    if settings.log.level in log_levels:
        log_level = log_levels[settings.log.level]
    else:
        log_level = log_levels["INFO"]
        log_warning = True
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )
    log = structlog.get_logger()
    if log_warning:
        log.warning(f"invalid log level: {settings.log.level}, defaulting to INFO")
    return log
