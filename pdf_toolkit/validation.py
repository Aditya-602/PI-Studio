from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {
    extension
    for extension, image_format in Image.registered_extensions().items()
    if not (
        (mime_type := Image.MIME.get(image_format))
        and not mime_type.startswith("image/")
    )
}
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_PDF_PAGES = 5000
MAX_IMAGE_PIXELS = 100_000_000
MIN_FREE_SPACE_BYTES = 100 * 1024 * 1024


def validate_inputs(paths: list[Path], kind: str) -> None:
    if not paths:
        raise ValueError("Choose at least one input file.")
    allowed = PDF_EXTENSIONS if kind == "pdf" else IMAGE_EXTENSIONS
    for path in paths:
        if not path.exists():
            raise ValueError(f"Input file does not exist: {path.name}")
        if not path.is_file():
            raise ValueError(f"Input is not a file: {path.name}")
        if path.suffix.lower() not in allowed:
            raise ValueError(f"Unsupported input format: {path.suffix.lower()}")
        if not path.stat().st_size:
            raise ValueError(f"Input file is empty: {path.name}")
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(
                f"Input file is too large: {path.name} "
                f"(maximum {MAX_INPUT_BYTES // (1024 * 1024)} MB)."
            )
        if not _readable(path, kind):
            raise ValueError(f"Input file could not be opened: {path.name}")


def validate_output_directory(
    directory: Path | None, required_bytes: int = 0
) -> Path | None:
    if directory is None:
        return None
    directory = directory.expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        raise ValueError("Output destination is not a directory.")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError("Output destination could not be created.") from exc
    if not directory.is_dir():
        raise ValueError("Output destination is not a directory.")
    probe = directory / ".pdf_toolkit_write_test"
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise ValueError("Output destination is not writable.") from exc
    required_space = max(MIN_FREE_SPACE_BYTES, required_bytes)
    try:
        available_bytes = shutil.disk_usage(directory).free
    except OSError as exc:
        raise ValueError("Could not determine available output disk space.") from exc
    if available_bytes < required_space:
        available_mb = available_bytes // (1024 * 1024)
        required_mb = required_space // (1024 * 1024)
        raise ValueError(
            f"Not enough free space in output destination "
            f"(available {available_mb} MB, required {required_mb} MB)."
        )
    return directory


def _readable(path: Path, kind: str) -> bool:
    try:
        if kind == "pdf":
            import fitz

            document = fitz.open(path)
            if document.page_count > MAX_PDF_PAGES:
                document.close()
                raise ValueError(
                    f"PDF has too many pages: {path.name} "
                    f"(maximum {MAX_PDF_PAGES})."
                )
            document.close()
        else:
            with Image.open(path) as image:
                image.verify()
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError(
                        f"Image dimensions are too large: {path.name} "
                        f"(maximum {MAX_IMAGE_PIXELS // 1_000_000} megapixels)."
                    )
        return True
    except ValueError:
        raise
    except Exception:
        return False
