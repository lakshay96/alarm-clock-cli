from __future__ import annotations

from dataclasses import asdict, dataclass

REPEAT_CHOICES = ("once", "daily", "weekdays", "weekends")


@dataclass
class Alarm:
    id: int
    time_str: str
    label: str
    created_at: str
    enabled: bool = True
    repeat: str = "once"
    sound: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        repeat = str(data.get("repeat", "once"))
        if repeat not in REPEAT_CHOICES:
            repeat = "once"
        return cls(
            id=int(data["id"]),
            time_str=str(data["time_str"]),
            label=str(data.get("label", "")),
            created_at=str(data["created_at"]),
            enabled=bool(data.get("enabled", True)),
            repeat=repeat,
            sound=str(data.get("sound", "")),
        )
