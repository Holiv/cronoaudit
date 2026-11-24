#!/usr/bin/env python3
"""The one preference file the engine, the skill and the MS Project add-in share.

    ~/.cronoaudit/config.json        (Windows: %USERPROFILE%\\.cronoaudit\\config.json)

One key today, `secret`, with three values:

    "ask"   factory default: ask before a run in free mode
    "on"    secret mode by default
    "off"   free mode by default, never ask

Free mode is what exists: whatever an agent reads goes to that agent's provider.
Secret mode is in secret_mode.py. This module only stores the preference and decides
which mode a run is in; it never reads a schedule.

The rule the callers rely on: a missing, unreadable or malformed file is "ask", and
the reason is reported, never swallowed. A preference that cannot be read must not
quietly turn into "free, do not ask".

CRONOAUDIT_CONFIG_DIR replaces the folder. The tests use it so that no test ever
touches the real home directory.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

ENV_DIR = "CRONOAUDIT_CONFIG_DIR"
FILE_NAME = "config.json"
KEY = "secret"
VALUES = ("ask", "on", "off")
DEFAULT = "ask"


def config_dir() -> str:
    override = os.environ.get(ENV_DIR)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(os.path.expanduser("~"), ".cronoaudit")


def config_path() -> str:
    return os.path.join(config_dir(), FILE_NAME)


def _read_object(path: str):
    """The file as a dict, or (None, status, detail) when it cannot be used."""
    try:
        # utf-8-sig: a Windows editor may have put a byte-order mark in front.
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return None, "missing", ""
    except (OSError, ValueError) as exc:
        return None, "corrupt", f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "corrupt", "the file is valid JSON but not an object"
    return data, "ok", ""


def load() -> dict:
    """The preference and how it was arrived at.

    status: "ok"       the file exists and holds a valid value
            "missing"  no file (or no key): factory default
            "corrupt"  the file is unreadable or not a JSON object: treated as ask
            "invalid"  the key holds something other than ask/on/off: treated as ask
    """
    path = config_path()
    data, status, detail = _read_object(path)
    if data is None:
        return {"secret": DEFAULT, "status": status, "detail": detail, "path": path}
    if KEY not in data:
        return {"secret": DEFAULT, "status": "missing", "detail": "", "path": path}
    value = data[KEY]
    if isinstance(value, str) and value.strip().lower() in VALUES:
        return {"secret": value.strip().lower(), "status": "ok", "detail": "", "path": path}
    return {"secret": DEFAULT, "status": "invalid", "detail": repr(value), "path": path}


def set_secret(value: str) -> str:
    """Store the preference and return the path written.

    Atomic: the new content goes to a temporary file in the same folder and replaces
    the old one in a single rename, so a reader never sees half a file and a crash
    never leaves one. Other keys of a readable file are kept; an unreadable file is
    replaced, because there is nothing in it to keep.
    """
    value = str(value).strip().lower()
    if value not in VALUES:
        raise ValueError(f"secret must be one of {', '.join(VALUES)}; got {value!r}")
    folder = config_dir()
    path = os.path.join(folder, FILE_NAME)
    os.makedirs(folder, exist_ok=True)
    data, _status, _detail = _read_object(path)
    data = dict(data or {})
    data[KEY] = value
    fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=folder)
    try:
        # UTF-8 without a byte-order mark, the same bytes the add-in writes.
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def decide(flag_secret: bool, flag_free: bool, preference: str, interactive: bool) -> str:
    """Which mode a run is in, from what was asked and what is stored.

    "secret"  asked for by flag, or stored as the default
    "free"    asked for by flag, or stored as "off"
    "ask"     stored as "ask" and a person is at the terminal
    "notice"  stored as "ask" and nobody can answer: go on in free mode, saying so

    An explicit flag wins over the stored preference. The two flags together are the
    caller's mistake and are rejected before this is reached.
    """
    if flag_secret:
        return "secret"
    if flag_free:
        return "free"
    if preference == "on":
        return "secret"
    if preference == "off":
        return "free"
    return "ask" if interactive else "notice"


def system_lang() -> str:
    """"pt" or "en", for messages printed before any schedule has been read.

    The report follows the schedule's language, but the mode question comes before
    the schedule is opened, so there is nothing to detect from. The environment is
    all there is; English when it says nothing.
    """
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = (os.environ.get(name) or "").strip().lower()
        if value and value not in ("c", "posix"):
            return "pt" if value.startswith("pt") else "en"
    if sys.platform == "win32":
        try:
            import ctypes
            # The low ten bits are the primary language; 0x16 is Portuguese.
            if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x16:
                return "pt"
        except Exception:
            pass
    return "en"
