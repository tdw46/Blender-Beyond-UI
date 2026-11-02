import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import vendor


class VendoringTests(unittest.TestCase):
    def test_cross_platform_record_can_be_replaced_without_losing_edit_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repository"
            library = root / "beyond_ui" / "hosts"
            library.mkdir(parents=True)
            (library / "example.py").write_bytes(b"example\n")
            with patch.object(vendor, "ROOT", root):
                target = vendor.vendor(Path(folder) / "consumer")
                marker = target / vendor.MARKER
                record = json.loads(marker.read_text())
                self.assertIn("hosts/example.py", record["files"])
                self.assertNotIn(b"\r\n", marker.read_bytes())
                # Previously Windows-written records used backslashes. They must
                # remain usable when the next update is authored on either OS.
                record["files"] = {k.replace("/", "\\"): v for k, v in record["files"].items()}
                marker.write_text(json.dumps(record))
                vendor.vendor(target.parent, replace=True)
                changed = target / "hosts/example.py"
                changed.write_bytes(b"user edit\n")
                with self.assertRaisesRegex(ValueError, "edited"):
                    vendor.vendor(target.parent, replace=True)
                self.assertEqual(changed.read_bytes(), b"user edit\n")
