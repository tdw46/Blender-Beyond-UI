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
    def run_fixture(self, windowed, help_text="--no-window-focus", timeout=False):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            result = output / "result-0.json"
            result.write_text('{"passed": true}')  # A stale success must not survive.
            args = ["runner", "--blender", "/test/blender", "--output", folder]
            if windowed:
                args.append("--windowed")
            process = MagicMock()
            process.pid = 123
            process.__enter__.return_value = process
            process.wait.side_effect = (
                [subprocess.TimeoutExpired("blender", 90), 0] if timeout else [0]
            )
            runner.require_no_focus.cache_clear()
            with (
                patch("sys.argv", args),
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
                command = launch.call_args.args[0]
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

    def test_missing_capability_never_launches_window(self):
        self.run_fixture(True, help_text="")

    def test_timeout_kills_owned_process_and_rejects_stale_result(self):
        self.run_fixture(True, timeout=True)
