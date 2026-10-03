from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Rewrite a readable PDF into a cleaned, compact document."""
    if not inputs:
        raise ValueError("Choose a PDF file to repair.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before repair.")
        output_path = output_path_for(source_path, options, suffix="_repaired")
        repaired = fitz.open()
        try:
            for index in range(source.page_count):
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Cancelled.")
                repaired.insert_pdf(source, from_page=index, to_page=index)
                emit_progress(progress_cb, (index + 1) / max(1, source.page_count) * 100, f"Repaired page {index + 1}")
            atomic_pdf_save(repaired, output_path, garbage=4, clean=True, deflate=True)
        finally:
            repaired.close()
    finally:
        source.close()
    return [output_path]
