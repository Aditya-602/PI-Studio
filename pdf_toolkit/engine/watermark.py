from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Apply a text watermark to every page of a PDF."""
    if not inputs:
        raise ValueError("Choose a PDF file to watermark.")
    options = options or {}
    text = str(options.get("text", "")).strip()
    if not text:
        raise ValueError("Enter watermark text.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before watermarking.")
        opacity = max(0.05, min(1.0, float(options.get("opacity", 35)) / 100))
        rotation = int(options.get("rotation", 45))
        output_path = output_path_for(source_path, options, suffix="_watermarked")
        for index, page in enumerate(source, start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            rect = page.rect
            page.insert_text(
                (rect.width * 0.18, rect.height * 0.55),
                text,
                fontsize=min(42, max(18, rect.width / 14)),
                color=(0.45, 0.45, 0.45),
                rotate=rotation,
                fill_opacity=opacity,
                overlay=True,
            )
            emit_progress(progress_cb, index / max(1, source.page_count) * 100, f"Watermarked page {index}")
        atomic_pdf_save(source, output_path, garbage=4, deflate=True)
    finally:
        source.close()
    return [output_path]
