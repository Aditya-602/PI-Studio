from __future__ import annotations

import time

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from pdf_toolkit.workers.operation_service import OperationService


def _wait_for(predicate, timeout_ms: int = 2000) -> None:
    loop = QEventLoop()
    deadline = time.monotonic() + timeout_ms / 1000
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(loop.quit)
    timer.start()
    while not predicate() and time.monotonic() < deadline:
        loop.exec()
    timer.stop()
    assert predicate(), "Timed out waiting for operation state."


def test_operation_service_completes_and_clears_handle():
    app = QCoreApplication.instance() or QCoreApplication([])
    service = OperationService()
    results: list[object] = []
    states: list[str] = []
    service.completed.connect(results.append)
    service.state_changed.connect(states.append)

    def complete(progress_cb=None, cancel_event=None):
        return ["done"]

    assert service.start(complete)
    _wait_for(lambda: bool(results))
    _wait_for(lambda: not service.running)

    assert results == [["done"]]
    assert states[:1] == ["running"]
    assert "completed" in states
    del app


def test_operation_service_rejects_duplicate_run():
    app = QCoreApplication.instance() or QCoreApplication([])
    service = OperationService()

    def slow(cancel_event=None, progress_cb=None):
        while not cancel_event.is_set():
            time.sleep(0.005)
        raise InterruptedError("Cancelled.")

    failures: list[str] = []
    service.failed.connect(lambda message, diagnostic: failures.append(message))
    assert service.start(slow)
    assert not service.start(slow)
    assert failures == ["Another task is already running."]
    assert service.shutdown(1000)
    del app


def test_operation_service_reports_diagnostic_on_failure():
    app = QCoreApplication.instance() or QCoreApplication([])
    service = OperationService()
    failures: list[tuple[str, str]] = []
    service.failed.connect(lambda message, diagnostic: failures.append((message, diagnostic)))

    def fail(progress_cb=None, cancel_event=None):
        raise ValueError("bad input")

    assert service.start(fail)
    _wait_for(lambda: bool(failures))
    _wait_for(lambda: not service.running)

    assert failures and failures[0][0] == "bad input"
    assert failures[0][1]
    del app


def test_operation_services_run_concurrently_and_finish_independently():
    app = QCoreApplication.instance() or QCoreApplication([])
    first = OperationService()
    second = OperationService()
    completed: list[str] = []

    def work(name, progress_cb=None, cancel_event=None):
        for value in (25, 50, 75):
            if cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            progress_cb(value, name)
            time.sleep(0.01)
        return name

    first.completed.connect(lambda result: completed.append(result))
    second.completed.connect(lambda result: completed.append(result))
    assert first.start(work, "first")
    assert second.start(work, "second")

    _wait_for(lambda: len(completed) == 2)
    _wait_for(lambda: not first.running and not second.running)

    assert sorted(completed) == ["first", "second"]
    assert first.shutdown() and second.shutdown()
    del app


def test_cancelling_one_operation_does_not_cancel_another():
    app = QCoreApplication.instance() or QCoreApplication([])
    cancelled = OperationService()
    completing = OperationService()
    results: list[object] = []
    failures: list[str] = []

    def cancellable(progress_cb=None, cancel_event=None):
        while not cancel_event.is_set():
            progress_cb(10, "waiting")
            time.sleep(0.005)
        raise InterruptedError("Cancelled.")

    def complete(progress_cb=None, cancel_event=None):
        time.sleep(0.03)
        return "completed"

    cancelled.failed.connect(lambda message, _diagnostic: failures.append(message))
    completing.completed.connect(results.append)
    assert cancelled.start(cancellable)
    assert completing.start(complete)
    time.sleep(0.01)
    cancelled.cancel()

    _wait_for(lambda: bool(failures) and bool(results))
    _wait_for(lambda: not cancelled.running and not completing.running)

    assert failures == ["Cancelled."]
    assert results == ["completed"]
    assert completing.shutdown()
    del app


def test_operation_service_can_be_reused_after_completion():
    app = QCoreApplication.instance() or QCoreApplication([])
    service = OperationService()
    results: list[object] = []
    service.completed.connect(results.append)

    def complete(progress_cb=None, cancel_event=None):
        return "done"

    assert service.start(complete)
    _wait_for(lambda: len(results) == 1)
    _wait_for(lambda: not service.running)
    assert service.start(complete)
    _wait_for(lambda: len(results) == 2)
    _wait_for(lambda: not service.running)

    assert results == ["done", "done"]
    del app
