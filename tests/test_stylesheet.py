import unittest
from beyond_ui import Canvas, StyleSheet, AnimationSettings
from beyond_ui.gpu.style import theme_palette


class StylesheetTests(unittest.TestCase):
    def test_constructor_owns_its_tokens_and_export_is_detached(self):
        colors = {"accent": "#FFAA00"}
        sheet = StyleSheet(colors=colors)
        base = theme_palette()
        palette = sheet.palette(base)
        colors["accent"] = "#000000"
        exported = sheet.to_dict()
        exported["colors"]["accent"] = "#FFFFFF"
        self.assertEqual(sheet.to_dict()["colors"]["accent"], "#FFAA00")
        self.assertIs(sheet.palette(base), palette)

    def test_explicit_overlay_keeps_unset_host_colors_and_data_independent(self):
        base = theme_palette()
        sheet = StyleSheet(colors={"accent": "#F17C67"})
        result = sheet.palette(base)
        self.assertEqual(result["text"], base["text"])
        self.assertEqual(result["accent"][:3], (241 / 255, 124 / 255, 103 / 255))
        self.assertIs(sheet.palette(base), result)
        self.assertIsNot(result, base)
        self.assertNotEqual(result["accent"], base["accent"])

    def test_extend_roundtrip_and_transaction_failure(self):
        parent = StyleSheet(colors={"text": "#FFFFFF"}, geometry={"gap": 6})
        child = parent.extend(name="Child", colors={"accent": "#FFAA00"})
        self.assertNotIn("accent", parent.to_dict()["colors"])
        self.assertEqual(
            StyleSheet.from_dict(child.to_dict()).to_dict(), child.to_dict()
        )
        previous = child.to_dict()
        with self.assertRaises(ValueError):
            child.update(geometry={"gap": float("nan")})
        self.assertEqual(child.to_dict(), previous)
        self.assertEqual(child.revision, 0)

    def test_live_size_motion_opacity_and_replace(self):
        sheet = StyleSheet()
        canvas = Canvas()
        sheet.apply(canvas)
        canvas.button("b", "Button", lambda: None)
        canvas.arrange(300)
        sheet.update(geometry={"padding": 14}, motion={"enabled": False}, opacity=0.5)
        self.assertEqual(canvas.theme.padding, 14)
        self.assertFalse(canvas.animation.enabled)
        base = theme_palette()
        result = sheet.palette(base)
        self.assertEqual(result["text"], base["text"])
        self.assertEqual(result["field"][3], base["field"][3] * 0.5)
        sheet.replace(colors={"accent": "#FF0000"})
        sheet.replace(colors={})
        self.assertEqual(sheet.palette(base)["accent"], base["accent"])

    def test_card_geometry_and_operator_variants_are_instance_scoped(self):
        a = StyleSheet(
            cards=True,
            variants={"primary": {"field": "#FF0000"}},
            operators={"test.run": "primary"},
        )
        ca = Canvas()
        a.apply(ca)
        box = ca.box()
        button = box.button("a", "Run", lambda: None, operator_id="test.run")
        ca.arrange(300)
        self.assertEqual(len(ca._style_cards), 1)
        base = a.palette(theme_palette())
        self.assertEqual(a.control_palette(base, button)["field"], (1, 0, 0, 1))
        self.assertNotEqual(
            StyleSheet().palette(theme_palette())["field"], (1, 0, 0, 1)
        )

    def test_motion_speed_preserves_area_and_settles(self):
        from beyond_ui.animation import Motion

        now = [0.0]
        settings = AnimationSettings(speed=2, strength=1)
        motion = Motion(settings, clock=lambda: now[0])
        motion.pulse("a")
        now[0] = 0.05
        shape, _ = motion.sample("a")
        self.assertAlmostEqual(shape[0] * shape[1], 1)
        now[0] = 10
        self.assertFalse(motion.advance())
        for value in (0, float("inf"), -1):
            with self.assertRaises(ValueError):
                settings.speed = value

    def test_live_cards_and_geometry_reset_preserve_open_owner(self):
        sheet = StyleSheet(geometry={"padding": 14}, cards=True)
        canvas = Canvas()
        original = canvas.theme.padding
        sheet.apply(canvas)
        canvas.box().button("b", "Action", lambda: None)
        canvas.arrange(300)
        canvas.overlay = {"widget": object()}
        sheet.replace(geometry={}, cards=False)
        self.assertEqual(canvas.theme.padding, original)
        self.assertIsNotNone(canvas.overlay)
        canvas.arrange(300)
        self.assertEqual(canvas._style_cards, [])

    def test_paragraph_reflows_at_real_width_and_preserves_all_words(self):
        from beyond_ui import Layout

        ui = Layout()
        message = "Requires stable vertex count, order, and topology on every frame."
        control = ui.paragraph(text=message)
        ui.canvas.arrange(150)
        narrow = control.rect[3]
        self.assertEqual(" ".join(control.options["_wrapped_lines"]), message)
        ui.canvas.arrange(500)
        self.assertLess(control.rect[3], narrow)

    def test_preset_factory_resolves_after_consumer_registration(self):
        from beyond_ui import AddonUI

        first, second = StyleSheet(), StyleSheet(name="Reloaded")
        current = [first]
        factory = lambda: current[0]
        current[0] = second
        self.assertIs(AddonUI("example", stylesheet=factory).stylesheet, second)
