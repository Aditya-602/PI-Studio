from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, ensure_pdf_file, emit_progress, output_path_for


def _page_numbers(value: str, page_count: int) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                start, end = int(start_text), int(end_text)
                if start > end:
                    raise ValueError
                selected = range(start, end + 1)
            else:
                selected = (int(token),)
        except ValueError as exc:
            raise ValueError(f"Invalid page selection: {token}") from exc
        for page in selected:
            if not 1 <= page <= page_count:
                raise ValueError(f"Page {page} is outside the document range 1-{page_count}.")
            if page - 1 not in pages:
                pages.append(page - 1)
    if not pages:
        raise ValueError("Enter a page selection such as 1, 3-5, or 2, 7-9.")
    return pages


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Extract selected pages into one new PDF."""
    if not inputs:
        raise ValueError("Please choose a PDF to extract from.")

    options = options or {}
    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        pages = _page_numbers(str(options.get("pages", "")), source.page_count)
        output_path = output_path_for(source_path, options, suffix="_extracted")
        document = fitz.open()
        try:
            for index, page_number in enumerate(pages, start=1):
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Cancelled.")
                document.insert_pdf(source, from_page=page_number, to_page=page_number)
                emit_progress(progress_cb, index / len(pages) * 100, f"Extracted page {index} of {len(pages)}")
            atomic_pdf_save(document, output_path, garbage=4, deflate=True)
        finally:
            document.close()
    finally:
        source.close()
    return [output_path]
