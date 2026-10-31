"""Disposable action/presentation checks and no-focus GPU capture matrix."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/action-parity-v1"
BUILD.mkdir(parents=True, exist_ok=True)


def run(label, version, fixture, windowed=False, **env):
    args = [
        sys.executable,
        "tools/run_blender_tests.py",
        "--blender",
        f"/Applications/Blender {version}.app/Contents/MacOS/Blender",
        "--fixture",
        "tests/" + fixture,
        "--output",
        str(BUILD / label),
    ]
    if windowed:
        args.append("--windowed")
    with (BUILD / (label + ".log")).open("w") as log:
        subprocess.run(
            args,
            cwd=ROOT,
            env={**os.environ, **env},
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print(label, "passed", flush=True)


for suffix, version in (
    () if "--captures-only" in sys.argv else (("", "5.2.2"), ("-51", "5.1.2"))
):
    for label, fixture in (
        ("actions", "blender_action_parity.py"),
        ("popup", "blender_popup_focus.py"),
        ("standalone", "blender_pie_standalone.py"),
        ("general", "blender_runtime.py"),
    ):
        run(label + suffix, version, fixture)
for label, version, dpi in (
    ()
    if "--headless-only" in sys.argv
    else (
        ("1x", "5.2.2", "1"),
        ("15x", "5.2.2", "1.5"),
        ("2x", "5.2.2", "2"),
        ("51", "5.1.2", "1"),
    )
):
    run(
        "run-" + label,
        version,
        "capture_action_parity.py",
        True,
        BEYOND_UI_ACTION_CAPTURE=str(BUILD / ("capture-" + label)),
        BEYOND_UI_CAPTURE_DPI=dpi,
    )
