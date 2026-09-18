"""
Shared sha256 file-fingerprint store for save-conflict detection
(known-issues #6), used by both the .his and JSON adapters.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional


class FileFingerprints:
    """Remember file content hashes at load/save time and detect drift."""

    def __init__(self):
        self._fingerprints: Dict[str, str] = {}

    @staticmethod
    def _key(path: str) -> str:
        return str(Path(path).absolute())

    @staticmethod
    def _hash(path: str) -> Optional[str]:
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return None

    def remember(self, path: str) -> None:
        fp = self._hash(path)
        if fp is not None:
            self._fingerprints[self._key(path)] = fp

    def has_conflict(self, path: str) -> bool:
        """True when the file was seen before and its content changed since."""
        known = self._fingerprints.get(self._key(path))
        current = self._hash(path)
        return known is not None and current is not None and current != known
