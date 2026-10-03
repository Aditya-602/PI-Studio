from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Permanently redact every occurrence of the requested text terms."""
    if not inputs:
        raise ValueError("Choose a PDF file to redact.")
    options = options or {}
    terms = [term.strip() for term in str(options.get("terms", "")).split(",") if term.strip()]
    if not terms:
        raise ValueError("Enter one or more terms to redact, separated by commas.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before redaction.")
        output_path = output_path_for(source_path, options, suffix="_redacted")
        total_matches = 0
        for page_index, page in enumerate(source):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            for term in terms:
                for rectangle in page.search_for(term):
                    page.add_redact_annot(rectangle, fill=(0, 0, 0), cross_out=False)
                    total_matches += 1
            page.apply_redactions()
            emit_progress(
                progress_cb,
                (page_index + 1) / max(1, source.page_count) * 100,
                f"Redacted page {page_index + 1}",
            )
        if total_matches == 0:
            raise ValueError("No matching text was found to redact.")
        atomic_pdf_save(source, output_path, garbage=4, clean=True, deflate=True)
    finally:
        source.close()
    return [output_path]
