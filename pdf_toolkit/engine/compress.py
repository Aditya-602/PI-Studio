from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


COMPRESSION_PROFILES = {
    "Extreme": {"quality": 45, "dpi_threshold": 120, "dpi_target": 96},
    "Recommended": {"quality": 68, "dpi_threshold": 160, "dpi_target": 144},
    "Less": {"quality": 84, "dpi_threshold": 220, "dpi_target": 180},
}


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Recompress embedded PDF images while preserving text and vector content."""
    if not inputs:
        raise ValueError("Choose a PDF file to compress.")

    options = options or {}
    source_path = ensure_pdf_file(inputs[0])
    profile_name = str(options.get("level", "Recommended"))
    profile = COMPRESSION_PROFILES.get(profile_name, COMPRESSION_PROFILES["Recommended"])
    output_path = output_path_for(source_path, options, suffix="_compressed")

    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Cancelled.")

    document = fitz.open(source_path)
    emit_progress(progress_cb, 5.0, "Reading PDF structure")
    try:
        document.rewrite_images(
            dpi_threshold=profile["dpi_threshold"],
            dpi_target=profile["dpi_target"],
            quality=profile["quality"],
            lossy=True,
            lossless=True,
            bitonal=True,
            color=True,
            gray=True,
        )
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        emit_progress(progress_cb, 75.0, "Recompressing embedded images")
        atomic_pdf_save(
            document,
            output_path,
            garbage=4,
            clean=1,
            deflate=1,
            deflate_images=1,
            deflate_fonts=1,
            use_objstms=1,
            compression_effort=3,
            preserve_metadata=1,
        )
    finally:
        document.close()

    emit_progress(progress_cb, 100.0, "Compression complete")
    return [output_path]
