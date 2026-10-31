"""Sequential disposable-profile marking-menu checks, preserving desktop focus."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu"
BASE = BUILD / "baseline"
BASE.mkdir(parents=True, exist_ok=True)
archive = subprocess.run(
    ["git", "archive", "6337e8e5fddc8b0db6dd134f4597e73d7441a3ed"],
    cwd=ROOT,
    capture_output=True,
    check=True,
).stdout
subprocess.run(["tar", "-x", "-C", str(BASE)], input=archive, check=True)


def run(label, fixture, executable, windowed=False, **variables):
    only = os.environ.get("BEYOND_UI_QA_ONLY", "")
    if only and not any(label.startswith(prefix) for prefix in only.split(",")):
        return
    args = [
        sys.executable,
        "tools/run_blender_tests.py",
        "--blender",
        executable,
        "--fixture",
        f"tests/{fixture}",
        "--output",
        str(BUILD / label),
    ]
    if windowed:
        args.append("--windowed")
    with (BUILD / (label + ".log")).open("w") as log:
        subprocess.run(
            args,
            cwd=ROOT,
            env={**os.environ, **variables},
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    data = json.loads((BUILD / label / "summary.json").read_text())
    print(label, all(r["passed"] for r in data), flush=True)


for suffix, version in (("", "5.2.2"), ("-51", "5.1.2")):
    exe = f"/Applications/Blender {version}.app/Contents/MacOS/Blender"
    run("runtime" + suffix, "blender_pie.py", exe)
    run("compound" + suffix, "blender_pie_compound.py", exe)
    run("general" + suffix, "blender_runtime.py", exe)

# Windowed GPU/input evidence is opt-in; standing authorization and no-focus
# capability checks remain enforced by the shared runner.
if os.environ.get("BEYOND_UI_MARKING_WINDOWED") == "1":
    for label, version, dpi, frames in (
        ("capture-1x", "5.2.2", "1", "60"),
        ("capture-15x", "5.2.2", "1.5", "12"),
        ("capture-2x", "5.2.2", "2", "12"),
        ("capture-51", "5.1.2", "1", "12"),
    ):
        run(label, "capture_pie_compound.py",
            f"/Applications/Blender {version}.app/Contents/MacOS/Blender", True,
            BEYOND_UI_PIE_CAPTURE=str(ROOT / "build/marking-menu-v3" / label),
            BEYOND_UI_CAPTURE_DPI=dpi, BEYOND_UI_PIE_FRAMES=frames)
    for suffix, version in (("", "5.2.2"), ("-51", "5.1.2")):
        run("windowed" + suffix, "blender_registered_menus_windowed.py",
            f"/Applications/Blender {version}.app/Contents/MacOS/Blender", True)
