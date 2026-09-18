"""
Agent API — REST + WebSocket backend over the Workspace model.

Wire format reuses the ``universal-history/v1`` JSON schema (timestamps are
exact JDN microsecond integers). All Workspace mutations broadcast to every
connected WebSocket client, so web frontends and agents stay in sync.

Run: ``python -m universal_history.service [file.his|file.uh.json ...]``
"""

from __future__ import annotations

import asyncio
import json
import uuid as uuid_module
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from universal_history.adapters import event_from_dict, event_to_dict
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.time_utils import parse_time_text
from universal_history.models import Event, Workspace


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------

class EventIn(BaseModel):
    """Create/update payload. uuid optional on create (server assigns)."""
    uuid: Optional[str] = None
    source: str
    since: Optional[int] = None  # JDN microseconds
    until: Optional[int] = None
    focus_label: str = "event"
    labels: dict = {}


class EventOut(BaseModel):
    uuid: str
    source: str
    since: Optional[int]
    until: Optional[int]
    focus_label: str
    labels: dict


class IndexOut(BaseModel):
    """EventIndex wire form: pointer + time range + abstract."""
    uuid: str
    source: str
    since: Optional[int]
    until: Optional[int]
    abstract: str


class SourceOut(BaseModel):
    source: str
    event_count: int


# ----------------------------------------------------------------------
# WebSocket broadcast hub
# ----------------------------------------------------------------------

class BroadcastHub:
    """Fan-out of Workspace change notifications to WebSocket clients."""

    def __init__(self):
        self._queues: List[asyncio.Queue] = []

    def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._queues.append(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        if q in self._queues:
            self._queues.remove(q)

    def notify(self, payload: dict) -> None:
        for q in list(self._queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # slow consumer drops rather than blocking the model


def _index_to_dict(index) -> dict:
    return {
        "uuid": index.uuid,
        "source": index.source,
        "since": index.since.value if index.since is not None else None,
        "until": index.until.value if index.until is not None else None,
        "abstract": index.abstract,
    }


# ----------------------------------------------------------------------
# App factory
# ----------------------------------------------------------------------

def create_app(workspace: Optional[Workspace] = None) -> FastAPI:
    workspace = workspace or Workspace()
    hub = BroadcastHub()

    app = FastAPI(title="UniversalHistory Agent API", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Wire model signals to broadcasts.
    def _broadcast_event(kind: str, event: Event):
        hub.notify({"type": kind, "event": event_to_dict(event)})

    workspace.event_added.connect(lambda e: _broadcast_event("event_added", e))
    workspace.event_updated.connect(lambda e: _broadcast_event("event_updated", e))
    workspace.event_removed.connect(
        lambda u: hub.notify({"type": "event_removed", "uuid": u})
    )
    workspace.source_loaded.connect(
        lambda s: hub.notify({"type": "source_loaded", "source": s})
    )
    workspace.source_removed.connect(
        lambda s: hub.notify({"type": "source_removed", "source": s})
    )

    # ------------------------------------------------------------------
    # REST
    # ------------------------------------------------------------------

    @app.get("/api/schema")
    def schema():
        """Self-description for agents/LLMs."""
        return {
            "format": "universal-history/v1",
            "time": "JDN microsecond integers; astronomical year numbering "
                    "(year 0 = 1 BC); null = no time",
            "endpoints": [
                "GET /api/sources",
                "GET /api/events?source=&time_from=&time_to=",
                "GET /api/events/{uuid}",
                "GET /api/parse_time?text=",
                "POST /api/events",
                "DELETE /api/events/{uuid}",
                "WS /ws (change notifications)",
            ],
        }

    @app.get("/api/sources", response_model=List[SourceOut])
    def list_sources():
        return [
            {"source": s, "event_count": len(workspace.events(s))}
            for s in workspace.sources()
        ]

    @app.get("/api/events", response_model=List[IndexOut])
    def list_events(source: Optional[str] = None,
                    focus_label: Optional[str] = None,
                    time_from: Optional[int] = None,
                    time_to: Optional[int] = None):
        time_range = None
        if time_from is not None or time_to is not None:
            time_range = (
                JDNTimestamp(time_from) if time_from is not None else None,
                JDNTimestamp(time_to) if time_to is not None else None,
            )
        events = workspace.select(
            sources=[source] if source else None,
            focus_label=focus_label,
            time_range=time_range,
        )
        return [_index_to_dict(e.to_index()) for e in events]

    @app.get("/api/events/{event_uuid}", response_model=EventOut)
    def get_event(event_uuid: str):
        event = workspace.get_by_uuid(event_uuid)
        if event is None:
            raise HTTPException(status_code=404, detail="event not found")
        return event_to_dict(event)

    @app.get("/api/parse_time")
    def parse_time(text: str):
        """Parse natural-language time text (server-side, same parser as the
        desktop app) into JDN microsecond endpoints for the web frontend."""
        since, until, _ = parse_time_text(text)
        return {
            "since": since.value if since is not None else None,
            "until": until.value if until is not None else None,
        }

    @app.post("/api/events", response_model=EventOut, status_code=201)
    def upsert_event(payload: EventIn):
        if not payload.source:
            raise HTTPException(status_code=400, detail="source is required")
        event = Event(
            uuid=payload.uuid or str(uuid_module.uuid4()),
            source=payload.source,
            since=JDNTimestamp(payload.since) if payload.since is not None else None,
            until=JDNTimestamp(payload.until) if payload.until is not None else None,
            focus_label=payload.focus_label or "event",
            labels={k: list(v) for k, v in payload.labels.items()},
        )
        try:
            workspace.upsert(event)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return event_to_dict(event)

    @app.delete("/api/events/{event_uuid}", status_code=204)
    def delete_event(event_uuid: str):
        if workspace.remove(event_uuid) is None:
            raise HTTPException(status_code=404, detail="event not found")

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    @app.websocket("/ws")
    async def ws(ws: WebSocket):
        await ws.accept()
        queue = hub.connect()
        try:
            await ws.send_text(json.dumps({
                "type": "hello",
                "sources": [s for s in workspace.sources()],
            }))
            while True:
                payload = await queue.get()
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            hub.disconnect(queue)

    app.state.workspace = workspace
    app.state.hub = hub
    return app
