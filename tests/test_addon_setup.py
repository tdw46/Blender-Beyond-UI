"""Consumer lifecycle and vendor safety contracts outside Blender."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from beyond_ui import AddonUI

ROOT = Path(__file__).resolve().parents[1]


class AddonSetup(unittest.TestCase):
    def test_import_has_no_blender_or_gpu_side_effects(self):
        code = "import sys; from beyond_ui import AddonUI; ui=AddonUI('consumer'); assert 'bpy' not in sys.modules; assert 'gpu' not in sys.modules; assert 'beyond_ui.hosts.addon' not in sys.modules; assert not ui.status['registered']"
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)

    def test_invalid_configuration_rejected_without_startup(self):
        with self.assertRaises(ValueError):
            AddonUI("")
        with self.assertRaises(ValueError):
            AddonUI("consumer", layout_options={"unknown": True})
        ui = AddonUI("consumer")
        ui.unregister()
        ui.refresh()
        self.assertEqual(ui.status, {"registered": False, "panels": {}})

    def test_vendor_records_assets_and_rejects_unowned_destination(self):
        spec = importlib.util.spec_from_file_location(
            "vendor_tool", ROOT / "tools/vendor.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "_vendor"
            target = module.vendor(parent)
            self.assertTrue((target / "LICENSE").is_file())
            self.assertTrue((target / "NOTICE").is_file())
            self.assertTrue((target / "assets/fonts/Inter-Regular.woff2").is_file())
            import json, hashlib

            record = json.loads((target / module.MARKER).read_text())
            self.assertEqual(
                record["files"]["addon.py"],
                hashlib.sha256((target / "addon.py").read_bytes()).hexdigest(),
            )
            with self.assertRaises(ValueError):
                module.vendor(parent)
            (target / "addon.py").write_text("# consumer local edit")
            with self.assertRaises(ValueError):
                module.vendor(parent, replace=True)
            self.assertEqual((target / "addon.py").read_text(), "# consumer local edit")
            marker = target / module.MARKER
            marker.unlink()
            with self.assertRaises(ValueError):
                module.vendor(parent, replace=True)
            (target / "keep.txt").write_text("Unowned work")
            self.assertEqual((target / "keep.txt").read_text(), "Unowned work")
