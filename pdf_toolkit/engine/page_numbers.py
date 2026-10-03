from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Add page numbers to every page in a PDF."""
    if not inputs:
        raise ValueError("Choose a PDF file to number.")
    options = options or {}
    try:
        start_number = int(options.get("start_number", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Starting page number must be a whole number.") from exc
    if start_number < 1:
        raise ValueError("Starting page number must be at least 1.")
    position = str(options.get("position", "bottom-center"))
    positions = {
        "bottom-left": 0.08,
        "bottom-center": 0.5,
        "bottom-right": 0.92,
    }
    if position not in positions:
        raise ValueError("Choose a valid page-number position.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before numbering.")
        output_path = output_path_for(source_path, options, suffix="_numbered")
        for index, page in enumerate(source):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            rect = page.rect
            text = str(start_number + index)
            width = fitz.get_text_length(text, fontname="helv", fontsize=10)
            x = rect.width * positions[position] - width / 2
            if position == "bottom-left":
                x = rect.width * 0.08
            elif position == "bottom-right":
                x = rect.width * 0.92 - width
            page.insert_text(
                (x, rect.height - 24),
                text,
                fontsize=10,
                fontname="helv",
                color=(0.25, 0.25, 0.25),
                overlay=True,
            )
            emit_progress(progress_cb, (index + 1) / max(1, source.page_count) * 100, f"Numbered page {index + 1}")
        atomic_pdf_save(source, output_path, garbage=4, deflate=True)
    finally:
        source.close()
    return [output_path]
