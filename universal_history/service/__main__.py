"""
CLI entry for the Agent API + web frontend server.

Usage:
    python -m universal_history.service [--host 127.0.0.1] [--port 8000]
                                        [file1.his file2.uh.json ...]

Loads the given history files (`.his` via HisFileAdapter, `.json` via
JsonFileAdapter) into one Workspace; serves the REST/WebSocket Agent API at
/api/* and /ws, and the web frontend (service/web/) at /.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from universal_history.adapters import HisFileAdapter, JsonFileAdapter
from universal_history.models import Workspace
from universal_history.service.agent_api import create_app
from universal_history.service.file_library import AllowedFileLibrary

if getattr(sys, "frozen", False):
    # PyInstaller bundle: data files live under sys._MEIPASS (the _internal dir).
    _WEB_DIR = Path(sys._MEIPASS) / "universal_history" / "service" / "web"
else:
    _WEB_DIR = Path(__file__).resolve().parent / "web"


def build_workspace(paths: list[str]) -> tuple[Workspace, dict[str, Path]]:
    workspace = Workspace()
    his = HisFileAdapter()
    js = JsonFileAdapter()
    source_paths = {}
    for p in paths:
        if p.endswith(".json"):
            events = js.load_file(p)
        else:
            events = his.load_file(p)
        workspace.load_events(events)
        resolved = Path(p).resolve()
        for source in {event.source for event in events}:
            source_paths[source] = resolved
    return workspace, source_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="universal_history.service")
    parser.add_argument("files", nargs="*", help=".his / .uh.json files to load")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--allow-root",
        action="append",
        default=[],
        metavar="PATH",
        help="Server file or directory exposed to the web file panel",
    )
    args = parser.parse_args(argv)

    workspace, source_paths = build_workspace(list(args.files))
    allowed_roots = [Path(path) for path in args.allow_root]
    allowed_roots.extend(Path(path) for path in args.files)
    file_library = AllowedFileLibrary(allowed_roots)
    for path in args.files:
        file_library.mark_loaded_path(path)
    app = create_app(workspace, file_library=file_library)
    app.state.source_paths.update(source_paths)
    for path in source_paths.values():
        app.state.file_fingerprints.remember(str(path))
    if _WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True),
                  name="web")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
