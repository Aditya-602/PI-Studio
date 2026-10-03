from __future__ import annotations

from pathlib import Path

import fitz

from pdf_toolkit.engine.compress import run as compress_run
from pdf_toolkit.engine.compare import run as compare_run
from pdf_toolkit.engine.extract import run as extract_run
from pdf_toolkit.engine.protect import run as protect_run
from pdf_toolkit.engine.remove_pages import run as remove_pages_run
from pdf_toolkit.engine.reorder import run as reorder_run
from pdf_toolkit.engine.remove_metadata import run as remove_metadata_run
from pdf_toolkit.engine.unlock import run as unlock_run
from pdf_toolkit.engine.watermark import run as watermark_run
from pdf_toolkit.engine.page_numbers import run as page_numbers_run
from pdf_toolkit.engine.repair import run as repair_run
from pdf_toolkit.engine.redact import run as redact_run
from pdf_toolkit.engine.form_fields import run as form_fields_run
from pdf_toolkit.engine.merge import run as merge_run
from pdf_toolkit.engine.rotate import run as rotate_run
from pdf_toolkit.engine.image_tools import (
    compress_image,
    crop_to_content,
    images_to_pdf,
    pdf_to_images,
    remove_background,
    resize_image,
    transform_image,
)
from PIL import Image
from pdf_toolkit.validation import validate_inputs, validate_output_directory
from pdf_toolkit.preferences import Preferences


def _make_pdf(path: Path, pages: int = 2) -> None:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), "Test PDF")
    doc.save(path)
    doc.close()


def test_merge_pdf(tmp_path):
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    _make_pdf(first)
    _make_pdf(second)

    outputs = merge_run([first, second], {"pages": []})

    assert len(outputs) == 1
    assert outputs[0].exists()
    out_doc = fitz.open(outputs[0])
    assert out_doc.page_count == 4
    out_doc.close()


def test_merge_pdf_respects_output_directory(tmp_path):
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    destination = tmp_path / "exports"
    _make_pdf(first)
    _make_pdf(second)

    outputs = merge_run([first, second], {"pages": [], "output_dir": str(destination)})

    assert outputs[0].parent == destination
    assert outputs[0].exists()


def test_rotate_pdf(tmp_path):
    source = tmp_path / "rotate.pdf"
    _make_pdf(source)

    outputs = rotate_run([source], {"angle": 90})

    assert outputs[0].exists()
    out_doc = fitz.open(outputs[0])
    assert out_doc.page_count == 2
    out_doc.close()


def test_compress_pdf(tmp_path):
    source = tmp_path / "compress.pdf"
    _make_pdf(source)

    outputs = compress_run([source], {"level": "Recommended"})

    assert outputs[0].exists()
    out_doc = fitz.open(outputs[0])
    assert out_doc.page_count == 2
    assert "Test PDF" in "".join(page.get_text() for page in out_doc)
    out_doc.close()


