from alarm_clock.models import Alarm


def test_to_from_dict_roundtrip():
    a = Alarm(
        id=1,
        time_str="07:00",
        label="wake",
        created_at="2026-01-01T00:00:00",
        enabled=True,
        repeat="daily",
        sound="/tmp/x.wav",
    )
    assert Alarm.from_dict(a.to_dict()) == a


def test_from_dict_defaults():
    a = Alarm.from_dict(
        {"id": 2, "time_str": "08:00", "label": "", "created_at": "x"}
    )
    assert a.enabled is True
    assert a.repeat == "once"
    assert a.sound == ""


def test_from_dict_invalid_repeat_falls_back_to_once():
    a = Alarm.from_dict(
        {
            "id": 3,
            "time_str": "09:00",
            "label": "",
            "created_at": "x",
            "repeat": "garbage",
        }
    )
    assert a.repeat == "once"


def test_from_dict_coerces_types():
    a = Alarm.from_dict(
        {"id": "3", "time_str": "09:00", "label": "x", "created_at": "y", "enabled": 1}
    )
    assert a.id == 3 and a.enabled is True
