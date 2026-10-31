"""Catch accidental self-fingerprint invalidation before clipboard silently disables."""

import hashlib
import json
from pathlib import Path
import unittest


class NativeAdmission(unittest.TestCase):
    def test_source_matches_audited_adapter(self):
        root = Path(__file__).resolve().parents[1] / "beyond_ui/hosts"
        audit = json.loads((root / "menu-native-audit.json").read_text())
        self.assertEqual(
            hashlib.sha256((root / "menu_native.py").read_bytes()).hexdigest(),
            audit["adapter_sha256"],
            "Native adapter changes require exact-build re-audit, not silent disabling",
        )

    def test_context_adapter_fingerprints(self):
        root = Path(__file__).resolve().parents[1] / "beyond_ui"
        directory = root / "_native/macos-arm64"
        record = json.loads((directory / "menu-context.json").read_text())
        for path, key in (
            (root / "hosts/menu_context.py", "python_adapter_sha256"),
            (root / "_native/menu_context_macos.cpp", "source_sha256"),
            (directory / record["library"], "binary_sha256"),
        ):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record[key])
