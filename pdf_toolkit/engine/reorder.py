from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Save a PDF with pages in the requested zero-based order."""
    if not inputs:
        raise ValueError("Please choose a PDF to reorder.")
    source_path = ensure_pdf_file(inputs[0])
    options = options or {}
    source = fitz.open(source_path)
    try:
        order = [int(page) for page in options.get("order", [])]
        if sorted(order) != list(range(source.page_count)):
            raise ValueError("Page order must contain every page exactly once.")
        output_path = output_path_for(source_path, options, suffix="_reordered")
        document = fitz.open()
        try:
            for position, page_number in enumerate(order, start=1):
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Cancelled.")
                document.insert_pdf(source, from_page=page_number, to_page=page_number)
                emit_progress(
                    progress_cb,
                    position / len(order) * 100,
                    f"Placed page {position} of {len(order)}",
                )
            atomic_pdf_save(document, output_path, garbage=4, deflate=True)
        finally:
            document.close()
    finally:
        source.close()
    return [output_path]
