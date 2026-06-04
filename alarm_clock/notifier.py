from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

from .models import Alarm

_BUNDLED_SOUND = Path(__file__).parent / "sounds" / "default.wav"
_ENV_DEFAULT_SOUND = "ALARM_DEFAULT_SOUND"

_MACOS_DEFAULTS = [
    "/System/Library/Sounds/Submarine.aiff",
    "/System/Library/Sounds/Sosumi.aiff",
    "/System/Library/Sounds/Glass.aiff",
    "/System/Library/Sounds/Ping.aiff",
]

_LINUX_DEFAULTS = [
    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/alsa/Front_Center.wav",
]


def default_sound() -> Optional[str]:
    """Resolve the fallback sound used when an alarm has no explicit `--sound`.

    Resolution order:
      1. `ALARM_DEFAULT_SOUND` env var (lets the user override system-wide)
      2. Platform built-in (macOS Submarine, Linux freedesktop alarm sound, …)
      3. Bundled WAV that ships with the repo (works on any machine)
    """
    env_path = os.environ.get(_ENV_DEFAULT_SOUND)
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return str(p)

    if sys.platform == "darwin":
        candidates = _MACOS_DEFAULTS
    elif sys.platform.startswith("linux"):
        candidates = _LINUX_DEFAULTS
    else:
        candidates = []
    for c in candidates:
        if Path(c).exists():
            return c
    if _BUNDLED_SOUND.exists():
        return str(_BUNDLED_SOUND)
    return None


def _player_cmd(sound_path: str) -> Optional[List[str]]:
    p = Path(sound_path).expanduser()
    if not p.exists():
        return None
    if sys.platform == "darwin":
        player = shutil.which("afplay")
    elif sys.platform.startswith("linux"):
        player = shutil.which("paplay") or shutil.which("aplay")
    else:
        return None
    if not player:
        return None
    return [player, str(p)]


def _play_sound(path: str) -> bool:
    """Play a sound file once, blocking until it finishes."""
    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(
                str(Path(path).expanduser()), winsound.SND_FILENAME
            )
            return True
        except Exception:
            return False
    cmd = _player_cmd(path)
    if cmd is None:
        return False
    try:
        result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


# --- Looped playback ---------------------------------------------------------
#
# When an alarm fires we play the sound on a background thread in a loop until
# the user dismisses / snoozes / quits the prompt, or the prompt auto-times out.
# State is module-global because there is at most one active alarm prompt at a
# time in this scheduler.

_stop_event: Optional[threading.Event] = None
_current_proc: Optional[subprocess.Popen] = None
_windows_playing = False
_loop_thread: Optional[threading.Thread] = None


def _looped_subprocess_playback(sound_path: str, stop: threading.Event) -> None:
    global _current_proc
    cmd = _player_cmd(sound_path)
    if cmd is None:
        return
    while not stop.is_set():
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
        except (FileNotFoundError, OSError):
            return
        _current_proc = proc  # published so stop_playback can also terminate
        while proc.poll() is None:
            if stop.wait(0.1):
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except (subprocess.TimeoutExpired, OSError):
                    try:
                        proc.kill()
                    except OSError:
                        pass
                return


def start_looped_playback(sound_path: str) -> bool:
    """Begin looping the given sound in the background. Returns True on start."""
    global _stop_event, _windows_playing, _loop_thread

    stop_playback()

    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(
                str(Path(sound_path).expanduser()),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )
            _windows_playing = True
            return True
        except Exception:
            return False

    if _player_cmd(sound_path) is None:
        return False

    _stop_event = threading.Event()
    _loop_thread = threading.Thread(
        target=_looped_subprocess_playback,
        args=(sound_path, _stop_event),
        daemon=True,
    )
    _loop_thread.start()
    return True


def stop_playback() -> None:
    """Stop any currently looping sound. Safe to call when nothing is playing."""
    global _stop_event, _current_proc, _windows_playing, _loop_thread

    if _windows_playing:
        try:
            import winsound

            winsound.PlaySound(None, 0)
        except Exception:
            pass
        _windows_playing = False

    if _stop_event is not None:
        _stop_event.set()
        _stop_event = None

    if _current_proc is not None:
        try:
            if _current_proc.poll() is None:
                _current_proc.terminate()
        except OSError:
            pass
        _current_proc = None

    if _loop_thread is not None:
        _loop_thread.join(timeout=2)
        _loop_thread = None


def notify(alarm: Alarm) -> None:
    sys.stdout.write("\a")
    sys.stdout.flush()
    label = alarm.label or "(no label)"
    repeat_tag = "" if alarm.repeat == "once" else f" [{alarm.repeat}]"
    print(f"\n*** ALARM [{alarm.id}] {label}{repeat_tag} — {alarm.time_str} ***")

    chosen = alarm.sound or default_sound()
    if chosen:
        source = "configured" if alarm.sound else "default"
        print(f"[looping sound ({source}): {chosen} — dismiss to stop]")
        if start_looped_playback(chosen):
            return
        print(f"(could not start playback of {chosen})")

    # Windows last-ditch: a single system beep (no looping for this fallback).
    if sys.platform == "win32":
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONHAND)
            return
        except Exception:
            pass

    print("[no audible sound available — terminal bell only]")
