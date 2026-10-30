"""Interleave baseline/current dense workloads to investigate timing variation."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/registered-lists"
OUT = BUILD / "perf-repeat"
OUT.mkdir(exist_ok=True)
for version in ("5.2.2", "5.1.2"):
    for index, revision in enumerate(("after", "before", "before", "after")):
        label = f"{version}-{index}-{revision}"
        folder = OUT / label
        with (OUT / (label + ".log")).open("w") as log:
            subprocess.run(
                [
                    sys.executable,
                    "tools/run_blender_tests.py",
                    "--fixture",
                    "tests/benchmark_flow_dense.py",
                    "--output",
                    str(OUT / (label + "-run")),
                    "--blender",
                    f"/Applications/Blender {version}.app/Contents/MacOS/Blender",
                    "--windowed",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "BEYOND_UI_LIBRARY_ROOT": str(
                        BUILD / "baseline" if revision == "before" else ROOT
                    ),
                    "BEYOND_UI_OPERATOR_BENCHMARK": str(folder),
                },
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        data = json.loads((folder / "capture.json").read_text())
        print(label, data["timings"], flush=True)

for version, suffix in (("5.2.2", ""), ("5.1.2", "-51")):
    label = "paired" + suffix
    with (BUILD / (label + "-runner.log")).open("w") as log:
        subprocess.run(
            [
                sys.executable,
                "tools/run_blender_tests.py",
                "--fixture",
                "tests/benchmark_registered_lists_paired.py",
                "--output",
                str(BUILD / (label + "-run")),
                "--blender",
                f"/Applications/Blender {version}.app/Contents/MacOS/Blender",
                "--windowed",
            ],
            cwd=ROOT,
            env={**os.environ, "BEYOND_UI_OPERATOR_BENCHMARK": str(BUILD / label)},
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print(label, "passed", flush=True)
