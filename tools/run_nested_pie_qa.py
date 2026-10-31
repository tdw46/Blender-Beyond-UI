"""Sequential disposable nested-pie checks; mandatory no-focus windows via runner."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu-v4"
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


for suffix, version in (("", "5.2.2"), ("-51", "5.1.2")):
    run("nested" + suffix, version, "blender_pie_nested.py")
    run("compound" + suffix, version, "blender_pie_compound.py")
    run("general" + suffix, version, "blender_runtime.py")
for label, version, dpi, frames in (
    ("1x", "5.2.2", "1", "96"),
    ("15x", "5.2.2", "1.5", "16"),
    ("2x", "5.2.2", "2", "16"),
    ("51", "5.1.2", "1", "16"),
):
    run(
        "run-" + label,
        version,
        "capture_pie_nested.py",
        True,
        BEYOND_UI_PIE_CAPTURE=str(BUILD / ("capture-" + label)),
        BEYOND_UI_CAPTURE_DPI=dpi,
        BEYOND_UI_PIE_FRAMES=frames,
    )
for suffix, version in (("", "5.2.2"), ("-51", "5.1.2")):
    run("windowed" + suffix, version, "blender_nested_menus_windowed.py", True)
