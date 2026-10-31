"""Current-source review captures in isolated no-focus Blender processes."""

import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = (
    Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/core-review-v1"
)
BUILD.mkdir(parents=True, exist_ok=True)
for label, version, scale, fixture, capture_variable in (
    ("1x", "5.2.2", "1", "capture_action_parity.py", "BEYOND_UI_ACTION_CAPTURE"),
    ("15x", "5.2.2", "1.5", "capture_action_parity.py", "BEYOND_UI_ACTION_CAPTURE"),
    ("2x", "5.2.2", "2", "capture_action_parity.py", "BEYOND_UI_ACTION_CAPTURE"),
    ("51", "5.1.2", "1", "capture_action_parity.py", "BEYOND_UI_ACTION_CAPTURE"),
    ("scalar", "5.2.2", "1", "capture_scalar_layout.py", "BEYOND_UI_SCALAR_CAPTURE"),
):
    with (BUILD / (label + ".log")).open("w") as log:
        subprocess.run(
            [
                sys.executable,
                "tools/run_blender_tests.py",
                "--blender",
                f"/Applications/Blender {version}.app/Contents/MacOS/Blender",
                "--fixture",
                "tests/" + fixture,
                "--windowed",
                *(["--macos-noactivate"] if os.environ.get("BEYOND_UI_MACOS_NOACTIVATE") == "1" else []),
                "--output",
                str(BUILD / ("run-" + label)),
            ],
            cwd=ROOT,
            env={
                **os.environ,
                capture_variable: str(BUILD / ("capture-" + label)),
                "BEYOND_UI_CAPTURE_DPI": scale,
                "BEYOND_UI_CORE_REVIEW": "1" if label == "1x" else "0",
            },
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print(label, "passed", flush=True)
