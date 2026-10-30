"""Isolated Blender execution, with timeout and mandatory result markers."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=8)
def require_no_focus(executable):
    """Fail closed before opening a window on an unqualified executable."""
    help_text = subprocess.run(
        [executable, "--help"], capture_output=True, text=True, timeout=15, check=True
    ).stdout
    if "--no-window-focus" not in help_text:
        raise RuntimeError("Windowed testing requires Blender --no-window-focus")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", action="append", required=True)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fixture", type=Path, help="Explicit disposable-profile test script"
    )
    args = parser.parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix="beyond-ui-tests-"))
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for i, executable in enumerate(args.blender):
        profile = output / f"profile-{i}"
        env = dict(os.environ)
        for key, folder in [
            ("BLENDER_USER_CONFIG", "config"),
            ("BLENDER_USER_SCRIPTS", "scripts"),
            ("BLENDER_USER_EXTENSIONS", "extensions"),
        ]:
            path = profile / folder
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        result = output / f"result-{i}.json"
        result.unlink(missing_ok=True)
        log = output / f"blender-{i}.log"
        env["BEYOND_UI_TEST_RESULT"] = str(result)
        command = [executable, "--factory-startup", "--python-exit-code", "1"]
        if not args.windowed:
            command += ["--background"]
        else:
            require_no_focus(executable)
            command += ["--no-window-focus", "--enable-event-simulate"]
        command += [
            "--python",
            str(
                args.fixture.resolve()
                if args.fixture
                else ROOT
                / "tests"
                / ("blender_windowed.py" if args.windowed else "blender_runtime.py")
            ),
        ]
        try:
            with log.open("w") as stream:
                with subprocess.Popen(
                    command,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                ) as process:
                    pid = process.pid
                    try:
                        code = process.wait(timeout=90)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise
        except subprocess.TimeoutExpired:
            code = "timeout"
        record = json.loads(result.read_text()) if result.exists() else {}
        passed = (
            code == 0
            and record.get("passed") is True
            and "Traceback" not in log.read_text()
        )
        summary = {
            "blender": str(executable),
            "pid": pid,
            "command": command,
            "focus_policy": "no-window-focus" if args.windowed else "headless",
            "passed": passed,
            "returncode": code,
            "result": record,
            "log": str(log),
        }
        results.append(summary)
        print(json.dumps(summary), flush=True)
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    raise SystemExit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
