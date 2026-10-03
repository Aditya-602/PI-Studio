from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, ensure_pdf_file, emit_progress, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Merge a list of PDFs into a single output PDF."""
    files = [ensure_pdf_file(path) for path in inputs]
    if not files:
        raise ValueError("Please select at least one PDF file to merge.")

    output_path = output_path_for(files[0], options, suffix="_merged")
    merged = fitz.open()
    total = len(files)

    for index, file_path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")

        source = fitz.open(file_path)
        source_pages = list(range(source.page_count))
        if options and options.get("pages"):
            source_pages = []
            for page in options["pages"]:
                if 0 <= page < source.page_count:
                    source_pages.append(page)
        for page_no in source_pages:
            merged.insert_pdf(source, from_page=page_no, to_page=page_no)
        source.close()
        emit_progress(progress_cb, (index / total) * 100.0, f"Merged {file_path.name}")

    atomic_pdf_save(merged, output_path, garbage=4, deflate=True)
    merged.close()
    return [output_path]
