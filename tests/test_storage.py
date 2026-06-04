from pathlib import Path

from alarm_clock.models import Alarm
from alarm_clock.storage import DEFAULT_PATH, Storage


def _alarm(id_=1, time_str="07:00", label="wake"):
    return Alarm(id=id_, time_str=time_str, label=label, created_at="2026-01-01T00:00:00")


def test_save_load_roundtrip(tmp_path):
    s = Storage(tmp_path / "alarms.json")
    alarms = [_alarm(1), _alarm(2, "08:30", "standup")]
    s.save(alarms)
    assert s.load() == alarms


def test_load_missing_returns_empty(tmp_path):
    s = Storage(tmp_path / "does-not-exist.json")
    assert s.load() == []


def test_load_corrupt_returns_empty(tmp_path):
    path = tmp_path / "alarms.json"
    path.write_text("{not valid json")
    s = Storage(path)
    assert s.load() == []


def test_load_wrong_shape_returns_empty(tmp_path):
    path = tmp_path / "alarms.json"
    path.write_text('{"not": "a list"}')
    s = Storage(path)
    assert s.load() == []


def test_load_skips_malformed_entries(tmp_path):
    path = tmp_path / "alarms.json"
    path.write_text(
        '[{"id": 1, "time_str": "07:00", "label": "ok", "created_at": "x"},'
        ' {"broken": true}]'
    )
    s = Storage(path)
    loaded = s.load()
    assert len(loaded) == 1 and loaded[0].id == 1


def test_next_id(tmp_path):
    s = Storage(tmp_path / "a.json")
    assert s.next_id([]) == 1
    assert s.next_id([_alarm(1), _alarm(5)]) == 6


def test_save_is_atomic_via_tmp(tmp_path):
    s = Storage(tmp_path / "a.json")
    s.save([_alarm(1)])
    # No leftover tmp file
    assert not (tmp_path / "a.json.tmp").exists()


def test_default_path_is_in_repo_root(monkeypatch):
    """Default storage file lives next to alarm.py so it's discoverable."""
    monkeypatch.delenv("ALARM_STORAGE_PATH", raising=False)
    assert DEFAULT_PATH.name == "alarms.json"
    assert (DEFAULT_PATH.parent / "alarm.py").exists()
    assert Storage().path == DEFAULT_PATH


def test_env_var_overrides_storage_path(monkeypatch, tmp_path):
    """ALARM_STORAGE_PATH should win over the default location."""
    custom = tmp_path / "custom-alarms.json"
    monkeypatch.setenv("ALARM_STORAGE_PATH", str(custom))
    assert Storage().path == custom


def test_env_var_expands_tilde(monkeypatch, tmp_path):
    """`~` in ALARM_STORAGE_PATH should expand to $HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ALARM_STORAGE_PATH", "~/my-alarms.json")
    assert Storage().path == tmp_path / "my-alarms.json"
