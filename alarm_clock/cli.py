from __future__ import annotations

import argparse
import select
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from .models import REPEAT_CHOICES, Alarm
from .notifier import notify, stop_playback
from .scheduler import Scheduler
from .storage import Storage
from .timeparse import TimeParseError, format_time, parse_time

PROMPT_TIMEOUT_SECONDS = 60


def add(args: argparse.Namespace, storage: Storage) -> int:
    try:
        t = parse_time(args.time)
    except TimeParseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.sound:
        sound_path = Path(args.sound).expanduser()
        if not sound_path.exists():
            print(f"error: sound file not found: {args.sound}", file=sys.stderr)
            return 2

    alarms = storage.load()
    alarm = Alarm(
        id=storage.next_id(alarms),
        time_str=format_time(t),
        label=args.label or "",
        created_at=datetime.now().isoformat(timespec="seconds"),
        repeat=args.repeat,
        sound=args.sound or "",
    )
    alarms.append(alarm)
    storage.save(alarms)

    parts = [f"Added alarm [{alarm.id}] at {alarm.time_str}"]
    if alarm.label:
        parts.append(f"— {alarm.label}")
    if alarm.repeat != "once":
        parts.append(f"({alarm.repeat})")
    if alarm.sound:
        parts.append(f"[sound: {alarm.sound}]")
    print(" ".join(parts))
    return 0


def list(args: argparse.Namespace, storage: Storage) -> int:
    alarms = storage.load()
    if not alarms:
        print("No alarms.")
        return 0
    for a in sorted(alarms, key=lambda x: x.id):
        label = a.label or "(no label)"
        flags = []
        if not a.enabled:
            flags.append("disabled")
        if a.repeat != "once":
            flags.append(a.repeat)
        if a.sound:
            flags.append(f"sound={a.sound}")
        suffix = f"  ({', '.join(flags)})" if flags else ""
        print(f"[{a.id}] {a.time_str}  {label}{suffix}")
    return 0


def cancel(args: argparse.Namespace, storage: Storage) -> int:
    alarms = storage.load()
    remaining = [a for a in alarms if a.id != args.id]
    if len(remaining) == len(alarms):
        print(f"error: no alarm with id {args.id}", file=sys.stderr)
        return 1
    storage.save(remaining)
    print(f"Cancelled alarm {args.id}")
    return 0


def _build_snooze_alarm(storage: Storage, original: Alarm, minutes: int) -> Alarm:
    alarms = storage.load()
    fire_at = datetime.now() + timedelta(minutes=minutes)
    label = f"snooze: {original.label}" if original.label else "snooze"
    new_alarm = Alarm(
        id=storage.next_id(alarms),
        time_str=fire_at.strftime("%H:%M"),
        label=label,
        created_at=datetime.now().isoformat(timespec="seconds"),
        repeat="once",
        sound=original.sound,
    )
    alarms.append(new_alarm)
    storage.save(alarms)
    return new_alarm


def snooze(args: argparse.Namespace, storage: Storage) -> int:
    if args.minutes <= 0:
        print("error: --minutes must be positive", file=sys.stderr)
        return 2

    alarms = storage.load()
    original = next((a for a in alarms if a.id == args.id), None)
    if original is None:
        print(f"error: no alarm with id {args.id}", file=sys.stderr)
        return 1

    new_alarm = _build_snooze_alarm(storage, original, args.minutes)
    print(
        f"Snoozed: created alarm [{new_alarm.id}] at {new_alarm.time_str} "
        f"(+{args.minutes} min)"
    )
    return 0


def _make_interactive_after_fire(
    storage: Storage, timeout: int = PROMPT_TIMEOUT_SECONDS
):
    """Return an `after_fire` callback that prompts for snooze/dismiss/quit.

    - 's' (or just <Enter> on 's')  → snooze 5 min
    - 's N'                         → snooze N min
    - 'd' or <Enter>                → dismiss
    - 'q'                           → stop the scheduler (raises KeyboardInterrupt)
    - no input within `timeout`s    → auto-dismiss

    No-op (returns None without prompting) when stdin is not a TTY, so the
    scheduler stays usable in pipes, cron, and tests.
    """

    def callback(alarm: Alarm) -> Optional[Alarm]:
        if not sys.stdin.isatty():
            stop_playback()
            return None

        try:
            print(
                f"[s] snooze 5m  |  [s <min>] e.g. 's 10' for 10 min  |  "
                f"[Enter] dismiss  |  [q] quit  (auto-dismiss in {timeout}s)"
            )
            sys.stdout.write("> ")
            sys.stdout.flush()

            try:
                ready, _, _ = select.select([sys.stdin], [], [], timeout)
            except (OSError, ValueError):
                print("\n(could not read input — dismissed)")
                return None

            if not ready:
                print("\n(timeout — dismissed)")
                return None

            line = sys.stdin.readline()
            if not line:
                print("(EOF — dismissed)")
                return None

            choice = line.strip().lower()

            if choice == "q":
                print("Quitting scheduler.")
                raise KeyboardInterrupt

            if choice.startswith("s"):
                parts = choice.split()
                minutes = 5
                if len(parts) > 1:
                    try:
                        minutes = int(parts[1])
                    except ValueError:
                        print(f"invalid minutes {parts[1]!r} — dismissed")
                        return None
                if minutes <= 0:
                    print("minutes must be positive — dismissed")
                    return None
                new_alarm = _build_snooze_alarm(storage, alarm, minutes)
                print(
                    f"Snoozed: alarm [{new_alarm.id}] at {new_alarm.time_str} "
                    f"(+{minutes} min)"
                )
                return new_alarm

            print("Dismissed.")
            return None
        finally:
            stop_playback()

    return callback


def run(args: argparse.Namespace, storage: Storage) -> int:
    alarms = storage.load()
    Scheduler(
        on_fire=notify,
        after_fire=_make_interactive_after_fire(storage),
    ).run(alarms)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alarm",
        description="A minimal CLI alarm clock. Add alarms, then `run` to wait for them.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new alarm.")
    p_add.add_argument("time", help="Time as 'HH:MM' (24h) or 'h:MM AM/PM' (12h).")
    p_add.add_argument("--label", "-l", default="", help="Optional label.")
    p_add.add_argument(
        "--repeat",
        "-r",
        choices=REPEAT_CHOICES,
        default="once",
        help="Repeat schedule (default: once).",
    )
    p_add.add_argument(
        "--sound",
        "-s",
        default="",
        help="Optional path to a sound file to play (.wav/.aiff recommended).",
    )

    sub.add_parser("list", help="List all alarms.")

    p_cancel = sub.add_parser("cancel", help="Cancel an alarm by id.")
    p_cancel.add_argument("id", type=int, help="Alarm id (from `list`).")

    p_snooze = sub.add_parser(
        "snooze",
        help="Create a one-shot alarm N minutes from now, copying label/sound from an existing alarm.",
    )
    p_snooze.add_argument("id", type=int, help="Source alarm id.")
    p_snooze.add_argument(
        "--minutes", "-m", type=int, default=5, help="Minutes from now (default: 5)."
    )

    sub.add_parser(
        "run",
        help="Run the scheduler. After each alarm fires you can snooze, dismiss, or quit.",
    )

    return parser


COMMANDS = {
    "add": add,
    "list": list,
    "cancel": cancel,
    "snooze": snooze,
    "run": run,
}


def main(argv: Optional[Sequence[str]] = None, storage: Optional[Storage] = None) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args, storage or Storage())


if __name__ == "__main__":
    sys.exit(main())
