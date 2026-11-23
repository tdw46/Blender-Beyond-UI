import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from beyond_ui.widgets.preview_icon import PreviewIcons


class Owner:
    visible = True


class PreviewPreparation(unittest.TestCase):
    def test_page_change_visibility_and_teardown(self):
        bank = PreviewIcons(lambda: ())
        owner = Owner()
        timers = Mock()
        platform = Mock()
        platform.backend_type_get.return_value = "METAL"
        loaded = []

        def upload(icon, tile, letterbox):
            loaded.append(icon)
            bank.textures[icon, "square"] = (object(), 1)

        with patch.dict(sys.modules, bpy=SimpleNamespace(app=SimpleNamespace(background=False, timers=timers)),
                        gpu=SimpleNamespace(platform=platform)), patch.object(bank, "_texture", upload):
            bank.prepare_tiles(owner, [0, 1, 1, 2, 3])
            callback, = timers.register.call_args.args
            self.assertGreater(callback(), 0)
            self.assertEqual(loaded, [1])
            bank.prepare_tiles(owner, [1, 4, 5])
            timers.register.assert_called_once()
            self.assertGreater(callback(), 0)
            self.assertEqual(loaded, [1, 4])
            owner.visible = False
            self.assertIsNone(callback())
            self.assertEqual(loaded, [1, 4])
            owner.visible = True
            bank.prepare_tiles(owner, [1, 4])
            timers.register.assert_called_once()
            bank.prepare_tiles(owner, [6])
            bank.cancel_preparation()
            timers.unregister.assert_called_once()
            self.assertIsNone(bank._warm_callback)
            platform.backend_type_get.return_value = "VULKAN"
            bank.prepare_tiles(owner, [7])
            self.assertEqual(timers.register.call_count, 2)
