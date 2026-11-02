"""Verify published artifacts, including after Git's Windows newline handling."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "beyond_ui"


class PackagedNativeTests(unittest.TestCase):
    def test_catalog_matches_shipped_bytes(self):
        native = ROOT / "_native"
        catalog = json.loads((native / "catalog.json").read_text())
        for key, entry in catalog["packages"].items():
            with self.subTest(package=key):
                directory = native / entry["directory"]
                path = directory / "manifest.json"
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    entry["manifest_sha256"],
                )
                manifest = json.loads(path.read_text())
                files = {directory / manifest["library"]: manifest["binary_sha256"]}
                files.update({native / p: h for p, h in manifest["sources"].items()})
                files.update({ROOT / p: h for p, h in manifest["adapters"].items()})
                for file, expected in files.items():
                    self.assertEqual(
                        hashlib.sha256(file.read_bytes()).hexdigest(), expected, str(file)
                    )
