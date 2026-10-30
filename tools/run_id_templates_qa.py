"""Run isolated ID-template evidence in sequence; never share GPU fixtures."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/id-templates"
BUILD.mkdir(parents=True, exist_ok=True)
BASE = BUILD / "baseline"
BASE.mkdir(exist_ok=True)
archive = subprocess.run(
    ["git", "archive", "8a321cb"], cwd=ROOT, check=True, capture_output=True
).stdout
subprocess.run(["tar", "-x", "-C", str(BASE)], input=archive, check=True)
blenders = [
    "/Applications/Blender 5.2.2.app/Contents/MacOS/Blender",
    "/Applications/Blender 5.1.2.app/Contents/MacOS/Blender",
]


waiting = os.environ.get("BEYOND_UI_QA_START")


def run(label, fixture, executable, windowed=False, **variables):
    global waiting
    if waiting and label != waiting:
        return
    waiting = None
    args = [
        sys.executable,
        "tools/run_blender_tests.py",
        "--fixture",
        f"tests/{fixture}",
        "--output",
        str(BUILD / label),
        "--blender",
        executable,
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


for suffix, executable in zip(("", "-51"), blenders):
    for dpi in ("1", "1.5", "2"):
        label = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        run(
            label + "-run",
            "capture_id_templates.py",
            executable,
            True,
            BEYOND_UI_ID_CAPTURE=str(BUILD / label),
            BEYOND_UI_CAPTURE_DPI=dpi,
        )
    for revision in ("before", "after"):
        label = "benchmark-" + revision + suffix
        run(
            label + "-run",
            "benchmark_operator_enums.py",
            executable,
            True,
            BEYOND_UI_OPERATOR_BENCHMARK=str(BUILD / label),
            BEYOND_UI_LIBRARY_ROOT=str(BASE if revision == "before" else ROOT),
        )
    for revision in ("before", "after"):
        label = "dense-" + revision + suffix
        run(
            label + "-run",
            "benchmark_flow_dense.py",
            executable,
            True,
            BEYOND_UI_OPERATOR_BENCHMARK=str(BUILD / label),
            BEYOND_UI_LIBRARY_ROOT=str(BASE if revision == "before" else ROOT),
        )
    for label, fixture in (
        ("runtime", "blender_id_templates.py"),
        ("windowed", "blender_id_templates_windowed.py"),
        ("general", "blender_runtime.py"),
        ("pointer", "blender_pointer_decorator.py"),
    ):
        run(label + suffix, fixture, executable, label in {"runtime", "windowed"})
