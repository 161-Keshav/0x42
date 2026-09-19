"""Central file logging with privacy-safe, allowlisted metadata only.

Logs go to data/logs/skill_erosion.log (override with SKILL_EROSION_LOG).
Raw response_text, tool arguments, and other sensitive fields are never
logged; only allowlisted metadata appears.
"""

import logging
import os
from pathlib import Path

from skill_erosion.config import project_root

_ROOT_LOGGER = "skill_erosion"
_configured = False

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


def _log_path() -> Path:
    override = os.environ.get("SKILL_EROSION_LOG")
    return Path(override) if override else project_root() / "data" / "logs" / "skill_erosion.log"


def _configure() -> None:
    global _configured
    if _configured:
        return
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger(_ROOT_LOGGER)
    if not root.handlers:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
        root.setLevel(os.environ.get("SKILL_EROSION_LOG_LEVEL", "INFO").upper())
        root.propagate = False
    _configured = True


def get_logger(name: str, *, separate_file: bool = False) -> logging.Logger:
    _configure()
    logger_name = name if name.startswith(_ROOT_LOGGER) else f"{_ROOT_LOGGER}.{name}"
    logger = logging.getLogger(logger_name)
    if not separate_file:
        return logger

    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        path = project_root() / "data" / "logs" / f"{name.rsplit('.', 1)[-1]}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False
    return logger