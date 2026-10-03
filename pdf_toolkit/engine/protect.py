from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, emit_progress, ensure_pdf_file, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Encrypt a PDF with a user password and selected permissions."""
    if not inputs:
        raise ValueError("Choose a PDF file to protect.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    user_password = str((options or {}).get("user_password", ""))
    owner_password = str((options or {}).get("owner_password", "")) or user_password
    if len(user_password) < 4:
        source.close()
        raise ValueError("Password must be at least 4 characters.")
    if not owner_password:
        source.close()
        raise ValueError("Owner password cannot be empty.")
    permissions = int((options or {}).get("permissions", 0))
    output_path = output_path_for(source_path, options, suffix="_protected")
    atomic_pdf_save(
        source,
        output_path,
        garbage=4,
        deflate=True,
        encryption=4,
        user_pw=user_password,
        owner_pw=owner_password,
        permissions=permissions,
    )
    source.close()
    emit_progress(progress_cb, 100.0, "Document protected.")
    return [output_path]
