from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for
from .extract import _page_numbers


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Remove selected pages from a PDF and save a new copy."""
    if not inputs:
        raise ValueError("Please choose a PDF to edit.")

    options = options or {}
    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        removed = set(_page_numbers(str(options.get("pages", "")), source.page_count))
        if len(removed) == source.page_count:
            raise ValueError("At least one page must remain in the PDF.")
        output_path = output_path_for(source_path, options, suffix="_pages_removed")
        document = fitz.open()
        try:
            kept = [index for index in range(source.page_count) if index not in removed]
            for index, page_number in enumerate(kept, start=1):
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Cancelled.")
                document.insert_pdf(source, from_page=page_number, to_page=page_number)
                emit_progress(progress_cb, index / len(kept) * 100, f"Kept page {index} of {len(kept)}")
            atomic_pdf_save(document, output_path, garbage=4, deflate=True)
        finally:
            document.close()
    finally:
        source.close()
    return [output_path]
