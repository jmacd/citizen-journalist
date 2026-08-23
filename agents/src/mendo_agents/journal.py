"""Append-only run manifests and event journals."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


class RunJournal:
    def __init__(self, run_root: Path, run_id: str) -> None:
        self.directory = run_root / run_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / "events.jsonl"
        self.manifest_path = self.directory / "manifest.json"

    def write_manifest(self, manifest: dict[str, Any]) -> None:
        if self.manifest_path.exists():
            raise FileExistsError(f"Run manifest already exists: {self.manifest_path}")
        self.manifest_path.write_text(
            json.dumps(manifest, default=_json_default, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    def append(self, event_type: str, data: Any) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "data": data,
        }
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(record, default=_json_default, sort_keys=True) + "\n"
            )