def test_compare_pdfs(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _make_pdf(first, pages=2)
    document = fitz.open()
    for text in ("Test PDF", "Changed PDF", "Extra page"):
        document.new_page().insert_text((72, 72), text)
    document.save(second)
    document.close()

    output = compare_run([first, second], {"output_dir": str(tmp_path / "comparison")})[0]
    report = output.read_text(encoding="utf-8")
    assert "PAGES A: 2" in report
    assert "PAGES B: 3" in report
    assert "DIFFERING PAGES: 2" in report
    assert "Changed PDF" in report


def test_extract_pages(tmp_path):
    source = tmp_path / "extract.pdf"
    _make_pdf(source, pages=4)

    outputs = extract_run([source], {"pages": "1, 3-4", "output_dir": str(tmp_path / "extracted")})

    assert outputs[0].exists()
    out_doc = fitz.open(outputs[0])
    assert out_doc.page_count == 3
    assert "Test PDF" in "".join(page.get_text() for page in out_doc)
    out_doc.close()


def test_remove_pages(tmp_path):
    source = tmp_path / "remove.pdf"
    _make_pdf(source, pages=4)

    outputs = remove_pages_run([source], {"pages": "2, 4", "output_dir": str(tmp_path / "remaining")})

    out_doc = fitz.open(outputs[0])
    assert out_doc.page_count == 2
    out_doc.close()

    try:
        remove_pages_run([source], {"pages": "1-4"})
    except ValueError as exc:
        assert "at least one page" in str(exc).lower()
    else:
        raise AssertionError("Removing every page should be rejected")


def test_reorder_pdf(tmp_path):
    source = tmp_path / "reorder.pdf"
    document = fitz.open()
    for text in ("FIRST", "SECOND", "THIRD"):
        document.new_page().insert_text((72, 72), text)
    document.save(source)
    document.close()

    output = reorder_run(
        [source],
        {"order": [2, 0, 1], "output_dir": str(tmp_path / "reordered")},
    )[0]
    reordered = fitz.open(output)
    assert [page.get_text().strip() for page in reordered] == [
        "THIRD",
        "FIRST",
        "SECOND",
    ]
    reordered.close()


def test_remove_metadata(tmp_path):
    source = tmp_path / "metadata.pdf"
    document = fitz.open()
    document.set_metadata({"title": "Private title", "author": "Private author"})
    document.new_page().insert_text((72, 72), "Visible content")
    document.save(source)
    document.close()

    output = remove_metadata_run([source], {"output_dir": str(tmp_path / "clean")})[0]
    cleaned = fitz.open(output)
    metadata = cleaned.metadata
    assert metadata["title"] == ""
    assert metadata["author"] == ""
    assert "Visible content" in cleaned[0].get_text()
    cleaned.close()


def test_protect_pdf_requires_password_and_encrypts(tmp_path):
    source = tmp_path / "protect.pdf"
    _make_pdf(source)

    outputs = protect_run(
        [source],
        {"user_password": "safe-pass", "owner_password": "safe-pass", "output_dir": str(tmp_path / "protected")},
    )
    document = fitz.open(outputs[0])
    assert document.is_encrypted
    assert document.authenticate("safe-pass")
    document.close()

    try:
        protect_run([source], {"user_password": "x"})
    except ValueError as exc:
        assert "4 characters" in str(exc)
    else:
        raise AssertionError("Short passwords should be rejected")


def test_unlock_pdf_requires_correct_password(tmp_path):
    source = tmp_path / "locked.pdf"
    _make_pdf(source)
    protected = protect_run([source], {"user_password": "safe-pass", "owner_password": "safe-pass"})[0]

    unlocked = unlock_run([protected], {"password": "safe-pass", "output_dir": str(tmp_path / "unlocked")})[0]
    document = fitz.open(unlocked)
    assert not document.is_encrypted
    assert "Test PDF" in document[0].get_text()
    document.close()

    try:
        unlock_run([protected], {"password": "wrong"})
    except ValueError as exc:
        assert "incorrect" in str(exc).lower()
    else:
        raise AssertionError("Incorrect passwords should be rejected")


def test_watermark_pdf(tmp_path):
    source = tmp_path / "watermark.pdf"
    _make_pdf(source, pages=2)
    output = watermark_run(
        [source],
        {"text": "CONFIDENTIAL", "opacity": 35, "rotation": 90, "output_dir": str(tmp_path / "marked")},
    )[0]
    document = fitz.open(output)
    assert document.page_count == 2
    assert "CONFIDENTIAL" in document[0].get_text()
    document.close()


def test_page_numbers(tmp_path):
    source = tmp_path / "numbered.pdf"
    _make_pdf(source, pages=3)
    output = page_numbers_run(
        [source],
        {"start_number": 10, "position": "bottom-right", "output_dir": str(tmp_path / "numbered")},
    )[0]
    document = fitz.open(output)
    assert document.page_count == 3
    assert "10" in document[0].get_text()
    assert "12" in document[2].get_text()
    document.close()


def test_repair_pdf_preserves_pages_and_text(tmp_path):
    source = tmp_path / "repair.pdf"
    _make_pdf(source, pages=3)
    output = repair_run([source], {"output_dir": str(tmp_path / "repaired")})[0]
    document = fitz.open(output)
    assert document.page_count == 3
    assert "Test PDF" in document[1].get_text()
    document.close()


def test_redact_pdf_removes_matching_text(tmp_path):
    source = tmp_path / "redact.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Public CONFIDENTIAL content")
    document.save(source)
    document.close()

    output = redact_run([source], {"terms": "CONFIDENTIAL", "output_dir": str(tmp_path / "redacted")})[0]
    redacted = fitz.open(output)
    text = redacted[0].get_text()
    assert "CONFIDENTIAL" not in text
    assert "Public" in text
    redacted.close()


def test_form_field_inventory_without_fields(tmp_path):
    source = tmp_path / "form.pdf"
    _make_pdf(source)
    output = form_fields_run([source], {"output_dir": str(tmp_path / "fields")})[0]
    report = output.read_text(encoding="utf-8")
    assert "FIELDS: 0" in report
    assert "NO INTERACTIVE FORM FIELDS FOUND" in report


def test_image_tools(tmp_path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (320, 240), "red").save(first)
    Image.new("RGB", (160, 120), "blue").save(second)

    pdf = images_to_pdf([first, second], {"output_dir": str(tmp_path / "pdf")})[0]
    assert pdf.exists()
    pages = pdf_to_images([pdf], {"output_dir": str(tmp_path / "pages")})
    assert len(pages) == 2
    assert all(path.exists() for path in pages)
    assert compress_image([first], {"output_dir": str(tmp_path / "compressed")})[0].exists()
    assert resize_image([first], {"width": 80, "height": 80, "output_dir": str(tmp_path / "resized")})[0].exists()


