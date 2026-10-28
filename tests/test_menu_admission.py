import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from beyond_ui.hosts import menu_native


class MenuAdmission(unittest.TestCase):
    def tearDown(self):
        menu_native.api.cache_clear()

    def test_unknown_platform_and_build_never_load_native_symbols(self):
        fake = SimpleNamespace(app=SimpleNamespace(build_hash=b"unqualified"))
        with (
            patch.dict(sys.modules, bpy=fake),
            patch.object(menu_native.C, "CDLL") as load,
        ):
            with patch.object(menu_native.platform, "system", return_value="Linux"):
                self.assertIsNone(menu_native.api())
                self.assertIn("platform", menu_native.reason())
            menu_native.api.cache_clear()
            with (
                patch.object(menu_native.platform, "system", return_value="Darwin"),
                patch.object(menu_native.platform, "machine", return_value="arm64"),
            ):
                self.assertIsNone(menu_native.api())
                self.assertIn("build", menu_native.reason())
            load.assert_not_called()

    def test_source_mismatch_fails_before_binary_access(self):
        fake = SimpleNamespace(app=SimpleNamespace(build_hash=b"d13f752e3b9c"))
        with (
            patch.dict(sys.modules, bpy=fake),
            patch.object(menu_native.platform, "system", return_value="Darwin"),
            patch.object(menu_native.platform, "machine", return_value="arm64"),
            patch.object(
                menu_native.Path,
                "read_text",
                return_value=json.dumps({"adapter_sha256": "invalid"}),
            ),
            patch.object(menu_native.C, "CDLL") as load,
        ):
            self.assertIsNone(menu_native.api())
            self.assertIn("source fingerprint", menu_native.reason())
            load.assert_not_called()


class GlassLifetime(unittest.TestCase):
    def test_shared_resources_live_until_last_host_releases(self):
        from beyond_ui.gpu import glass

        shader = object()
        with (
            patch.object(glass, "_owners", {"a": {}, "b": {}}),
            patch.object(glass, "_views", {"view": object()}),
            patch.object(glass, "_lens_batches", {"batch": object()}),
            patch.object(glass, "_lens_shader", shader),
        ):
            glass.release("a")
            self.assertEqual(set(glass._owners), {"b"})
            self.assertIs(glass._lens_shader, shader)
            self.assertTrue(glass._lens_batches)
            glass.release("b")
            self.assertFalse(glass._owners)
            self.assertFalse(glass._views)
            self.assertFalse(glass._lens_batches)
            self.assertIsNone(glass._lens_shader)
