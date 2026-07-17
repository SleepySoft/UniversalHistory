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
│   ├── adapters/               # .his file adapter
│   ├── render/                 # timeline geometry/layout/painter/view
│   └── ui/                     # editor, filter, thread-manager, add-thread,
│                               # and bind-source dialogs
├── tests/                      # unit tests
└── docs/                       # design notes
```

The sibling `History/` directory is kept as a reference and is used only by the
`.his` adapter parser.
