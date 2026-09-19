"""Central file logging with privacy-safe, allowlisted metadata only.

Logs go to data/logs/skill_erosion.log (override with SKILL_EROSION_LOG).
Raw response_text, tool arguments, and other sensitive fields are never
logged; only allowlisted metadata appears.
"""

import logging
import os
import sys
from contextlib import contextmanager
from functools import wraps
from inspect import signature
from time import perf_counter
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
        terminal = logging.StreamHandler(sys.stdout)
        terminal.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(terminal)
        root.setLevel(os.environ.get("SKILL_EROSION_LOG_LEVEL", "INFO").upper())
        root.propagate = False
    _configured = True


def get_logger(name: str, *, separate_file: bool = False) -> logging.Logger:
    _configure()
    logger_name = name if name.startswith(_ROOT_LOGGER) else f"{_ROOT_LOGGER}.{name}"
    logger = logging.getLogger(logger_name)
    if not separate_file:
        return logger

    if not any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", "").endswith(f"{name.rsplit('.', 1)[-1]}.log")
        for handler in logging.getLogger(_ROOT_LOGGER).handlers
    ):
        path = project_root() / "data" / "logs" / f"{name.rsplit('.', 1)[-1]}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logging.getLogger(_ROOT_LOGGER).addHandler(handler)
    logger.propagate = True
    return logger


@contextmanager
def agent_call(logger: logging.Logger, agent: str, student_id: str = "-", skill_id: str = "-"):
    """Log privacy-safe agent start, completion timing, and failures."""
    started = perf_counter()
    logger.info("agent=%s start student_id=%s skill_id=%s", agent, student_id, skill_id)
    try:
        yield
    except Exception:
        logger.exception(
            "agent=%s error student_id=%s skill_id=%s duration_ms=%.2f",
            agent, student_id, skill_id, (perf_counter() - started) * 1000,
        )
        raise


def agent_result(
    logger: logging.Logger,
    agent: str,
    student_id: str,
    skill_id: str,
    summary: str,
    started: float,
) -> None:
    """Log a privacy-safe result summary for an agent call."""
    logger.info(
        "agent=%s result student_id=%s skill_id=%s summary=%s duration_ms=%.2f",
        agent, student_id, skill_id, summary, (perf_counter() - started) * 1000,
    )


def timed_agent(logger: logging.Logger, agent: str):
    """Decorate an agent entry point with privacy-safe timing summaries."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            started = perf_counter()
            bound = signature(function).bind_partial(*args, **kwargs)
            scope = next(
                (
                    bound.arguments.get(name)
                    for name in ("trend", "cluster", "result")
                    if bound.arguments.get(name) is not None
                ),
                None,
            )
            if scope is not None and hasattr(scope, "trend"):
                scope = scope.trend
            student_id = bound.arguments.get("student_id", getattr(scope, "student_id", "-"))
            skill_id = bound.arguments.get("skill_id", getattr(scope, "skill_id", "-"))
            if isinstance(scope, dict):
                student_id = scope.get("student_id", student_id)
                skill_id = scope.get("skill_id", skill_id)
            if "attempts" in bound.arguments:
                attempt_values = list(bound.arguments["attempts"])
                students = {getattr(item, "student_id", "-") for item in attempt_values}
                skills = {getattr(item, "skill_id", "-") for item in attempt_values}
                student_id = next(iter(students)) if len(students) == 1 else "multiple"
                skill_id = next(iter(skills)) if len(skills) == 1 else "multiple"
            if not isinstance(student_id, str):
                student_id = "-"
            if not isinstance(skill_id, str):
                skill_id = "-"
            logger.info("agent=%s start student_id=%s skill_id=%s", agent, student_id, skill_id)
            try:
                result = function(*args, **kwargs)
            except Exception:
                logger.exception(
                    "agent=%s error student_id=%s skill_id=%s duration_ms=%.2f",
                    agent, student_id, skill_id, (perf_counter() - started) * 1000,
                )
                raise
            if student_id == "-" and hasattr(result, "student_id"):
                student_id = result.student_id
            if skill_id == "-" and hasattr(result, "skill_id"):
                skill_id = result.skill_id
            if isinstance(result, list):
                summary = f"count={len(result)}"
            elif hasattr(result, "status"):
                summary = f"status={result.status}"
            elif hasattr(result, "verdict"):
                summary = f"verdict={result.verdict}"
            elif hasattr(result, "attempt_ids"):
                summary = f"count={len(result.attempt_ids)}"
            elif isinstance(result, str):
                summary = "text=redacted"
            else:
                summary = f"type={type(result).__name__}"
            logger.info(
                "agent=%s result student_id=%s skill_id=%s summary=%s duration_ms=%.2f",
                agent, student_id, skill_id, summary, (perf_counter() - started) * 1000,
            )
            return result
        return wrapped
    return decorate