from __future__ import annotations

import difflib
from pathlib import Path

import fitz

from .common import emit_progress, ensure_pdf_file, next_output_path


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Compare two PDFs and write a local plain-text report."""
    if len(inputs) != 2:
        raise ValueError("Choose exactly two PDF files to compare.")

    options = options or {}
    first_path, second_path = (ensure_pdf_file(path) for path in inputs)
    first = fitz.open(first_path)
    second = fitz.open(second_path)
    try:
        output_dir = Path(options.get("output_dir", first_path.parent)).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = next_output_path(
            output_dir / first_path.name,
            suffix="_comparison",
            extension=".txt",
        )
        lines = [
            "PDF COMPARISON REPORT",
            f"FILE A: {first_path}",
            f"FILE B: {second_path}",
            f"PAGES A: {first.page_count}",
            f"PAGES B: {second.page_count}",
            "",
        ]
        max_pages = max(first.page_count, second.page_count)
        differences = 0
        for index in range(max_pages):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            text_a = first[index].get_text().splitlines() if index < first.page_count else []
            text_b = second[index].get_text().splitlines() if index < second.page_count else []
            if text_a != text_b:
                differences += 1
                lines.extend(
                    [
                        f"PAGE {index + 1}: DIFFERENT",
                        *difflib.unified_diff(
                            text_a,
                            text_b,
                            fromfile=f"{first_path.name} page {index + 1}",
                            tofile=f"{second_path.name} page {index + 1}",
                            lineterm="",
                        ),
                        "",
                    ]
                )
            emit_progress(progress_cb, (index + 1) / max(1, max_pages) * 100, f"Compared page {index + 1}")
        lines.insert(5, f"DIFFERING PAGES: {differences}")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    finally:
        first.close()
        second.close()
    return [output_path]
