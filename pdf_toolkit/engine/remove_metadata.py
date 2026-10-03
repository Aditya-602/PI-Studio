from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Remove document metadata from a PDF while preserving its pages."""
    if not inputs:
        raise ValueError("Choose a PDF file to clean.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before cleaning metadata.")
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        source.set_metadata({})
        output_path = output_path_for(source_path, options, suffix="_metadata_removed")
        atomic_pdf_save(source, output_path, garbage=4, deflate=True)
    finally:
        source.close()
    emit_progress(progress_cb, 100.0, "Metadata removed.")
    return [output_path]
