"""Theme changes must preserve source color semantics and retained resources."""

import unittest
from types import SimpleNamespace as NS

from beyond_ui import Theme
from beyond_ui.gpu import style, skin


def preferences():
    widgets = {}
    for name in ("radio", "regular", "tool", "num", "tab", "numslider", "toggle"):
        widgets["wcol_" + name] = NS(
            inner=(0.12, 0.14, 0.18, 0.9),
            inner_sel=(0.8, 0.2, 0.5, 1),
            text=(0.9, 0.8, 0.7),
            text_sel=(0.01, 0.02, 0.03),
            item=(0.1, 0.7, 0.2, 1),
        )
    return NS(themes=[NS(user_interface=NS(**widgets))])


class ThemeTests(unittest.TestCase):
    def test_native_default_and_live_roles_without_color_conversion(self):
        prefs = preferences()
        ui = prefs.themes[0].user_interface
        palette = style.theme_palette(prefs)
        self.assertEqual(Theme().palette, "BLENDER")
        self.assertEqual(palette["source"], "blender")
        self.assertEqual(palette["fallback_roles"], ())
        self.assertEqual(palette["accent"], (0.8, 0.2, 0.5, 1))
        self.assertEqual(palette["text"], (0.9, 0.8, 0.7, 1))
        self.assertEqual(palette["selected_text"], (0.01, 0.02, 0.03, 1))
        self.assertEqual(palette["curve"], palette["accent"])
        self.assertEqual(palette["surfaces"]["fill"][0][:3], ui.wcol_numslider.item[:3])
        self.assertIs(palette, style.theme_palette(prefs))
        ui.wcol_radio.inner_sel = (0.1, 0.6, 0.3, 1)
        changed = style.theme_palette(prefs)
        self.assertIsNot(changed, palette)
        self.assertEqual(changed["point_selected"], (0.1, 0.6, 0.3, 1))
        self.assertEqual(palette["accent"], (0.8, 0.2, 0.5, 1))
        for name, surface in changed["surfaces"].items():
            self.assertEqual(
                tuple(c[3] for c in surface), tuple(c[3] for c in skin.ROLES[name])
            )

    def test_reference_is_explicit_immutable_and_does_not_leak(self):
        prefs = preferences()
        reference = style.theme_palette(prefs, reference=True)
        self.assertEqual(reference["source"], "reference")
        self.assertEqual(reference["surfaces"]["selected"], skin.ROLES["selected"])
        self.assertNotEqual(reference["text"], style.theme_palette(prefs)["text"])
        with self.assertRaises(TypeError):
            reference["text"] = (0, 0, 0, 0)
        with self.assertRaises(TypeError):
            style.theme_palette(prefs)["surfaces"]["field"] = ()
        with self.assertRaises(ValueError):
            Theme(palette="TYPO")

    def test_missing_invalid_and_removed_rna_falls_back_explicitly(self):
        self.assertEqual(style.theme_palette(None)["source"], "fallback")
        prefs = preferences()
        ui = prefs.themes[0].user_interface
        del ui.wcol_num
        ui.wcol_radio.inner_sel = (float("nan"), 0.2, 0.5, 1)
        palette = style.theme_palette(prefs)
        self.assertEqual(palette["source"], "mixed")
        self.assertEqual(
            set(palette["fallback_roles"]), {"wcol_num.inner", "wcol_radio.inner_sel"}
        )
        self.assertEqual(palette["accent"], (0.025, 0.38, 0.77, 1))

        class Removed:
            @property
            def themes(self):
                raise ReferenceError("removed")

        self.assertEqual(style.theme_palette(Removed())["source"], "fallback")

    def test_signature_cache_is_bounded(self):
        prefs = preferences()
        for i in range(30):
            prefs.themes[0].user_interface.wcol_radio.inner_sel = (i / 30, 0.5, 0.8, 1)
            style.theme_palette(prefs)
        self.assertLessEqual(style._theme_palette.cache_info().currsize, 8)


if __name__ == "__main__":
    unittest.main()
