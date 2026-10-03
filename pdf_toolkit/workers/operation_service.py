from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal

from .task_worker import TaskWorker


@dataclass
class OperationHandle:
    thread: QThread
    worker: TaskWorker
    cancel_event: Event


class OperationService(QObject):
    progress = Signal(float, str)
    completed = Signal(object)
    failed = Signal(str, str)
    state_changed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._handle: OperationHandle | None = None
        self._diagnostic_id = ""
        self._final_state = ""

    @property
    def running(self) -> bool:
        return self._handle is not None

    def start(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> bool:
        if self.running:
            self.failed.emit("Another task is already running.", "")
            return False

        cancel_event = Event()
        thread = QThread(self)
        worker = TaskWorker(function, *args, cancel_event=cancel_event, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        worker.diagnostic.connect(self._on_diagnostic)
        # The GUI event loop may be blocked in shutdown while waiting for the
        # worker. Quit the thread directly so queued delivery cannot deadlock.
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        worker.error.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_handle)
        self._handle = OperationHandle(thread, worker, cancel_event)
        self._final_state = ""
        self.state_changed.emit("running")
        thread.start()
        return True

    def cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel_event.set()
            self.state_changed.emit("cancelling")

    def shutdown(self, timeout_ms: int = 2000) -> bool:
        """Request cancellation and wait a bounded amount of time for the worker."""
        handle = self._handle
        if handle is None or not handle.thread.isRunning():
            return True
        self.cancel()
        stopped = handle.thread.wait(timeout_ms)
        if stopped and self._handle is handle:
            self._handle = None
        return stopped

    def _on_finished(self, result: object) -> None:
        self.completed.emit(result)
        self._final_state = "completed"

    def _on_error(self, message: str) -> None:
        self.failed.emit(message, self._diagnostic_id)
        self._diagnostic_id = ""
        self._final_state = "failed"

    def _on_diagnostic(self, operation_id: str) -> None:
        self._diagnostic_id = operation_id

    def _clear_handle(self) -> None:
        self._handle = None
        if self._final_state:
            self.state_changed.emit(self._final_state)
            self._final_state = ""
