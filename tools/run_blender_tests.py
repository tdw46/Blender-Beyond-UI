"""Isolated Blender execution, with timeout and mandatory result markers."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from functools import lru_cache
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def windows_fault_dialog_policy():
    """Only child processes inherit suppression; restore this runner on exit."""
    if os.name != "nt":
        yield
        return
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetErrorMode.restype = ctypes.c_uint
    kernel.SetErrorMode.argtypes = (ctypes.c_uint,)
    kernel.SetErrorMode.restype = ctypes.c_uint
    previous = kernel.GetErrorMode()
    # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX.
    kernel.SetErrorMode(previous | 0x0001 | 0x0002 | 0x8000)
    try:
        yield
    finally:
        kernel.SetErrorMode(previous)


def require_windowed_admission():
    """Require current launch authorization, separate from focus-safety evidence."""
    path = ROOT / "docs/WINDOWED_TEST_STATUS.json"
    if not path.is_file():
        raise RuntimeError("Windowed tests require an explicit focus admission record")
    status = json.loads(path.read_text())
    if status.get("admitted") is not True:
        raise RuntimeError(
            "Windowed tests suspended: " + status.get("reason", "No focus admission")
        )


@lru_cache(maxsize=8)
def require_no_focus(executable):
    """Fail closed before opening a window on an unqualified executable."""
    help_text = subprocess.run(
        [executable, "--help"], capture_output=True, text=True, timeout=15, check=True
    ).stdout
    if "--no-window-focus" not in help_text:
        raise RuntimeError("Windowed testing requires Blender --no-window-focus")
    return help_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", action="append", required=True)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--gpu-backend", choices=("metal", "opengl", "vulkan"))
    parser.add_argument("--debug-gpu", action="store_true",
                        help="Enable Blender GPU diagnostics; do not use for performance acceptance")
    parser.add_argument(
        "--macos-noactivate",
        action="store_true",
        help="Use nonactivating LaunchServices launch with observation-only focus audit",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=90,
                        help="Bounded per-process timeout in seconds (1–900)")
    parser.add_argument(
        "--fixture", type=Path, help="Explicit disposable-profile test script"
    )
    args = parser.parse_args()
    if not 1 <= args.timeout <= 900:
        parser.error("--timeout must be between 1 and 900 seconds")
    if args.windowed:
        require_windowed_admission()
    output = args.output or Path(tempfile.mkdtemp(prefix="beyond-ui-tests-"))
    output = output.resolve()
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
        # Recovery files (quit.blend) must not overwrite another session's temp.
        temporary = profile / "temp"
        temporary.mkdir(parents=True, exist_ok=True)
        env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(temporary)
        result = output / f"result-{i}.json"
        result.unlink(missing_ok=True)
        log = output / f"blender-{i}.log"
        env["BEYOND_UI_TEST_RESULT"] = str(result)
        command = [executable, "--factory-startup", "--python-exit-code", "1"]
        if not args.windowed:
            command += ["--background"]
        else:
            executable_help = require_no_focus(executable)
            command += ["--no-window-focus", "--enable-event-simulate"]
            if sys.platform == "win32":
                # Native crashes must report to the retained log, not raise a
                # foreground error dialog over the user's current application.
                if "--console-crash-handler" in executable_help:
                    command.append("--console-crash-handler")
                # GHOST's maximized ShowWindow path uses SW_SHOWMAXIMIZED even
                # with --no-window-focus. A normal window honors SW_SHOWNOACTIVATE.
                command += ["--window-geometry", "80", "80", "1280", "900"]
        if args.gpu_backend:
            command += ["--gpu-backend", args.gpu_backend]
            env["BEYOND_UI_EXPECT_BACKEND"] = args.gpu_backend.upper()
        if args.debug_gpu:
            command.append("--debug-gpu")
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
        launch_command = command
        launch_report = output / f"launch-{i}.json"
        if args.macos_noactivate:
            if not args.windowed or sys.platform != "darwin":
                raise RuntimeError(
                    "LaunchServices capture requires a macOS windowed test"
                )
            launcher = ROOT / "build/focus-audit/launch-blender"
            if not launcher.is_file():
                raise RuntimeError(
                    "Compile tools/launch_blender_macos.swift before using this mode"
                )
            source = ROOT / "tools/launch_blender_macos.swift"
            if launcher.stat().st_mtime < source.stat().st_mtime:
                raise RuntimeError(
                    "Recompile the changed macOS test launcher before using this mode"
                )
            env["BEYOND_UI_TEST_LOG"] = str(log.resolve())
            command[-2:-2] = [
                "--python-expr",
                "import os,sys; sys.stdout=open(os.environ['BEYOND_UI_TEST_LOG'],'a',buffering=1); sys.stderr=sys.stdout",
            ]
            # Cocoa argument-domain defaults are process-local. Ignore crash
            # restoration for this disposable instance without changing user defaults.
            command += ["--", "-ApplePersistenceIgnoreState", "YES"]
            config = output / f"launch-config-{i}.json"
            config.write_text(
                json.dumps({"command": command, "report": str(launch_report.resolve())})
            )
            launch_report.unlink(missing_ok=True)
            launch_command = [str(launcher), str(config.resolve())]
        try:
            with log.open("w") as stream:
                with windows_fault_dialog_policy(), subprocess.Popen(
                    launch_command,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    **({"creationflags": subprocess.CREATE_NO_WINDOW}
                       if sys.platform == "win32" else {}),
                ) as process:
                    pid = process.pid
                    try:
                        code = process.wait(timeout=args.timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise
        except subprocess.TimeoutExpired:
            code = "timeout"
        launch = (
            json.loads(launch_report.read_text())
            if args.macos_noactivate and launch_report.exists()
            else None
        )
        if launch:
            pid = launch["pid"]
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
            "launch": launch,
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
