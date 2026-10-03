from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable
import os


def next_output_path(source: str | Path, suffix: str = "_out", extension: str = ".pdf") -> Path:
    source_path = Path(source)
    stem = source_path.stem
    target = source_path.with_name(f"{stem}{suffix}{extension}")
    counter = 1
    while target.exists():
        target = source_path.with_name(f"{stem}{suffix}_{counter}{extension}")
        counter += 1
    return target


def output_path_for(source: str | Path, options: dict | None, suffix: str = "_out") -> Path:
    source_path = Path(source)
    output_dir = Path((options or {}).get("output_dir", source_path.parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return next_output_path(output_dir / source_path.name, suffix=suffix)


def ensure_pdf_file(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Input file not found: {resolved}")
    if resolved.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, received: {resolved}")
    return resolved


def coerce_path_list(paths: Iterable[str | Path]) -> list[Path]:
    items = [Path(p).expanduser().resolve() for p in paths]
    return [p for p in items if p.exists()]


def parse_page_ranges(step_text: str | None) -> list[int]:
    if not step_text:
        return []
    pages: list[int] = []
    for part in str(step_text).split(","):
        candidate = part.strip()
        if not candidate:
            continue
        if "-" in candidate:
            start_str, end_str = candidate.split("-", 1)
            try:
                start = int(start_str.strip())
                end = int(end_str.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid page range: {candidate}") from exc
            pages.extend(range(start, end + 1))
        else:
            try:
                pages.append(int(candidate))
            except ValueError as exc:
                raise ValueError(f"Invalid page number: {candidate}") from exc
    return pages


def emit_progress(progress_cb: Callable[[float, str], None] | None, value: float, message: str) -> None:
    if progress_cb is not None:
        progress_cb(value, message)


def safe_mkdir(path: str | Path) -> Path:
    directory = Path(path).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def file_size_bytes(path: str | Path) -> int:
    return os.path.getsize(Path(path))


def cleanup_paths(paths: Iterable[str | Path]) -> None:
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            # Best effort cleanup must not hide the original cancellation/error.
            continue


def atomic_pdf_save(document, output: str | Path, **kwargs: object) -> Path:
    """Save a PDF beside its destination, then publish it with one rename."""
    destination = Path(output)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp.pdf")
    try:
        document.save(temporary, **kwargs)
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return destination
