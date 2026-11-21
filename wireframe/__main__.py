import sys

from .cli import main

# Windows consoles often default to a legacy encoding that cannot print every
# label a wireframe may contain; ask for UTF-8 instead.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

sys.exit(main())
