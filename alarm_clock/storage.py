from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from .models import Alarm

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _REPO_ROOT / "alarms.json"
_ENV_STORAGE_PATH = "ALARM_STORAGE_PATH"


def _resolve_default_path() -> Path:
    env = os.environ.get(_ENV_STORAGE_PATH)
    if env:
        return Path(env).expanduser()
    return DEFAULT_PATH


class Storage:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else _resolve_default_path()

    def load(self) -> List[Alarm]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(raw, list):
            return []
        alarms: List[Alarm] = []
        for item in raw:
            try:
                alarms.append(Alarm.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return alarms

    def save(self, alarms: List[Alarm]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps([a.to_dict() for a in alarms], indent=2))
        tmp.replace(self.path)

    @staticmethod
    def next_id(alarms: List[Alarm]) -> int:
        return max((a.id for a in alarms), default=0) + 1
