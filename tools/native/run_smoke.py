"""Run only the owned disposable Blender runtime produced by the native builder."""

import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
record = Path(sys.argv[1]).resolve()
build = json.loads(record.read_text())
result = subprocess.run(
    [
        sys.executable,
        str(root / "tools/run_blender_tests.py"),
        "--blender",
        build["blender"],
        "--fixture",
        str(root / "tests/blender_portable_bridge.py"),
        "--output",
        str(record.parent / "smoke"),
    ],
    cwd=root,
)
if result.returncode:
    for log in (record.parent / "smoke").glob("*.log"):
        print(log.read_text(errors="replace"), flush=True)
    raise SystemExit(result.returncode)
