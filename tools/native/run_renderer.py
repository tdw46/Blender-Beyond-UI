"""Run shared GPU paint/glass checks, independently of native ABI availability."""

import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
record = Path(sys.argv[1]).resolve()
backend = sys.argv[2]
build = json.loads(record.read_text())
result = subprocess.run(
    [
        sys.executable,
        str(root / "tools/run_blender_tests.py"),
        "--blender",
        build["blender"],
        "--windowed",
        "--gpu-backend",
        backend,
        "--fixture",
        str(root / "tests/blender_backend_renderer.py"),
        "--output",
        str(record.parent / ("renderer-" + backend)),
    ],
    cwd=root,
)
if result.returncode:
    for log in (record.parent / ("renderer-" + backend)).glob("*.log"):
        print(log.read_text(errors="replace"), flush=True)
raise SystemExit(result.returncode)