def test_background_and_image_transforms(tmp_path):
    source = tmp_path / "subject.png"
    image = Image.new("RGB", (40, 40), "white")
    for x in range(12, 28):
        for y in range(12, 28):
            image.putpixel((x, y), (220, 20, 20))
    image.save(source)

    transparent = remove_background([source], {"output_dir": str(tmp_path / "transparent")})[0]
    assert transparent.exists()
    assert Image.open(transparent).getpixel((0, 0))[3] == 0
    assert transform_image([source], {"operation": "rotate-right", "output_dir": str(tmp_path / "rotated")})[0].exists()
    assert crop_to_content([transparent], {"output_dir": str(tmp_path / "cropped")})[0].exists()


def test_input_and_output_validation(tmp_path):
    image = tmp_path / "valid.png"
    Image.new("RGB", (8, 8), "white").save(image)
    validate_inputs([image], "image")
    destination = validate_output_directory(tmp_path / "exports")
    assert destination is not None and destination.exists()

    empty = tmp_path / "empty.png"
    empty.touch()
    try:
        validate_inputs([empty], "image")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Empty input should be rejected")


def test_validation_rejects_malformed_pdf(tmp_path):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"%PDF-not-a-valid-document")

    try:
        validate_inputs([source], "pdf")
    except ValueError as exc:
        assert "could not be opened" in str(exc).lower()
    else:
        raise AssertionError("Malformed PDFs should be rejected")


def test_validation_rejects_malformed_image(tmp_path):
    source = tmp_path / "broken.png"
    source.write_bytes(b"not an image")

    try:
        validate_inputs([source], "image")
    except ValueError as exc:
        assert "could not be opened" in str(exc).lower()
    else:
        raise AssertionError("Malformed images should be rejected")


def test_validation_rejects_output_path_that_is_a_file(tmp_path):
    output_path = tmp_path / "not-a-directory"
    output_path.write_text("occupied", encoding="utf-8")

    try:
        validate_output_directory(output_path)
    except ValueError as exc:
        assert "not a directory" in str(exc).lower()
    else:
        raise AssertionError("A file cannot be used as an output directory")


def test_validation_rejects_insufficient_output_space(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import pdf_toolkit.validation as validation

    monkeypatch.setattr(
        validation.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=90, free=10),
    )
    try:
        validate_output_directory(tmp_path, required_bytes=20)
    except ValueError as exc:
        assert "not enough free space" in str(exc).lower()
    else:
        raise AssertionError("Insufficient output space should be rejected")


def test_input_limits_reject_oversized_pdf(tmp_path):
    source = tmp_path / "large.pdf"
    _make_pdf(source)
    import pdf_toolkit.validation as validation

    original_limit = validation.MAX_INPUT_BYTES
    validation.MAX_INPUT_BYTES = 1
    try:
        validate_inputs([source], "pdf")
    except ValueError as exc:
        assert "too large" in str(exc).lower()
    else:
        raise AssertionError("Oversized PDFs should be rejected")
    finally:
        validation.MAX_INPUT_BYTES = original_limit


def test_input_limits_reject_large_pdf_page_count(tmp_path, monkeypatch):
    source = tmp_path / "many-pages.pdf"
    _make_pdf(source, pages=2)
    monkeypatch.setattr("pdf_toolkit.validation.MAX_PDF_PAGES", 1)
    try:
        validate_inputs([source], "pdf")
    except ValueError as exc:
        assert "too many pages" in str(exc).lower()
    else:
        raise AssertionError("PDFs over the page limit should be rejected")


def test_input_limits_reject_large_images(tmp_path, monkeypatch):
    source = tmp_path / "large.png"
    Image.new("RGB", (20, 20), "white").save(source)
    monkeypatch.setattr("pdf_toolkit.validation.MAX_IMAGE_PIXELS", 100)
    try:
        validate_inputs([source], "image")
    except ValueError as exc:
        assert "dimensions are too large" in str(exc).lower()
    else:
        raise AssertionError("Oversized images should be rejected")


def test_split_cancellation_cleans_partial_outputs(tmp_path):
    source = tmp_path / "many.pdf"
    _make_pdf(source, pages=4)
    output_dir = tmp_path / "cancelled"

    class CancelAfterFirst:
        def __init__(self):
            self.called = False

        def is_set(self):
            if self.called:
                return True
            self.called = True
            return False

    try:
        from pdf_toolkit.engine.split import run as split_run

        split_run(
            [source],
            {"mode": "chunks", "chunk_size": 1, "output_dir": str(output_dir)},
            cancel_event=CancelAfterFirst(),
        )
    except InterruptedError:
        pass
    else:
        raise AssertionError("Cancellation should interrupt splitting")
    assert not list(output_dir.glob("*.pdf")) if output_dir.exists() else True


def test_preferences_round_trip(tmp_path, monkeypatch):
    preferences_path = tmp_path / "preferences.json"
    preferences = Preferences(preferences_path)
    preferences.set("last_output_dir", str(tmp_path))
    loaded = Preferences(preferences_path)
    assert loaded.get("last_output_dir") == str(tmp_path)
