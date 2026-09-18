"""
JsonFileAdapter — non-.his persistence (roadmap: JSON adapter).

Format ``universal-history/v1``: timestamps are stored as exact JDN
microsecond integers (never floats), so round-trips are loss-free across the
whole astronomical range — including deep-time and BCE values that ISO-8601
strings cannot represent.

The same schema doubles as the Agent API wire format (see ``service/``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from universal_history.adapters.fingerprint import FileFingerprints
from universal_history.adapters.his_adapter import SaveConflictError
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models.event import Event

FORMAT_ID = "universal-history/v1"


def event_to_dict(event: Event) -> dict:
    return {
        "uuid": event.uuid,
        "source": event.source,
        "since": event.since.value if event.since is not None else None,
        "until": event.until.value if event.until is not None else None,
        "focus_label": event.focus_label,
        "labels": {k: list(v) for k, v in event.labels.items()},
    }


def event_from_dict(data: dict) -> Event:
    since = data.get("since")
    until = data.get("until")
    return Event(
        uuid=data["uuid"],
        source=data.get("source", ""),
        since=JDNTimestamp(since) if since is not None else None,
        until=JDNTimestamp(until) if until is not None else None,
        focus_label=data.get("focus_label") or "event",
        labels={k: list(v) for k, v in (data.get("labels") or {}).items()},
    )


class JsonFileAdapter:
    """Load/save events as a single JSON document per source file."""

    def __init__(self):
        self._fingerprints = FileFingerprints()

    def load_file(self, path: str) -> List[Event]:
        self._fingerprints.remember(path)
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise OSError(f"Cannot read {path}: {e}") from e
        if not raw.strip():
            return []
        data = json.loads(raw)
        if isinstance(data, list):  # bare list shorthand
            events_raw = data
        elif isinstance(data, dict) and data.get("format") == FORMAT_ID:
            events_raw = data.get("events", [])
        else:
            raise ValueError(f"Not a {FORMAT_ID} file: {path}")
        return [event_from_dict(e) for e in events_raw]

    def save_file(self, path: str, events: List[Event], force: bool = False) -> None:
        """Write events as JSON; raises SaveConflictError on disk drift unless
        ``force=True`` (same contract as HisFileAdapter)."""
        if not force and self._fingerprints.has_conflict(path):
            raise SaveConflictError(
                f"File changed on disk since it was loaded: {path}"
            )
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "format": FORMAT_ID,
            "source": str(path),
            "events": [event_to_dict(e) for e in events],
        }
        path_obj.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._fingerprints.remember(path)

    def save_workspace(self, workspace: "Workspace", source: str, path: str,
                       force: bool = False) -> None:
        self.save_file(path, workspace.events(source), force=force)
