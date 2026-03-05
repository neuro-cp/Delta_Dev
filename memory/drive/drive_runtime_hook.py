from __future__ import annotations

from typing import Dict, Any

from memory.drive.drive_field import DriveField


class DriveRuntimeHook:
    """
    Read-only runtime hook for drive state.

    CONTRACT:
    - Inspection only
    - No influence
    """

    def __init__(self, *, field: DriveField) -> None:
        self._field = field

    def snapshot(self) -> Dict[str, Any]:
        return {
            "count": len(self._field.signals()),
            "signals": {
                s.key: s.magnitude
                for s in self._field.signals()
            },
        }
