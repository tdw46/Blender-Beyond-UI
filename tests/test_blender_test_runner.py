import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools import run_blender_tests as runner


class BlenderTestRunner(unittest.TestCase):
    def run_fixture(
        self, windowed, help_text="--no-window-focus", timeout=False, macos=False, windows=False
    ):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            result = output / "result-0.json"
            result.write_text('{"passed": true}')  # A stale success must not survive.
            args = ["runner", "--blender", "/test/blender", "--output", folder]
            if windowed:
                args.append("--windowed")
            if macos:
                args.append("--macos-noactivate")
                source = output / "tools/launch_blender_macos.swift"
                source.parent.mkdir()
                source.touch()
                launcher = output / "build/focus-audit/launch-blender"
                launcher.parent.mkdir(parents=True)
                launcher.touch()
            process = MagicMock()
            process.pid = 123
            process.__enter__.return_value = process
            process.wait.side_effect = (
                [subprocess.TimeoutExpired("blender", 90), 0] if timeout else [0]
            )
            runner.require_no_focus.cache_clear()
            with (
                patch("sys.argv", args),
                patch("sys.platform", "win32" if windows else "darwin"),
                patch.object(runner.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True),
                patch.object(runner, "ROOT", output if macos else runner.ROOT),
                # These are mocked-process tests; no Blender windows are launched.
                patch.object(runner, "require_windowed_admission"),
                patch.object(
                    runner.subprocess, "run", return_value=MagicMock(stdout=help_text)
                ),
                patch.object(
                    runner.subprocess, "Popen", return_value=process
                ) as launch,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                if windowed and not help_text:
                    with self.assertRaisesRegex(RuntimeError, "requires"):
                        runner.main()
                    launch.assert_not_called()
                    return
                with self.assertRaises(SystemExit) as exit:
                    runner.main()
                self.assertEqual(exit.exception.code, 1)
                self.assertFalse(result.exists())
                summary = json.loads((output / "summary.json").read_text())[0]
                self.assertFalse(summary["passed"])
                self.assertEqual(summary["pid"], 123)
                command = summary["command"]
                if windows:
                    self.assertEqual(launch.call_args.kwargs["creationflags"], 0x08000000)
                    if windowed:
                        pos = command.index("--window-geometry")
                        self.assertEqual(command[pos + 1:pos + 5], ["80", "80", "1280", "900"])
                        self.assertLess(pos, command.index("--python"))
                else:
                    self.assertNotIn("creationflags", launch.call_args.kwargs)
                    self.assertNotIn("--window-geometry", command)
                if macos:
                    self.assertEqual(
                        command[-3:], ["--", "-ApplePersistenceIgnoreState", "YES"]
                    )
                    self.assertLess(command.index("--python"), command.index("--"))
                if windowed:
                    self.assertIn("--no-window-focus", command)
                    self.assertLess(
                        command.index("--no-window-focus"), command.index("--python")
                    )
                    self.assertNotIn("--background", command)
                else:
                    self.assertIn("--background", command)
                if timeout:
                    process.kill.assert_called_once()
                    self.assertEqual(summary["returncode"], "timeout")

    def test_headless_default_rejects_stale_success(self):
        self.run_fixture(False)

    def test_windowed_launch_never_omits_no_focus(self):
        self.run_fixture(True)

    def test_windows_uses_normal_nonactivating_window_without_console(self):
        self.run_fixture(True, windows=True)

    def test_macos_restoration_override_is_process_local_and_after_blender_args(self):
        self.run_fixture(True, macos=True)

    def test_missing_capability_never_launches_window(self):
        self.run_fixture(True, help_text="")

    def test_timeout_kills_owned_process_and_rejects_stale_result(self):
        self.run_fixture(True, timeout=True)

    def test_revoked_admission_blocks_before_any_process_launch(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(runner, "ROOT", Path(folder)),
            patch("sys.argv", ["runner", "--windowed", "--blender", "/test/blender"]),
            patch.object(runner.subprocess, "Popen") as launch,
            patch.object(runner.subprocess, "run") as probe,
        ):
            status = Path(folder) / "docs/WINDOWED_TEST_STATUS.json"
            status.parent.mkdir()
            status.write_text('{"admitted": false, "reason": "Revoked"}')
            with self.assertRaisesRegex(RuntimeError, "Windowed tests suspended"):
                runner.main()
            launch.assert_not_called()
            probe.assert_not_called()

    def test_missing_focus_admission_fails_closed(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(runner, "ROOT", Path(folder)),
        ):
            with self.assertRaisesRegex(RuntimeError, "explicit focus admission"):
                runner.require_windowed_admission()

    def test_standing_authorization_admits_current_no_focus_route(self):
        runner.require_windowed_admission()
        status = json.loads(
            (runner.ROOT / "docs/WINDOWED_TEST_STATUS.json").read_text()
        )
        self.assertIn("authorization", status)
        self.assertTrue(status["prior_focus_failure"]["user_confirmed"])
