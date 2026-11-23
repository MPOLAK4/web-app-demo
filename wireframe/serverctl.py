"""Start, stop and check a background editor server (R12).

A server started with `start` writes a small *state file* (pid, port, url, file) once
it is listening and deletes it when it stops. These functions use that file to find it.

`stop` asks the server to shut down over HTTP (POST /api/shutdown). It never kills a
process by number: a stale state file could name a pid that now belongs to something
else, and a wrong guess there would be destructive.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from .model import WireframeError

DEFAULT_STATE_FILE = ".wireframe-server.json"
DEFAULT_IDLE_TIMEOUT = 600
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_PY = os.path.join(os.path.dirname(HERE), "server.py")

# Never route requests to our own machine through a proxy from the environment.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def write_state(path, info):
    """Write the state file in one step, so a reader never sees half of it."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(info, f)
    os.replace(tmp, path)


def remove_state(path):
    """Delete the state file. Both `stop` and the dying server do this, and on Windows a
    delete can fail for a moment while the other one is deleting, so retry briefly."""
    for attempt in range(20):
        try:
            os.remove(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def read_state(path):
    """The recorded info, or None if there is no file or it is not what we wrote."""
    try:
        with open(path, encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(info, dict) or not isinstance(info.get("url"), str) \
            or not isinstance(info.get("port"), int):
        return None
    return info


def ping(url, timeout=1.0):
    """True if a wireframe server answers at `url`."""
    try:
        with _opener.open(url + "/api/ping", timeout=timeout) as resp:
            return resp.status == 200 and json.load(resp).get("ok") is True
    except (OSError, ValueError, urllib.error.URLError):
        return False


def status(state_file=DEFAULT_STATE_FILE):
    """The URL of the running server, or None. A state file for a dead server is removed."""
    info = read_state(state_file)
    if info and ping(info["url"]):
        return info["url"]
    remove_state(state_file)
    return None


def start(file, port=0, idle_timeout=DEFAULT_IDLE_TIMEOUT, state_file=DEFAULT_STATE_FILE, wait=15.0):
    """Start the server in the background. Returns (info, already_running)."""
    if isinstance(idle_timeout, bool) or not isinstance(idle_timeout, (int, float)) or idle_timeout <= 0:
        raise WireframeError("--idle-timeout must be a number of seconds greater than 0")
    if status(state_file):
        return read_state(state_file), True
    command = [sys.executable, SERVER_PY, os.path.abspath(file), "--port", str(port),
               "--idle-timeout", str(idle_timeout), "--state-file", os.path.abspath(state_file)]
    flags = {}
    if os.name == "nt":      # no console window, and not tied to ours
        flags["creationflags"] = 0x08000000 | 0x00000200   # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    else:
        flags["start_new_session"] = True
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=err, **flags)
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            info = read_state(state_file)
            if info and info.get("pid") == proc.pid and ping(info["url"]):
                return info, False
            if proc.poll() is not None:
                err.seek(0)
                text = err.read().decode("utf-8", "replace").strip()
                raise WireframeError((text or "the server exited right after starting").splitlines())
            time.sleep(0.05)
        proc.terminate()          # our own child, started a moment ago
        raise WireframeError(f"the server did not answer within {wait:g} seconds")


def stop(state_file=DEFAULT_STATE_FILE, wait=5.0):
    """Ask the recorded server to stop. Returns a sentence saying what happened."""
    info = read_state(state_file)
    if not info or not ping(info["url"]):
        stale = os.path.exists(state_file)
        remove_state(state_file)
        return "Server is not running" + (" (removed a stale state file)." if stale else ".")
    request = urllib.request.Request(info["url"] + "/api/shutdown", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        _opener.open(request, timeout=2).close()
    except (OSError, urllib.error.URLError):
        pass                      # it may close the connection as it goes down; check below
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if not ping(info["url"], timeout=0.3):
            remove_state(state_file)
            return f"Stopped the server at {info['url']}."
        time.sleep(0.05)
    return f"Asked the server at {info['url']} to stop, but it is still answering."
