"""
Event / EventIndex / Workspace

The new data model for UniversalHistory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from universal_history.chrono.jdn_timestamp import JDNTimestamp


@dataclass
class Event:
    """
    A single historical event / record.

    Time is stored as JDNTimestamp (microsecond precision, proleptic Gregorian,
    astronomical year numbering where year 0 = 1 BC).

    Labels are arbitrary key -> [value, ...] pairs. The five canonical labels
    are time, location, people, organization, event.
    """

    uuid: str
    source: str
    since: Optional[JDNTimestamp]
    until: Optional[JDNTimestamp]
    focus_label: str
    labels: Dict[str, List[str]] = field(default_factory=dict)

    def is_point_event(self) -> bool:
        """True if this event represents a single moment in time."""
        return self.since is not None and self.until is not None and self.since == self.until

    def is_period_event(self) -> bool:
        """True if this event spans a non-zero duration."""
        return self.since is not None and self.until is not None and self.since != self.until

    def has_time(self) -> bool:
        return self.since is not None and self.until is not None

    def title(self) -> str:
        return self.first_tag("title")

    def brief(self) -> str:
        return self.first_tag("brief")

    def event_text(self) -> str:
        return self.first_tag("event")

    def time_text(self) -> str:
        return ", ".join(self.labels.get("time", []))

    def abstract(self, max_length: int = 50) -> str:
        """Short display text: title > brief > event."""
        text = self.title() or self.brief() or self.event_text()
        text = text.strip().replace("\n", " ")
        return text if len(text) <= max_length else text[: max_length - 1] + "…"

    def first_tag(self, label: str) -> str:
        tags = self.labels.get(label, [])
        return tags[0] if tags else ""

    def all_tags(self, label: str) -> List[str]:
        return list(self.labels.get(label, []))

    def to_index(self) -> EventIndex:
        return EventIndex(
            uuid=self.uuid,
            source=self.source,
            since=self.since,
            until=self.until,
            abstract=self.abstract(),
        )


@dataclass
class EventIndex:
    """
    Lightweight display index of an Event.

    Used when only a summary is needed (e.g. network transmission, large
    lists, timeline rendering before detail view).
    """

    uuid: str
    source: str
    since: Optional[JDNTimestamp]
    until: Optional[JDNTimestamp]
    abstract: str

    def is_point_event(self) -> bool:
        return self.since is not None and self.until is not None and self.since == self.until


class Workspace(QObject):
    """
    In-memory collection of loaded Events grouped by their source.

    This corresponds to the old `History` class, but is decoupled from any
    specific loader or UI. It emits signals when events change so that views
    can update in real time.
    """

    event_added = pyqtSignal(Event)
    event_updated = pyqtSignal(Event)
    event_removed = pyqtSignal(str)  # uuid
    source_loaded = pyqtSignal(str)  # source path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_events: Dict[str, List[Event]] = {}

    # ------------------------------------------------------------------
    # Basic management
    # ------------------------------------------------------------------

    def sources(self) -> List[str]:
        return list(self._source_events.keys())

    def events(self, source: Optional[str] = None) -> List[Event]:
        if source is None:
            return [e for events in self._source_events.values() for e in events]
        return list(self._source_events.get(source, []))

    def indexes(self, source: Optional[str] = None) -> List[EventIndex]:
        return [e.to_index() for e in self.events(source)]

    def add(self, event: Event) -> None:
        if not event.source:
            raise ValueError("Event source cannot be empty")
        self._source_events.setdefault(event.source, [])
        self._source_events[event.source].append(event)
        self.event_added.emit(event)

    def upsert(self, event: Event) -> None:
        """Replace an existing event with the same uuid, or append."""
        existing = self.remove(event.uuid)
        self._add_silent(event)
        if existing is not None:
            self.event_updated.emit(event)
        else:
            self.event_added.emit(event)

    def remove(self, uuid: str) -> Optional[Event]:
        for source, events in self._source_events.items():
            for i, e in enumerate(events):
                if e.uuid == uuid:
                    removed = events.pop(i)
                    if not events:
                        self._source_events.pop(source, None)
                    self.event_removed.emit(uuid)
                    return removed
        return None

    def remove_source(self, source: str) -> None:
        events = self._source_events.pop(source, [])
        for e in events:
            self.event_removed.emit(e.uuid)

    def clear(self) -> None:
        sources = list(self._source_events.keys())
        self._source_events.clear()
        for s in sources:
            self.source_loaded.emit(s)

    def get_by_uuid(self, uuid: str) -> Optional[Event]:
        for e in self.events():
            if e.uuid == uuid:
                return e
        return None

    # ------------------------------------------------------------------
    # Selection / filtering
    # ------------------------------------------------------------------

    def select(
        self,
        *,
        sources: Optional[List[str]] = None,
        focus_label: Optional[str] = None,
        include_labels: Optional[Dict[str, List[str]]] = None,
        include_all: bool = True,
        exclude_labels: Optional[Dict[str, List[str]]] = None,
        exclude_any: bool = True,
        time_range: Optional[tuple] = None,
    ) -> List[Event]:
        """
        Flexible filter over the workspace.

        Parameters mirror the old `History.select_records()` behaviour.
        """
        results: List[Event] = []

        source_set = set(sources) if sources else None
        include_labels = include_labels or {}
        exclude_labels = exclude_labels or {}

        for source, events in self._source_events.items():
            if source_set is not None and source not in source_set:
                continue
            for event in events:
                if focus_label is not None and event.focus_label != focus_label:
                    continue
                if include_labels and not self._match_labels(
                    event.labels, include_labels, match_all=include_all
                ):
                    continue
                if exclude_labels and self._match_labels(
                    event.labels, exclude_labels, match_all=not exclude_any
                ):
                    continue
                if time_range is not None:
                    lo, hi = time_range
                    if event.until is None or event.since is None:
                        continue
                    if not (event.since <= hi and event.until >= lo):
                        continue
                results.append(event)

        return results

    @staticmethod
    def _match_labels(
        labels: Dict[str, List[str]],
        expected: Dict[str, List[str]],
        match_all: bool,
    ) -> bool:
        if not expected:
            return True

        for key, wanted in expected.items():
            actual = set(labels.get(key, []))
            if match_all:
                if not wanted or not all(w in actual for w in wanted):
                    return False
            else:
                if any(w in actual for w in wanted):
                    return True

        return match_all

    # ------------------------------------------------------------------
    # Load via adapter
    # ------------------------------------------------------------------

    def load(self, adapter_result: Dict[str, List[Event]]) -> None:
        """Merge adapter output (source -> events) into the workspace."""
        for source, events in adapter_result.items():
            self.remove_source(source)
            for event in events:
                self._add_silent(event)
            self.source_loaded.emit(source)

    def load_events(self, events: List[Event]) -> None:
        """Merge a flat list of events, grouping by event.source."""
        by_source: Dict[str, List[Event]] = {}
        for event in events:
            by_source.setdefault(event.source, []).append(event)
        self.load(by_source)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_silent(self, event: Event) -> None:
        """Add without emitting (used by upsert/load)."""
        if not event.source:
            raise ValueError("Event source cannot be empty")
        self._source_events.setdefault(event.source, [])
        self._source_events[event.source].append(event)
