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
        from beyond_ui.gpu.contrast import ratio, over
        self.assertGreaterEqual(ratio(palette["selected_text"], over(palette["selected"], palette["card"])), 4.5)
        self.assertEqual(palette["curve"], palette["point_selected"])
        self.assertEqual(palette["surfaces"]["fill"][0][:3], ui.wcol_numslider.item[:3])
        self.assertIs(palette, style.theme_palette(prefs))
        ui.wcol_radio.inner_sel = (0.1, 0.6, 0.3, 1)
        changed = style.theme_palette(prefs)
        self.assertIsNot(changed, palette)
        self.assertNotEqual(changed["point_selected"], palette["point_selected"])
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

    def test_readable_inks_preserve_native_fill_hue_and_glass(self):
        from beyond_ui.gpu.contrast import backgrounds, ratio, over
        from colorsys import rgb_to_hsv
        prefs=preferences();u=prefs.themes[0].user_interface
        for light in (False,True):
            base=(.85,.85,.85,.9) if light else (.14,.14,.14,.9)
            text=(.12,.12,.12) if light else (.77,.77,.77)
            for name in ('regular','tool','num','numslider','toggle'):
                getattr(u,'wcol_'+name).inner=base
            u.wcol_regular.text=text
            u.wcol_radio.inner_sel=(.46,.24,.72,1)
            p=style.theme_palette(prefs)
            for bg in backgrounds(p):
                self.assertGreaterEqual(ratio(p['accent_text'],bg),4.5-1e-5)
                self.assertGreaterEqual(ratio(p['text'],bg),4.5-1e-5)
                self.assertGreaterEqual(ratio(p['muted'],bg),3.5-1e-5)
            self.assertEqual(p['accent'],u.wcol_radio.inner_sel)
            self.assertAlmostEqual(rgb_to_hsv(*p['accent'][:3])[0],rgb_to_hsv(*p['accent_text'][:3])[0])
            self.assertLess(p['bg'][3],1)
            self.assertGreater(p['header_divider'][3],.28)
            if light:self.assertGreater(p['input'][0],.8)

    def test_explicit_ink_override_and_data_colors_are_not_rewritten(self):
        from beyond_ui import StyleSheet
        base=style.theme_palette(preferences())
        override=(.8,.2,.3,1)
        sheet=StyleSheet(colors={'accent_text':override})
        resolved=sheet.palette(base)
        self.assertEqual(resolved['accent_text'],override)
        self.assertEqual(resolved['slider_fill'],base['slider_fill'])
        self.assertIs(resolved,sheet.palette(base))

    def test_vivid_accent_retains_more_saturation_at_same_contrast(self):
        from colorsys import rgb_to_hsv
        from beyond_ui.gpu.contrast import readable, backgrounds, ratio
        p=style.theme_palette(preferences())
        grounds=backgrounds(p)
        purple=(.46,.24,.72,1)
        old=readable(purple,grounds)
        vivid=readable(purple,grounds,vivid=True)
        self.assertGreater(rgb_to_hsv(*vivid[:3])[1],rgb_to_hsv(*old[:3])[1])
        self.assertAlmostEqual(rgb_to_hsv(*vivid[:3])[0],rgb_to_hsv(*purple[:3])[0])
        for bg in grounds:self.assertGreaterEqual(ratio(vivid,bg),4.5-1e-5)
        self.assertEqual(readable(vivid,grounds,vivid=True),vivid)
        light=((.95,.95,.95,1),)
        dark=readable(purple,light,vivid=True)
        self.assertGreaterEqual(ratio(dark,light[0]),4.5-1e-5)
        self.assertAlmostEqual(rgb_to_hsv(*dark[:3])[1],rgb_to_hsv(*purple[:3])[1])

    def test_active_value_preserves_full_theme_saturation(self):
        from colorsys import rgb_to_hsv
        from beyond_ui import StyleSheet
        p=style.theme_palette(preferences())
        source=rgb_to_hsv(*p['accent'][:3])
        active=rgb_to_hsv(*p['value_change'][:3])
        self.assertAlmostEqual(source[0],active[0])
        self.assertAlmostEqual(source[1],active[1])
        self.assertAlmostEqual(active[2],max(p['accent_text'][:3]))
        self.assertGreaterEqual(active[1],rgb_to_hsv(*p['accent_text'][:3])[1])
        custom=(.95,.4,.1,1)
        sheet=StyleSheet(colors={'accent':custom})
        self.assertEqual(sheet.palette(p)['value_change'],custom)
        sheet.replace(colors={'accent':custom,'value_change':(.1,.9,.4,1)})
        self.assertEqual(sheet.palette(p)['value_change'],(.1,.9,.4,1))

    def test_signature_cache_is_bounded(self):
        prefs = preferences()
        for i in range(30):
            prefs.themes[0].user_interface.wcol_radio.inner_sel = (i / 30, 0.5, 0.8, 1)
            style.theme_palette(prefs)
        self.assertLessEqual(style._theme_palette.cache_info().currsize, 8)


if __name__ == "__main__":
    unittest.main()
