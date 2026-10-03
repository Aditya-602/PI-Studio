from __future__ import annotations

from pathlib import Path

import fitz

from .common import emit_progress, ensure_pdf_file, next_output_path


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Write an inventory of interactive PDF form fields."""
    if not inputs:
        raise ValueError("Choose a PDF file to inspect.")
    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    try:
        if source.needs_pass:
            raise ValueError("Password-protected PDFs must be unlocked before inspecting forms.")
        output_dir = Path((options or {}).get("output_dir", source_path.parent)).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = next_output_path(
            output_dir / source_path.name,
            suffix="_form_fields",
            extension=".txt",
        )
        lines = ["PDF FORM FIELD INVENTORY", f"FILE: {source_path}", ""]
        fields = 0
        for page_number, page in enumerate(source, start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    fields += 1
                    name = str(getattr(widget, "field_name", "") or "(unnamed)")
                    field_type = str(getattr(widget, "field_type_string", "") or "unknown")
                    value = str(getattr(widget, "field_value", "") or "")
                    lines.append(f"PAGE {page_number} | {field_type} | {name} | VALUE: {value}")
            emit_progress(progress_cb, page_number / max(1, source.page_count) * 100, f"Inspected page {page_number}")
        if not fields:
            lines.append("NO INTERACTIVE FORM FIELDS FOUND")
        lines.insert(2, f"FIELDS: {fields}")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    finally:
        source.close()
    return [output_path]
