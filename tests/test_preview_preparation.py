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
            platform.backend_type_get.return_value = "NONE"
            bank.prepare_tiles(owner, [7])
            self.assertEqual(timers.register.call_count, 2)

    def test_ready_metal_tile_uses_supplied_pixels_and_a_miss_uses_the_live_preview(self):
        bank = PreviewIcons(lambda: ())
        owner = Owner()
        prepared = Mock(return_value=lambda icon: (1, 1, b"abcd") if icon == 1 else None)
        timers = Mock()
        platform = Mock()
        platform.backend_type_get.return_value = "METAL"
        with (patch.dict(sys.modules, bpy=SimpleNamespace(app=SimpleNamespace(background=False, timers=timers)),
                         gpu=SimpleNamespace(platform=platform)),
              patch.object(bank, "_upload_pixels", return_value=("packed", 1)) as packed,
              patch.object(bank, "_preview", return_value="live") as resolve,
              patch.object(bank, "_upload", return_value=("ordinary", 1)) as ordinary):
            bank.prepare_tiles(owner, [1, 2], prepare_pixels=prepared)
            prepared.assert_called_once_with((1, 2))
            self.assertEqual(bank._texture(1, True, None), ("packed", 1))
            packed.assert_called_once_with(1, 1, b"abcd", square=True, letterbox=None)
            resolve.assert_not_called()
            self.assertEqual(bank._texture(2, True, None), ("ordinary", 1))
            ordinary.assert_called_once_with("live", square=True, letterbox=None)
            bank.prepare_tiles(owner, [1, 2], prepare_pixels=prepared)
            prepared.assert_called_once()

    def test_windows_prepares_pixels_without_creating_gpu_resources(self):
        for backend in ("VULKAN", "OPENGL"):
            with self.subTest(backend=backend):
                owner = Owner()
                timers = Mock()
                platform = Mock()
                platform.backend_type_get.return_value = backend
                reads = []

                class Preview:
                    icon_id = 13

                    @property
                    def image_size(self):
                        reads.append(self.icon_id)
                        return 32, 48

                collection = {"pose": Preview()}
                bank = PreviewIcons(lambda: [collection])
                with (patch.object(sys, "platform", "win32"),
                      patch.dict(sys.modules, bpy=SimpleNamespace(app=SimpleNamespace(background=False, timers=timers)),
                                 gpu=SimpleNamespace(platform=platform)),
                      patch.object(bank, "_upload", return_value=("texture", 2/3)) as upload):
                    bank.prepare_tiles(owner, [13, 13])
                    callback, = timers.register.call_args.args
                    self.assertGreater(callback(), 0)
                    self.assertIsNone(callback())
                    self.assertEqual(reads, [13])
                    upload.assert_not_called()
                    bank.prepare_tiles(owner, [13])
                    timers.register.assert_called_once()
                    self.assertEqual(bank._texture(13, True, None), ("texture", 2/3))
                    upload.assert_called_once_with(collection["pose"], square=True, letterbox=None)
