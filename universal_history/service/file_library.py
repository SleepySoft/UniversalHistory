"""Allow-listed server files for the web frontend.

The HTTP API never accepts a client-provided path. It only accepts an opaque
ID generated from a file that was discovered under one of the server-configured
allow-list roots.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


SUPPORTED_SUFFIXES = {".his", ".json"}


@dataclass(frozen=True)
class LibraryFile:
    id: str
    name: str
    relative_path: str
    file_format: str
    size_bytes: int


class AllowedFileLibrary:
    """Discover and resolve files from explicit server-side roots."""

    def __init__(self, roots: Sequence[Path | str] = ()):
        self._roots: List[Path] = []
        for raw_root in roots:
            root = Path(raw_root).expanduser().resolve(strict=True)
            if root.is_file() and root.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise ValueError(f"Unsupported allowed file: {root}")
            if not root.is_file() and not root.is_dir():
                raise ValueError(f"Allowed path is not a file or directory: {root}")
            if root not in self._roots:
                self._roots.append(root)
        self._files: Dict[str, Path] = {}
        self._loaded_ids: set[str] = set()

    @property
    def roots(self) -> List[Path]:
        return list(self._roots)

    def list_files(self) -> List[LibraryFile]:
        files: Dict[str, LibraryFile] = {}
        self._files.clear()
        for root in self._roots:
            candidates = [root] if root.is_file() else self._scan_directory(root)
            for candidate in candidates:
                resolved = candidate.resolve(strict=True)
                try:
                    relative = resolved.relative_to(root)
                except ValueError:
                    continue
                file_id = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
                if file_id in files:
                    continue
                relative_path = (
                    root.name if root.is_file() else relative.as_posix()
                )
                files[file_id] = LibraryFile(
                    id=file_id,
                    name=resolved.name,
                    relative_path=relative_path,
                    file_format=resolved.suffix.lower().removeprefix("."),
                    size_bytes=resolved.stat().st_size,
                )
                self._files[file_id] = resolved
        return sorted(files.values(), key=lambda item: item.relative_path.lower())

    def resolve(self, file_id: str) -> Path:
        if file_id not in self._files:
            self.list_files()
        if file_id not in self._files:
            raise FileNotFoundError("File is not in the server allow-list")
        return self._files[file_id].resolve(strict=True)

    def mark_loaded(self, file_id: str) -> None:
        self._loaded_ids.add(file_id)

    def mark_loaded_path(self, path: Path | str) -> None:
        resolved = Path(path).expanduser().resolve(strict=True)
        file_id = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
        self._loaded_ids.add(file_id)

    def loaded_ids(self) -> set[str]:
        return set(self._loaded_ids)

    @staticmethod
    def _scan_directory(root: Path) -> List[Path]:
        candidates: List[Path] = []
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            resolved = candidate.resolve(strict=False)
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            candidates.append(resolved)
        return candidates
