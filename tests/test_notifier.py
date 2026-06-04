import sys
import threading
from pathlib import Path

from alarm_clock import notifier
from alarm_clock.models import Alarm
from alarm_clock.notifier import default_sound, notify, start_looped_playback, stop_playback


def test_default_sound_returns_existing_path():
    """default_sound should always return something — bundled WAV ships with repo."""
    d = default_sound()
    assert d is not None
    assert Path(d).exists()


def test_bundled_sound_exists_in_repo():
    """The bundled fallback WAV must ship with the package."""
    bundled = Path(__file__).resolve().parent.parent / "alarm_clock" / "sounds" / "default.wav"
    assert bundled.exists()
    assert bundled.stat().st_size > 0


def test_env_var_overrides_default_sound(monkeypatch, tmp_path):
    """ALARM_DEFAULT_SOUND should win over the platform default."""
    custom = tmp_path / "my.wav"
    custom.write_bytes(b"RIFF")
    monkeypatch.setenv("ALARM_DEFAULT_SOUND", str(custom))
    assert default_sound() == str(custom)


def test_env_var_pointing_to_missing_file_falls_through(monkeypatch):
    """If the env var points to nothing, we still get a working default."""
    monkeypatch.setenv("ALARM_DEFAULT_SOUND", "/definitely/not/a/file.wav")
    d = default_sound()
    assert d is not None
    assert Path(d).exists()


def test_env_var_expands_tilde(monkeypatch, tmp_path, capsys):
    """`~` in ALARM_DEFAULT_SOUND should expand to $HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))
    sound = tmp_path / "mine.wav"
    sound.write_bytes(b"RIFF")
    monkeypatch.setenv("ALARM_DEFAULT_SOUND", "~/mine.wav")
    assert default_sound() == str(sound)


def test_notify_uses_alarm_sound_when_set(monkeypatch, capsys, tmp_path):
    started = []

    def fake_start(path):
        started.append(path)
        return True

    monkeypatch.setattr(notifier, "start_looped_playback", fake_start)

    sound = tmp_path / "x.wav"
    sound.write_bytes(b"x")
    a = Alarm(id=1, time_str="07:00", label="w", created_at="x", sound=str(sound))
    notify(a)

    assert started == [str(sound)]
    assert "looping sound (configured)" in capsys.readouterr().out


def test_notify_uses_default_when_no_alarm_sound(monkeypatch, capsys):
    started = []
    monkeypatch.setattr(notifier, "start_looped_playback", lambda p: started.append(p) or True)
    monkeypatch.setattr(notifier, "default_sound", lambda: "/some/default.aiff")

    a = Alarm(id=1, time_str="07:00", label="w", created_at="x")
    notify(a)

    assert started == ["/some/default.aiff"]
    assert "looping sound (default)" in capsys.readouterr().out


def test_stop_playback_is_safe_when_nothing_is_playing():
    # Just shouldn't raise.
    stop_playback()
    stop_playback()


def test_start_looped_playback_then_stop_actually_terminates_thread(monkeypatch, tmp_path):
    """The background loop thread must exit promptly when stop_playback() is called."""
    sound = tmp_path / "x.wav"
    sound.write_bytes(b"RIFF")

    # Replace subprocess.Popen with a fake that sleeps in poll() until terminate.
    class FakeProc:
        def __init__(self, *a, **kw):
            self._terminated = threading.Event()

        def poll(self):
            return 0 if self._terminated.is_set() else None

        def terminate(self):
            self._terminated.set()

        def wait(self, timeout=None):
            self._terminated.wait(timeout)
            return 0

        def kill(self):
            self._terminated.set()

    monkeypatch.setattr(notifier.subprocess, "Popen", FakeProc)
    # Pretend a player is available regardless of platform.
    monkeypatch.setattr(notifier, "_player_cmd", lambda p: ["fake-player", p])

    assert start_looped_playback(str(sound)) is True
    stop_playback()
    # If stop_playback returned, the thread joined within its 2s timeout.
    assert notifier._loop_thread is None
    assert notifier._stop_event is None
