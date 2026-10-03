from __future__ import annotations

from pathlib import Path

import fitz

from .common import atomic_pdf_save, cleanup_paths, ensure_pdf_file, emit_progress, output_path_for


def run(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Split a PDF into multiple files."""
    if not inputs:
        raise ValueError("Please choose a PDF to split.")

    source_path = ensure_pdf_file(inputs[0])
    source = fitz.open(source_path)
    mode = (options or {}).get("mode", "ranges")
    outputs: list[Path] = []

    try:
        if mode == "ranges":
            ranges = (options or {}).get("ranges", "")
            if not isinstance(ranges, str) or not ranges.strip():
                raise ValueError("Enter a page range such as 1-3, 5, 9-10.")
            fragments = []
            for chunk in ranges.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                if "-" in chunk:
                    start_text, end_text = chunk.split("-", 1)
                    start = max(1, int(start_text))
                    end = min(source.page_count, int(end_text))
                    fragments.extend(range(start - 1, end))
                else:
                    page_no = int(chunk) - 1
                    if 0 <= page_no < source.page_count:
                        fragments.append(page_no)
            unique_pages = sorted(set(fragments))
            output_path = output_path_for(source_path, options, suffix="_split_1")
            doc = fitz.open()
            for page_no in unique_pages:
                doc.insert_pdf(source, from_page=page_no, to_page=page_no)
            atomic_pdf_save(doc, output_path, garbage=4, deflate=True)
            doc.close()
            outputs.append(output_path)
        else:
            chunk_size = max(1, int((options or {}).get("chunk_size", 2)))
            for index in range(0, source.page_count, chunk_size):
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Cancelled.")
                chunk_doc = fitz.open()
                end = min(source.page_count, index + chunk_size)
                for page_no in range(index, end):
                    chunk_doc.insert_pdf(source, from_page=page_no, to_page=page_no)
                output_dir = Path((options or {}).get("output_dir", source_path.parent)).expanduser().resolve()
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{source_path.stem}_part_{index // chunk_size + 1}.pdf"
                counter = 1
                while output_path.exists():
                    output_path = output_dir / f"{source_path.stem}_part_{index // chunk_size + 1}_{counter}.pdf"
                    counter += 1
                atomic_pdf_save(chunk_doc, output_path, garbage=4, deflate=True)
                chunk_doc.close()
                outputs.append(output_path)
                emit_progress(progress_cb, (index / max(1, source.page_count)) * 100.0, f"Split chunk {len(outputs)}")
    except InterruptedError:
        cleanup_paths(outputs)
        raise
    finally:
        source.close()
    return outputs
