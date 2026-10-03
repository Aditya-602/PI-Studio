from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path


def log_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "PI-Studio" / "logs"
    if os.name == "posix" and os.uname().sysname == "Darwin":
        return Path.home() / "Library" / "Logs" / "PI-Studio"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "pdf-toolkit"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("pdf_toolkit")
    if logger.handlers:
        return logger
    directory = log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "app.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = configure_logging()


@dataclass
class Operation:
    tool: str
    input_count: int
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.monotonic)

    def event(self, status: str, **fields: object) -> None:
        safe_fields = {
            "operation_id": self.operation_id,
            "tool": self.tool,
            "input_count": self.input_count,
            "status": status,
            **fields,
        }
        LOGGER.info("operation %s", safe_fields)

    def finish(self, status: str, **fields: object) -> None:
        fields["duration_ms"] = round((time.monotonic() - self.started_at) * 1000)
        self.event(status, **fields)
