from datetime import datetime, time, timedelta

from alarm_clock.models import Alarm
from alarm_clock.scheduler import Scheduler, next_fire


def test_next_fire_later_today():
    now = datetime(2026, 6, 4, 10, 0, 0)
    assert next_fire(time(14, 30), now) == datetime(2026, 6, 4, 14, 30)


def test_next_fire_rolls_to_tomorrow():
    now = datetime(2026, 6, 4, 15, 0, 0)
    assert next_fire(time(7, 0), now) == datetime(2026, 6, 5, 7, 0)


def test_next_fire_same_minute_fires_now():
    now = datetime(2026, 6, 4, 7, 0, 30)
    assert next_fire(time(7, 0), now) == datetime(2026, 6, 4, 7, 0, 0)


def test_next_fire_one_minute_past_rolls_over():
    now = datetime(2026, 6, 4, 7, 1, 0)
    assert next_fire(time(7, 0), now) == datetime(2026, 6, 5, 7, 0)


def test_next_fire_weekdays_skips_weekend():
    # 2026-06-06 is a Saturday
    now = datetime(2026, 6, 6, 10, 0, 0)
    nxt = next_fire(time(7, 0), now, repeat="weekdays")
    # Should land on Monday 2026-06-08
    assert nxt == datetime(2026, 6, 8, 7, 0)


def test_next_fire_weekends_skips_weekdays():
    # 2026-06-04 is a Thursday
    now = datetime(2026, 6, 4, 10, 0, 0)
    nxt = next_fire(time(9, 0), now, repeat="weekends")
    # Should land on Saturday 2026-06-06
    assert nxt == datetime(2026, 6, 6, 9, 0)


class _FakeClock:
    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def test_scheduler_fires_in_order_and_exits():
    clock = _FakeClock(datetime(2026, 6, 4, 6, 59, 0))
    fired = []

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    sch = Scheduler(on_fire=fired.append, clock=clock, sleep=fake_sleep)
    alarms = [
        Alarm(id=1, time_str="08:00", label="b", created_at="x"),
        Alarm(id=2, time_str="07:00", label="a", created_at="x"),
    ]
    sch.run(alarms)

    assert [a.id for a in fired] == [2, 1]


def test_scheduler_recurring_daily_fires_on_consecutive_days():
    """A recurring daily alarm should re-fire on consecutive days."""
    clock = _FakeClock(datetime(2026, 6, 4, 6, 59, 0))
    fired = []

    def on_fire(a: Alarm) -> None:
        fired.append((a.id, clock.now.date()))
        if len(fired) >= 3:
            raise KeyboardInterrupt

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    sch = Scheduler(on_fire=on_fire, clock=clock, sleep=fake_sleep)
    alarms = [
        Alarm(id=1, time_str="07:00", label="d", created_at="x", repeat="daily"),
    ]
    sch.run(alarms)

    assert len(fired) == 3
    assert [d for _, d in fired] == [
        datetime(2026, 6, 4).date(),
        datetime(2026, 6, 5).date(),
        datetime(2026, 6, 6).date(),
    ]


def test_scheduler_recurring_alongside_one_shot():
    """One-shot terminates after firing; recurring keeps going until interrupted."""
    clock = _FakeClock(datetime(2026, 6, 4, 6, 59, 0))
    fired = []

    def on_fire(a: Alarm) -> None:
        fired.append((a.id, clock.now.strftime("%Y-%m-%d %H:%M")))
        if len(fired) >= 3:
            raise KeyboardInterrupt

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    sch = Scheduler(on_fire=on_fire, clock=clock, sleep=fake_sleep)
    alarms = [
        Alarm(id=1, time_str="07:00", label="daily", created_at="x", repeat="daily"),
        Alarm(id=2, time_str="07:30", label="once", created_at="x"),
    ]
    sch.run(alarms)

    # Expected: daily D1 07:00, once D1 07:30, daily D2 07:00 → interrupt
    assert [pair[0] for pair in fired] == [1, 2, 1]


def test_scheduler_with_no_active_alarms_is_noop(capsys):
    sch = Scheduler(on_fire=lambda a: None)
    sch.run([])
    out = capsys.readouterr().out
    assert "No active alarms" in out


def test_after_fire_callback_can_inject_a_snoozed_alarm():
    """If after_fire returns an Alarm, it should be appended to the queue."""
    clock = _FakeClock(datetime(2026, 6, 4, 6, 59, 0))
    fired = []

    def on_fire(a: Alarm) -> None:
        fired.append(a.id)

    def after_fire(a: Alarm):
        # Inject a snooze the first time the original alarm fires.
        if a.id == 1 and not any(f == 99 for f in fired):
            return Alarm(id=99, time_str="07:05", label="snooze", created_at="x")
        return None

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    sch = Scheduler(
        on_fire=on_fire, after_fire=after_fire, clock=clock, sleep=fake_sleep
    )
    alarms = [Alarm(id=1, time_str="07:00", label="orig", created_at="x")]
    sch.run(alarms)

    assert fired == [1, 99]


def test_after_fire_raising_keyboard_interrupt_stops_loop(capsys):
    """The 'q' interactive choice raises KeyboardInterrupt — must terminate cleanly."""
    clock = _FakeClock(datetime(2026, 6, 4, 6, 59, 0))
    fired = []

    def after_fire(a: Alarm):
        raise KeyboardInterrupt

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    sch = Scheduler(
        on_fire=fired.append,
        after_fire=after_fire,
        clock=clock,
        sleep=fake_sleep,
    )
    alarms = [
        Alarm(id=1, time_str="07:00", label="a", created_at="x", repeat="daily"),
    ]
    sch.run(alarms)

    assert len(fired) == 1
    assert "Stopped." in capsys.readouterr().out
