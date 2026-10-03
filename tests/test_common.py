from pathlib import Path

import pytest

from pdf_toolkit.engine.common import atomic_pdf_save


def test_atomic_pdf_save_removes_temporary_file_on_failure(tmp_path):
    destination = tmp_path / "result.pdf"
    destination.write_bytes(b"previous output")

    class FailingDocument:
        def save(self, path, **kwargs):
            Path(path).write_bytes(b"partial")
            raise RuntimeError("save failed")

    with pytest.raises(RuntimeError, match="save failed"):
        atomic_pdf_save(FailingDocument(), destination)

    assert destination.read_bytes() == b"previous output"
    assert not list(tmp_path.glob(".*.tmp.pdf"))
