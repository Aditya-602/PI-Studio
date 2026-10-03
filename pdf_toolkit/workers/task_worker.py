from __future__ import annotations

from threading import Event
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from pdf_toolkit.logging_config import Operation


class TaskWorker(QObject):
    progress = Signal(float, str)
    finished = Signal(object)
    error = Signal(str)
    diagnostic = Signal(str)

    def __init__(
        self,
        func: Callable[..., Any],
        *args: Any,
        cancel_event: Event | None = None,
        **kwargs: Any,
    ):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.cancel_event = cancel_event or Event()
        self.operation = Operation(
            tool=getattr(func, "__module__", "unknown").split(".")[-1],
            input_count=len(args[0]) if args and isinstance(args[0], (list, tuple)) else 0,
        )

    def run(self) -> None:
        self.operation.event("started")
        try:
            kwargs = dict(self._kwargs)
            kwargs.setdefault("progress_cb", self.progress.emit)
            kwargs.setdefault("cancel_event", self.cancel_event)
            result = self._func(*self._args, **kwargs)
            self.operation.finish("cancelled" if self.cancel_event.is_set() else "completed")
            self.finished.emit(result)
        except Exception as exc:  # pragma: no cover
            self.operation.finish(
                "cancelled" if isinstance(exc, InterruptedError) else "failed",
                error_type=type(exc).__name__,
            )
            self.diagnostic.emit(self.operation.operation_id)
            self.error.emit(str(exc))


def run_in_thread(thread_pool, func: Callable[..., Any], *args: Any, **kwargs: Any):
    worker = TaskWorker(func, *args, **kwargs)
    if hasattr(thread_pool, "start"):
        thread_pool.started.connect(worker.run)
    return worker
