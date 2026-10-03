from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Preferences:
    def __init__(self, path: Path | None = None):
        self.path = path or (Path.home() / ".pdf_toolkit" / "preferences.json")
        self.values: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            self.values = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            self.values = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
        temporary.replace(self.path)
