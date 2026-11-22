# 0011. The server stops itself when idle, and is stopped over HTTP via a state file

Status: accepted (Round 4). Requirement: R12.

**In the context of** an assistant starting servers that must not be left running,
**facing** that a forgotten server keeps a port and a process for ever, **we decided
for** three parts: a watcher thread that shuts the server down after 300 seconds
without any request (the editor sends a heartbeat every 60 s), a state file
(`.wireframe-server.json`: pid, port, url, file) so `start`, `status` and `stop` can
find it, and `stop` asking the server to quit with `POST /api/shutdown`, **and
neglected** killing by pid (a stale pid may belong to an unrelated program), a
dedicated ping route only (a refused or 404 request would not count, though it proves
the server is alive), and no heartbeat (an editor left open while someone thinks would
be shut down), **to achieve** a server that cleans up after itself and can be stopped
safely by a command, **accepting** that a browser tab left open stops pinging if the
server dies, so the editor shows a message, and that the state file can be left behind
after a crash (`status` removes a stale one).

## Consequences you can check yourself

- `python -m wireframe start`, then `status`, then `stop`; the state file appears and
  disappears.
- `python -m wireframe start --idle-timeout 5`, wait, then `status`: it is gone.
