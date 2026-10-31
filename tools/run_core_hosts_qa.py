"""Sequential no-focus validation of both supported panel hosts."""

import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for version in ("5.2.2", "5.1.2"):
    for host in ("N_PANEL", "PROPERTIES"):
        label = version + "-" + host.lower()
        out = ROOT / "build/core-hosts-v1" / label
        out.mkdir(parents=True, exist_ok=True)
        with (out / "runner.log").open("w") as log:
            p = subprocess.run(
                [
                    sys.executable,
                    "tools/run_blender_tests.py",
                    "--blender",
                    f"/Applications/Blender {version}.app/Contents/MacOS/Blender",
                    "--fixture",
                    "tests/blender_core_hosts.py",
                    "--output",
                    str(out),
                    "--windowed",
                ],
                cwd=ROOT,
                env={**os.environ, "BEYOND_UI_CORE_HOST": host},
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        print(label, "passed" if p.returncode == 0 else "FAILED", flush=True)
        if p.returncode:
            raise SystemExit(p.returncode)
