from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Rotate all pages in a PDF by 90, 180, or 270 degrees."""
    if not inputs:
        raise ValueError("Choose a PDF file to rotate.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    angle = int((options or {}).get("angle", 90))
    output_path = output_path_for(source_path, options, suffix=f"_rot{angle}")

    for index in range(source.page_count):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        page = source[index]
        page.set_rotation(angle)
        emit_progress(progress_cb, ((index + 1) / max(1, source.page_count)) * 100.0, f"Rotated page {index + 1}")

    atomic_pdf_save(source, output_path, garbage=4, deflate=True)
    source.close()
    return [output_path]
