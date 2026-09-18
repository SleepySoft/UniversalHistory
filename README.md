# UniversalHistory

English | [中文](README.zh_CN.md)

A standard implementation of infinite historical time and a timeline viewer,
built on a single proleptic-Gregorian JDN timestamp model.

## Features

- **Unified time model**: microsecond-precision `JDNTimestamp` with astronomical
  year numbering (year 0 = 1 BC).
- **Legacy `.his` adapter**: loads and saves History-format files, converting
  natural-language time expressions to `JDNTimestamp`.
- **Timeline renderer**: PyQt6-based infinite zoom/pan timeline with automatic
  track layout for point and period events.
- **Multiple threads**: display any number of sources on the left/right sides of
  the axis; allocate side space proportionally via per-thread **share** (each
  side's shares always sum to 1); add threads from existing `.his` files,
  create new source files, or create empty threads and bind a source later.
- **Horizontal / vertical orientation**: toggle the time axis direction with
  `Ctrl+T`; threads keep their intuitive left/right placement.
- **Event editor**: edit time, location, people, organization, tags, title,
  brief, and event text; select the focus label. Dirty-flag save prompts on
  every flow; BCE-capable astronomical date picker for out-of-Qt-range dates.
- **Timeline-centric editing**: position-aware create (right-click prefills the
  clicked axis time), post-save reveal, click-to-expand details panel,
  non-modal side editor dock, and quick entry (title + time in one step).
- **Hover progress for period events**: the tooltip shows "Year N of M" at the
  cursor position.
- **i18n**: English source strings wrapped in `tr()`, JSON translation
  catalogs (`translations/zh_CN.json`); `--lang` / `UH_LANGUAGE`.
- **JSON persistence**: `JsonFileAdapter` (schema `universal-history/v1`)
  stores `since`/`until` as JDN microsecond integers.
- **Agent API**: FastAPI REST + WebSocket backend
  (`universal_history/service/`) exposing schema/sources/events queries,
  natural-language time parsing, event upsert/delete, and live Workspace
  signal broadcast.
- **Web frontend**: single-file canvas app (`service/web/index.html`)
  mirroring the native timeline design; its JS calendar math is verified
  point-for-point against the Python `JDNTimestamp`.
- **Filter dialog**: query the workspace by source, focus label, included/excluded
  tags, and time range; results reuse a single filter thread.

## Install

```bash
python -m pip install -r requirements.txt
```

Or install the project as an editable package (add `[service]` for the
Agent API / web frontend server):

```bash
python -m pip install -e .
python -m pip install -e .[service]
```

## Run

```bash
python -m universal_history
```

Or, after installation:

```bash
universal-history
```

Agent API + web frontend server:

```bash
python -m universal_history.service [--host 127.0.0.1] [--port 8000] [file1.his file2.json ...]
universal-history-server ../History/depot/example/example.his   # after install
```

## Packaging

PyInstaller specs live in `packaging/`:

```bash
pyinstaller packaging/universal_history.spec --distpath dist --workpath build -y  # desktop app
pyinstaller packaging/service.spec --distpath dist --workpath build -y            # API + web server
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
UniversalHistory/
├── pyproject.toml
├── requirements.txt
├── README.md
├── packaging/                # PyInstaller specs (desktop + server)
├── universal_history/          # main package
│   ├── __main__.py             # python -m universal_history
│   ├── main_window.py          # PyQt6 application entry point
│   ├── models/                 # Event, EventIndex, Workspace
│   ├── chrono/                 # JDN timestamp, bridges, tick stepping
│   ├── parsing/                # ported .his parser (labels, records, time text)
│   ├── adapters/               # .his and .json file adapters
│   ├── render/                 # timeline geometry/layout/painter/view
│   ├── service/                # Agent API (REST/WS) + web frontend
│   │   └── web/index.html      # canvas timeline frontend
│   ├── translations/           # JSON translation catalogs (e.g. zh_CN.json)
│   └── ui/                     # editor, side editor dock, quick entry,
│                               # astro date picker, filter, thread-manager,
│                               # add-thread and bind-source dialogs
├── tests/                      # unit tests
└── docs/                       # design notes
    ├── core_design.md          # time system design
    ├── zoom_design.md          # tick / zoom design (multi-layer LOD fade implemented)
    └── spec/                   # WHY / WHAT / HOW structured spec
```

`docs/spec/` is the authoritative behavior spec: operation logic inherits the
legacy History project plus targeted optimizations, while the foundations
(time, data, adapter, rendering layers) follow the new design. Behavior details
not covered here fall back to `HistoryMigration/docs/history_legacy_spec/`.

The `.his` parser is fully ported into `universal_history/parsing/` — there is
no code dependency on the sibling `History/` repository. Its `History/depot`
directory remains the default data depot (a plain data path; a different depot
root can be injected into `HisFileAdapter`).
