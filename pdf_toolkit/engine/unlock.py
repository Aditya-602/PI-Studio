from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Remove password protection from a PDF when the password is known."""
    if not inputs:
        raise ValueError("Choose a PDF file to unlock.")

    source_path = ensure_pdf_file(inputs[0])
    password = str((options or {}).get("password", ""))
    if not password:
        raise ValueError("Enter the PDF password.")

    source = fitz.open(source_path)
    try:
        if source.needs_pass and not source.authenticate(password):
            raise ValueError("The PDF password is incorrect.")
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        output_path = output_path_for(source_path, options, suffix="_unlocked")
        atomic_pdf_save(
            source,
            output_path,
            garbage=4,
            deflate=True,
            encryption=fitz.PDF_ENCRYPT_NONE,
            user_pw="",
            owner_pw="",
        )
    finally:
        source.close()
    emit_progress(progress_cb, 100.0, "Document unlocked.")
    return [output_path]
