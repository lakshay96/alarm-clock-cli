from alarm_clock.cli import main
from alarm_clock.storage import Storage


def _storage(tmp_path):
    return Storage(tmp_path / "alarms.json")


def test_add_then_list(tmp_path, capsys):
    s = _storage(tmp_path)
    assert main(["add", "07:00", "-l", "wake"], storage=s) == 0
    capsys.readouterr()
    assert main(["list"], storage=s) == 0
    out = capsys.readouterr().out
    assert "[1] 07:00" in out and "wake" in out


def test_add_invalid_time_fails(tmp_path, capsys):
    s = _storage(tmp_path)
    rc = main(["add", "25:00"], storage=s)
    err = capsys.readouterr().err
    assert rc == 2 and "Invalid time" in err


def test_add_with_repeat_persists(tmp_path, capsys):
    s = _storage(tmp_path)
    assert main(["add", "07:00", "-r", "weekdays"], storage=s) == 0
    capsys.readouterr()
    main(["list"], storage=s)
    out = capsys.readouterr().out
    assert "weekdays" in out


def test_add_with_missing_sound_file_fails(tmp_path, capsys):
    s = _storage(tmp_path)
    rc = main(["add", "07:00", "--sound", str(tmp_path / "nope.wav")], storage=s)
    err = capsys.readouterr().err
    assert rc == 2 and "sound file not found" in err


def test_add_with_existing_sound_persists(tmp_path, capsys):
    sound = tmp_path / "bell.wav"
    sound.write_bytes(b"RIFF")
    s = _storage(tmp_path)
    assert main(["add", "07:00", "--sound", str(sound)], storage=s) == 0
    assert s.load()[0].sound == str(sound)


def test_cancel_existing(tmp_path, capsys):
    s = _storage(tmp_path)
    main(["add", "07:00"], storage=s)
    capsys.readouterr()
    assert main(["cancel", "1"], storage=s) == 0
    assert s.load() == []


def test_cancel_unknown_id(tmp_path, capsys):
    s = _storage(tmp_path)
    rc = main(["cancel", "42"], storage=s)
    err = capsys.readouterr().err
    assert rc == 1 and "no alarm with id 42" in err


def test_snooze_creates_new_alarm(tmp_path, capsys):
    s = _storage(tmp_path)
    main(["add", "07:00", "-l", "wake"], storage=s)
    capsys.readouterr()
    rc = main(["snooze", "1", "-m", "5"], storage=s)
    assert rc == 0
    alarms = s.load()
    assert len(alarms) == 2
    snoozed = alarms[-1]
    assert snoozed.repeat == "once"
    assert "snooze" in snoozed.label.lower()


def test_snooze_unknown_id(tmp_path, capsys):
    s = _storage(tmp_path)
    rc = main(["snooze", "99", "-m", "5"], storage=s)
    err = capsys.readouterr().err
    assert rc == 1 and "no alarm with id 99" in err


def test_snooze_invalid_minutes(tmp_path, capsys):
    s = _storage(tmp_path)
    main(["add", "07:00"], storage=s)
    capsys.readouterr()
    rc = main(["snooze", "1", "-m", "0"], storage=s)
    err = capsys.readouterr().err
    assert rc == 2 and "must be positive" in err


def test_list_empty(tmp_path, capsys):
    s = _storage(tmp_path)
    assert main(["list"], storage=s) == 0
    assert "No alarms." in capsys.readouterr().out


def test_twelve_hour_input_is_normalized(tmp_path, capsys):
    s = _storage(tmp_path)
    main(["add", "2:30 PM"], storage=s)
    capsys.readouterr()
    main(["list"], storage=s)
    assert "14:30" in capsys.readouterr().out
