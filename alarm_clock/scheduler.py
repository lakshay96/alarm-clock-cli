from __future__ import annotations

import time as _time
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional

from .models import Alarm
from .timeparse import parse_time

_WEEKDAYS = frozenset({0, 1, 2, 3, 4})
_WEEKENDS = frozenset({5, 6})
_ALL_DAYS = frozenset(range(7))


def _allowed_days(repeat: str) -> frozenset:
    if repeat == "weekdays":
        return _WEEKDAYS
    if repeat == "weekends":
        return _WEEKENDS
    return _ALL_DAYS


def next_fire(alarm_time: time, now: datetime, repeat: str = "once") -> datetime:
    """Compute the next datetime an alarm at `alarm_time` should fire.

    For recurring alarms (`weekdays`, `weekends`), skips disallowed days.
    """
    candidate = now.replace(
        hour=alarm_time.hour, minute=alarm_time.minute, second=0, microsecond=0
    )
    now_minute = now.replace(second=0, microsecond=0)
    if candidate < now_minute:
        candidate += timedelta(days=1)

    allowed = _allowed_days(repeat)
    while candidate.weekday() not in allowed:
        candidate += timedelta(days=1)
    return candidate


class Scheduler:
    def __init__(
        self,
        on_fire: Callable[[Alarm], None],
        after_fire: Optional[Callable[[Alarm], Optional[Alarm]]] = None,
        clock: Callable[[], datetime] = datetime.now,
        sleep: Callable[[float], None] = _time.sleep,
    ) -> None:
        self.on_fire = on_fire
        # after_fire is an optional hook called right after on_fire. If it
        # returns an Alarm, that alarm is appended to the active queue (used
        # by the interactive snooze prompt in the CLI).
        self.after_fire = after_fire
        self.clock = clock
        self.sleep = sleep

    def run(self, alarms: List[Alarm]) -> None:
        queue = [a for a in alarms if a.enabled]
        if not queue:
            print("No active alarms. Add one with: alarm.py add HH:MM")
            return

        last_fired: Dict[int, datetime] = {}

        try:
            while queue:
                now = self.clock()
                upcoming = []
                for a in queue:
                    anchor = now
                    lf = last_fired.get(a.id)
                    if lf is not None:
                        anchor = max(anchor, lf + timedelta(seconds=60))
                    upcoming.append(
                        (next_fire(parse_time(a.time_str), anchor, a.repeat), a)
                    )
                upcoming.sort(key=lambda pair: pair[0])
                next_dt, alarm = upcoming[0]

                delta = (next_dt - self.clock()).total_seconds()
                label = alarm.label or "(no label)"
                repeat_tag = "" if alarm.repeat == "once" else f" [{alarm.repeat}]"
                print(
                    f"Next: [{alarm.id}] {label}{repeat_tag} at "
                    f"{next_dt.strftime('%Y-%m-%d %H:%M')} (in {max(0, int(delta))}s)"
                )
                if delta > 0:
                    self.sleep(delta)

                self.on_fire(alarm)
                last_fired[alarm.id] = next_dt

                if alarm.repeat == "once":
                    queue = [a for a in queue if a.id != alarm.id]

                if self.after_fire is not None:
                    extra = self.after_fire(alarm)
                    if extra is not None:
                        queue.append(extra)
        except KeyboardInterrupt:
            print("\nStopped.")
