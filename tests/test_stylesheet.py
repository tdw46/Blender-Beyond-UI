import unittest
from beyond_ui import Canvas, StyleSheet, AnimationSettings
from beyond_ui.gpu.style import theme_palette


class StylesheetTests(unittest.TestCase):
    def test_nested_palette_reuses_surface_opacity_and_invalidates_on_edit(self):
        base = theme_palette()
        sheet = StyleSheet(opacity=0.5)
        resolved = sheet.palette(base)
        self.assertIs(sheet.palette(resolved), resolved)
        self.assertIs(sheet.palette(base), resolved)
        self.assertEqual(resolved['field'][3], base['field'][3] * 0.5)
        sheet.update(opacity=0.75)
        updated = sheet.palette(base)
        self.assertIsNot(updated, resolved)
        self.assertIs(sheet.palette(updated), updated)
        self.assertEqual(updated['field'][3], base['field'][3] * 0.75)

    def test_large_heading_reserves_icon_and_wrapped_line_height(self):
        from beyond_ui import Layout

        ui = Layout()
        ui.canvas.panel_layout = True
        StyleSheet(geometry={"font_size": 16, "heading_height": 18}).apply(ui.canvas)
        ui.title(text="Camera animation settings", icon="CAMERA_DATA")
        ui.canvas.arrange(150)
        heading = next(iter(ui.canvas.controls.values()))
        lines = heading.options["_heading_lines"]
        self.assertGreater(len(lines), 1)
        self.assertGreater(heading.options["_heading_icon_gutter"], 0)
        self.assertGreaterEqual(heading.rect[3], len(lines) * 16 * 18 / 11)

    def test_geometry_variants_stay_local_and_follow_live_base_updates(self):
        sheet = StyleSheet(
            geometry={"gap": 6},
            geometry_variants={
                "compact": {"gap": 3, "heading_height": 18, "box_padding": 5}
            },
        )
        compact, ordinary = Canvas(), Canvas()
        sheet.apply(compact, variant="compact")
        sheet.apply(ordinary)
        self.assertEqual((compact.theme.gap, ordinary.theme.gap), (3, 6))
        sheet.update(geometry={"padding": 12})
        self.assertEqual((compact.theme.padding, ordinary.theme.padding), (12, 12))
        self.assertEqual(compact.theme.box_padding, 5)
        sheet.replace(geometry_variants={})
        self.assertEqual(compact.theme.gap, 6)
        self.assertIsNone(compact.theme.box_padding)
        with self.assertRaises(ValueError):
            sheet.apply(ordinary, variant="missing")
        with self.assertRaises(ValueError):
            sheet.update(geometry_variants={"bad": {"gap": -1}})
        with self.assertRaises(ValueError):
            sheet.update(geometry_variants={"": {"gap": 100}})

    def test_structural_disclosure_heading_excludes_help_actions(self):
        from beyond_ui.bindings import Binding

        canvas = Canvas()
        canvas.panel_layout = True
        row = canvas.box().row()
        header = row.toggle(
            "header",
            "Section",
            Binding(lambda: True, lambda v: None),
            bool_button=True,
            icon="TRIA_DOWN",
        )
        row.label("icon", "", icon="CAMERA_DATA")
        help_action = (
            canvas.box()
            .row()
            .toggle(
                "help",
                "Help",
                Binding(lambda: False, lambda v: None),
                bool_button=True,
                icon="TRIA_RIGHT",
            )
        )
        canvas.arrange(300)
        self.assertEqual(header.options["text_role"], "title")
        self.assertEqual(header.options["text_alignment"], "LEFT")
        self.assertNotEqual(help_action.options.get("text_role"), "title")

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

    def test_wrapped_bold_heading_uses_exact_face_and_size(self):
        from beyond_ui import Layout, heading
        ui = Layout()
        heading(ui, 'Back View Plane', font_size=15, line_height=21, wrap=True)
        calls = []
        def measured(text, role):
            raise AssertionError('Sized glyph metrics are available')
        def at_size(text, role, size):
            calls.append((role, size))
            return len(text) * (8 if role == 'title' else 4)
        measured.at_size = at_size
        ui.canvas.set_text_measure(measured, 'heading-regression')
        for width in (120, 160, 220):
            ui.canvas.arrange(width)
            control = next(c for c in ui.canvas.controls.values() if c.label == 'Back View Plane')
            lines = control.options['_wrapped_lines']
            self.assertEqual(' '.join(lines), 'Back View Plane')
            self.assertTrue(all(len(line) * 8 <= control.rect[2] - 12 for line in lines))
        self.assertTrue(calls)
        self.assertEqual(set(calls), {('title', 15)})

    def test_preset_factory_resolves_after_consumer_registration(self):
        from beyond_ui import AddonUI

        first, second = StyleSheet(), StyleSheet(name="Reloaded")
        current = [first]
        factory = lambda: current[0]
        current[0] = second
        self.assertIs(AddonUI("example", stylesheet=factory).stylesheet, second)

class ExplicitThemePriority(unittest.TestCase):
    def test_custom_accents_survive_nested_styles_and_native_mode_returns(self):
        base = theme_palette()
        coral = (241/255, 124/255, 103/255, 1)
        mint = (57/255, 191/255, 165/255, .76)
        sheet = StyleSheet(colors={'accent': coral, 'toggle_on': mint, 'edge': coral})
        p = sheet.palette(base)
        self.assertEqual(p['accent_text'], coral)
        self.assertEqual(p['toggle_on'], mint)
        child = StyleSheet(colors={'field': '#333333'})
        nested = child.palette(p)
        self.assertEqual(nested['accent_text'], coral)
        self.assertEqual(nested['edge'], coral)
        self.assertEqual(nested['toggle_on'], mint)
        sheet.replace(colors={})
        native = sheet.palette(base)
        for role in ('accent', 'accent_text', 'toggle_on', 'slider_fill'):
            self.assertEqual(native[role], base[role])
        self.assertFalse(native['_color_overrides'])

    def test_variant_ink_and_nested_opacity_are_preserved(self):
        from types import SimpleNamespace
        parent=StyleSheet(colors={'accent':'#FFAA00','card':'#11223380'}, opacity=.5,
                          variants={'special':{'accent':'#00FF00','accent_text':'#CCFFCC'}})
        p=parent.palette(theme_palette())
        variant=parent.control_palette(p,SimpleNamespace(options={'style_class':'special'}))
        child=StyleSheet(colors={'text':'#FFFFFF'},opacity=.5)
        result=child.palette(variant)
        self.assertEqual(result['accent_text'],(0.8,1.0,0.8,1.0))
        self.assertAlmostEqual(result['card'][3],p['card'][3]*.5)
