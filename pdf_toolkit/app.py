from __future__ import annotations

from .ui.main_window import launch_app
from .logging_config import LOGGER


def main() -> None:
    LOGGER.info("application_started")
    launch_app()
