"""
HisFileAdapter

Load legacy `.his` files / depots / directories and convert them into the new
UniversalHistory Event model.

The .his parser is the native port in `universal_history.parsing` (behaviour
compatible with History's own parser); this adapter only maps the resulting
HistoryRecords to Event instances using JDNTimestamp.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from universal_history.parsing import (
    HistoryRecord,
    HistoryRecordLoader,
    LabelTagParser,
)

from universal_history.adapters.fingerprint import FileFingerprints
from universal_history.models.event import Event
from universal_history.chrono.history_time_adapter import history_record_time_range


# Labels that are stored as dedicated Event fields rather than generic labels.
_RESERVED_LABELS = {"uuid", "since", "until"}


class SaveConflictError(RuntimeError):
    """
    Raised when saving a .his file whose on-disk content changed since this
    adapter last loaded/saved it (known-issues #6: was last-writer-wins).

    Catch this in the UI, ask the user, and retry with ``force=True`` to
    overwrite anyway.
    """


def _history_record_to_event(record: HistoryRecord) -> Event:
    """Convert a parsed HistoryRecord into an Event."""
    since, until = history_record_time_range(record)

    labels: Dict[str, List[str]] = {}
    for label in record.get_labels():
        if label in _RESERVED_LABELS:
            continue
        labels[label] = list(record.get_tags(label))

    return Event(
        uuid=record.uuid(),
        source=record.source(),
        since=since,
        until=until,
        focus_label=record.get_focus_label() or "event",
        labels=labels,
    )


class HisFileAdapter:
    """
    Adapter for the legacy `.his` text format.

    A single instance is bound to a depot root. All relative paths are resolved
    against this root, matching History's own behaviour.
    """

    def __init__(self, depot_root: Optional[Path] = None):
        if depot_root is None:
            depot_root = Path(HistoryRecordLoader.get_local_depot_root())
        self.depot_root = Path(depot_root)
        # absolute path -> sha256 of file content at last load/save
        self._fingerprints = FileFingerprints()

    # ------------------------------------------------------------------
    # Load methods
    # ------------------------------------------------------------------

    def load_file(self, path: str) -> List[Event]:
        """Load a single .his file and return a list of Events."""
        self._remember_fingerprint(path)
        result = HistoryRecordLoader.from_file(path)
        events: List[Event] = []
        for records in result.values():
            events.extend(_history_record_to_event(r) for r in records)
        return events

    def load_source(self, source: str) -> List[Event]:
        """Load by source path (relative to depot root or absolute)."""
        if not HistoryRecordLoader.is_web_url(source):
            self._remember_fingerprint(HistoryRecordLoader.source_to_absolute_path(source))
        result = HistoryRecordLoader.from_source(source)
        events: List[Event] = []
        for records in result.values():
            events.extend(_history_record_to_event(r) for r in records)
        return events

    def load_depot(self, depot_name: str) -> Dict[str, List[Event]]:
        """Load an entire depot directory (e.g. 'example', 'China_CN')."""
        raw = HistoryRecordLoader.from_local_depot(depot_name)
        for path in raw.keys():
            self._remember_fingerprint(path)
        return self._convert_raw(raw)

    def load_directory(self, directory: str) -> Dict[str, List[Event]]:
        """Load all .his files under an arbitrary directory."""
        raw = HistoryRecordLoader.from_directory(directory)
        for path in raw.keys():
            self._remember_fingerprint(path)
        return self._convert_raw(raw)

    # ------------------------------------------------------------------
    # Save methods
    # ------------------------------------------------------------------

    def save_file(self, path: str, events: List[Event], force: bool = False) -> None:
        """
        Write a list of Events back to a .his file (format-compatible).

        Raises SaveConflictError when the file was previously loaded/saved by
        this adapter and its on-disk content has changed since. Pass
        ``force=True`` to overwrite anyway.
        """
        if not force and self._fingerprints.has_conflict(path):
            raise SaveConflictError(
                f"File changed on disk since it was loaded: {path}"
            )
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, "wt", encoding="utf-8") as f:
            for i, event in enumerate(events):
                if i > 0:
                    f.write("\n# ----------------------------------------------------------------------------------------------------------------------\n\n")
                f.write(self._event_to_his_text(event))
        self._remember_fingerprint(path)

    def save_workspace(self, workspace: "Workspace", source: str, path: str, force: bool = False) -> None:
        """Save all events belonging to a single workspace source."""
        self.save_file(path, workspace.events(source), force=force)

    # ------------------------------------------------------------------
    # Conflict-detection helpers
    # ------------------------------------------------------------------

    def _remember_fingerprint(self, path: str) -> None:
        self._fingerprints.remember(path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_raw(raw: Dict[str, List[HistoryRecord]]) -> Dict[str, List[Event]]:
        return {
            source: [_history_record_to_event(r) for r in records]
            for source, records in raw.items()
        }

    @staticmethod
    def _event_to_his_text(event: Event) -> str:
        """Serialize a single Event to the legacy .his text format."""
        focus = event.focus_label or "event"

        # Build ordered label list: canonical priority labels first,
        # then arbitrary labels, then title/brief/event tail labels,
        # with the focus label always last.
        priority = ["time", "people", "location", "organization"]
        tail = ["title", "brief", "event"]
        existing = set(event.labels.keys())

        ordered = [l for l in priority if l in existing]
        ordered += sorted(existing - set(priority) - set(tail) - {focus})
        ordered += [l for l in tail if l in existing and l != focus]
        if focus in existing:
            ordered.append(focus)

        lines: List[str] = []
        lines.append(f"[START]: {focus}")
        lines.append("")
        lines.append(_label_line("uuid", [event.uuid]))

        for label in ordered:
            if label == focus:
                continue
            lines.append(_label_line(label, event.labels[label]))

        # Focus label content (or 'end' if empty)
        focus_tags = event.labels.get(focus, [])
        if not focus_tags or not any(t.strip() for t in focus_tags):
            lines.append(_label_line(focus, ["end"]))
        else:
            lines.append(_label_line(focus, focus_tags))

        return "\n".join(lines) + "\n"


def _label_line(label: str, tags: List[str]) -> str:
    """Render one label line, wrapping multi-line or token-rich text."""
    # The ported parser's persistence helper guarantees format compatibility.
    text = LabelTagParser.tags_to_text(tags, persistence=True)
    return f"{label}: {text}"
