from __future__ import annotations

from collections import deque
from pathlib import Path

import fitz
from PIL import Image

from .common import cleanup_paths, ensure_pdf_file, output_path_for
from pdf_toolkit.validation import IMAGE_EXTENSIONS


def _image_paths(inputs) -> list[Path]:
    paths = [Path(path).expanduser().resolve() for path in inputs]
    if not paths:
        raise ValueError("Choose at least one image.")
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {path.suffix}")
    return paths


def images_to_pdf(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    paths = _image_paths(inputs)
    first = paths[0]
    output_dir = Path((options or {}).get("output_dir", first.parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_path_for(first, {"output_dir": str(output_dir)}, suffix="_images")
    document = fitz.open()
    for index, path in enumerate(paths):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            page = document.new_page(width=rgb.width, height=rgb.height)
            page.insert_image(page.rect, stream=_image_bytes(rgb, "JPEG"))
        if progress_cb:
            progress_cb((index + 1) / len(paths) * 100, f"Added {path.name}")
    document.save(output, garbage=4, deflate=True)
    document.close()
    return [output]


def _image_bytes(image: Image.Image, fmt: str) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format=fmt, quality=92, optimize=True)
    return buffer.getvalue()


def compress_image(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    paths = _image_paths(inputs)
    quality = int((options or {}).get("quality", 82))
    output_dir = Path((options or {}).get("output_dir", paths[0].parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    try:
        for index, path in enumerate(paths):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            with Image.open(path) as image:
                rgb = image.convert("RGB")
                output = output_dir / f"{path.stem}_compressed.jpg"
                counter = 1
                while output.exists():
                    output = output_dir / f"{path.stem}_compressed_{counter}.jpg"
                    counter += 1
                rgb.save(output, format="JPEG", quality=quality, optimize=True)
            outputs.append(output)
            if progress_cb:
                progress_cb((index + 1) / len(paths) * 100, f"Compressed {path.name}")
    except InterruptedError:
        cleanup_paths(outputs)
        raise
    return outputs


def resize_image(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    paths = _image_paths(inputs)
    max_width = int((options or {}).get("width", 1600))
    max_height = int((options or {}).get("height", 1600))
    output_dir = Path((options or {}).get("output_dir", paths[0].parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    try:
        for index, path in enumerate(paths):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            with Image.open(path) as image:
                copy = image.copy()
                copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                output = output_dir / f"{path.stem}_resized.jpg"
                counter = 1
                while output.exists():
                    output = output_dir / f"{path.stem}_resized_{counter}.jpg"
                    counter += 1
                copy.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
            outputs.append(output)
            if progress_cb:
                progress_cb((index + 1) / len(paths) * 100, f"Resized {path.name}")
    except InterruptedError:
        cleanup_paths(outputs)
        raise
    return outputs


def pdf_to_images(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    source = ensure_pdf_file(inputs[0])
    output_dir = Path((options or {}).get("output_dir", source.parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dpi = int((options or {}).get("dpi", 150))
    document = fitz.open(source)
    outputs = []
    try:
        for index, page in enumerate(document):
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Cancelled.")
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            output = output_dir / f"{source.stem}_page_{index + 1}.png"
            pixmap.save(output)
            outputs.append(output)
            if progress_cb:
                progress_cb((index + 1) / max(document.page_count, 1) * 100, f"Rendered page {index + 1}")
    except InterruptedError:
        cleanup_paths(outputs)
        raise
    finally:
        document.close()
    return outputs


def remove_background(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    """Remove a connected near-uniform background starting from image edges.

    This deliberately avoids claiming AI segmentation. It works best on products,
    logos, and portraits photographed against a clean solid or near-solid backdrop.
    """
    paths = _image_paths(inputs)
    tolerance = max(1, min(100, int((options or {}).get("tolerance", 32))))
    output_dir = Path((options or {}).get("output_dir", paths[0].parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = source.convert("RGBA")
            pixels = image.load()
            width, height = image.size
            samples = [
                pixels[0, 0][:3],
                pixels[width - 1, 0][:3],
                pixels[0, height - 1][:3],
                pixels[width - 1, height - 1][:3],
            ]
            background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))
            visited = bytearray(width * height)
            queue = deque()

            for x in range(width):
                queue.extend(((x, 0), (x, height - 1)))
            for y in range(height):
                queue.extend(((0, y), (width - 1, y)))

            while queue:
                x, y = queue.popleft()
                position = y * width + x
                if visited[position]:
                    continue
                visited[position] = 1
                pixel = pixels[x, y]
                distance = sum(abs(pixel[channel] - background[channel]) for channel in range(3)) / 3
                if distance > tolerance:
                    continue
                pixels[x, y] = (pixel[0], pixel[1], pixel[2], 0)
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < width and 0 <= ny < height:
                        queue.append((nx, ny))

            output = output_dir / f"{path.stem}_no_bg.png"
            counter = 1
            while output.exists():
                output = output_dir / f"{path.stem}_no_bg_{counter}.png"
                counter += 1
            image.save(output, format="PNG", optimize=True)
        outputs.append(output)
        if progress_cb:
            progress_cb((index + 1) / len(paths) * 100, f"Removed background from {path.name}")
    return outputs


def transform_image(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    paths = _image_paths(inputs)
    operation = (options or {}).get("operation", "rotate-right")
    output_dir = Path((options or {}).get("output_dir", paths[0].parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = source.convert("RGBA")
            if operation == "rotate-left":
                image = image.rotate(90, expand=True)
            elif operation == "rotate-right":
                image = image.rotate(-90, expand=True)
            elif operation == "flip-horizontal":
                image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            elif operation == "flip-vertical":
                image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            elif operation == "grayscale":
                image = image.convert("L").convert("RGBA")
            else:
                raise ValueError(f"Unsupported image transform: {operation}")
            output = output_dir / f"{path.stem}_{operation.replace('-', '_')}.png"
            counter = 1
            while output.exists():
                output = output_dir / f"{path.stem}_{operation.replace('-', '_')}_{counter}.png"
                counter += 1
            image.save(output, format="PNG", optimize=True)
        outputs.append(output)
        if progress_cb:
            progress_cb((index + 1) / len(paths) * 100, f"Transformed {path.name}")
    return outputs


def crop_to_content(inputs, options=None, progress_cb=None, cancel_event=None) -> list[Path]:
    paths = _image_paths(inputs)
    output_dir = Path((options or {}).get("output_dir", paths[0].parent)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = source.convert("RGBA")
            alpha_bbox = image.getchannel("A").getbbox()
            bbox = alpha_bbox or image.getbbox()
            cropped = image.crop(bbox) if bbox else image
            output = output_dir / f"{path.stem}_cropped.png"
            counter = 1
            while output.exists():
                output = output_dir / f"{path.stem}_cropped_{counter}.png"
                counter += 1
            cropped.save(output, format="PNG", optimize=True)
        outputs.append(output)
        if progress_cb:
            progress_cb((index + 1) / len(paths) * 100, f"Cropped {path.name}")
    return outputs
