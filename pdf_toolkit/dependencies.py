from __future__ import annotations

from dataclasses import dataclass
from shutil import which


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    installed: bool
    path: str | None
    required: bool = False


def detect_optional_tools() -> dict[str, DependencyStatus]:
    names = {
        "tesseract": "Tesseract",
        "gs": "Ghostscript",
        "soffice": "LibreOffice",
        "ocrmypdf": "OCRmyPDF",
        "python": "Python",
    }
    result: dict[str, DependencyStatus] = {}
    for command, label in names.items():
        resolved = which(command)
        result[command] = DependencyStatus(
            name=label,
            installed=bool(resolved),
            path=resolved,
            required=command in {"tesseract", "gs", "soffice"},
        )
    return result


def dependency_hint(command: str, extra_message: str | None = None) -> str:
    status = detect_optional_tools().get(command)
    if status and status.installed:
        return f"Ready: {status.name} at {status.path}"
    if extra_message:
        return extra_message
    return f"Requires {command.title()} and will stay disabled until it is installed."
