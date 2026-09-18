# UniversalHistory

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
  brief, and event text; select the focus label.
- **Filter dialog**: query the workspace by source, focus label, included/excluded
  tags, and time range; results reuse a single filter thread.

## Install

```bash
python -m pip install -r requirements.txt
```

Or install the project as an editable package:

```bash
python -m pip install -e .
```

## Run

```bash
python -m universal_history
```

Or, after installation:

```bash
universal-history
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
├── universal_history/          # main package
│   ├── __main__.py             # python -m universal_history
│   ├── main_window.py          # PyQt6 application entry point
│   ├── models/                 # Event, EventIndex, Workspace
│   ├── chrono/                 # JDN timestamp, bridges, tick stepping
│   ├── parsing/                # ported .his parser (labels, records, time text)
│   ├── adapters/               # .his file adapter
│   ├── render/                 # timeline geometry/layout/painter/view
│   ├── translations/           # JSON translation catalogs (e.g. zh_CN.json)
│   └── ui/                     # editor, filter, thread-manager, add-thread,
│                               # and bind-source dialogs
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
