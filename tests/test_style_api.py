import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout, StyleSheet, style, prop
from beyond_ui.bindings import Binding
from beyond_ui.layout_recording import Tape
from beyond_ui.style_api import normalize
from test_numeric import codec


class InlineStyleTests(unittest.TestCase):
    def number(self, ui, key="n", unit="NONE"):
        return ui.group.number(
            key,
            "Value",
            Binding(lambda: 1.234567, lambda v: None),
            numeric=codec(unit=unit),
            slider=False,
        )

    def test_native_noop_and_wrapper_does_not_forward_style_keywords(self):
        class Native:
            def prop(self, data, name, **kw):
                self.last = (data, name, kw)
                return None

        ui = Native()
        self.assertIs(style(ui, padding=8, units="mm"), ui)
        prop(ui, "owner", "lens", text="Lens", style={"units": "mm"})
        self.assertEqual(ui.last, ("owner", "lens", {"text": "Lens"}))

    def test_tape_replay_and_signature_detect_style_changes(self):
        tape = Tape()
        row = tape.root.row()
        row.label(text="Hello")
        style(row, padding=(2, 7), font_weight="bold")
        ui = Layout()
        tape.play(ui)
        ui.canvas.arrange(300)
        c = next(iter(ui.canvas.controls.values()))
        self.assertEqual(c.options["font_weight"], "bold")
        self.assertEqual(c.rect[:2], (15, 10))
        other = Tape()
        r = other.root.row()
        r.label(text="Hello")
        style(r, padding=3)
        self.assertNotEqual(tape.signature, other.signature)

    def test_presets_are_detached_and_unknown_properties_rejected(self):
        preset = {"colors": {"text": "#FFFFFF"}, "padding": (2, 4)}
        result = normalize(preset, colors={"accent": "#123456"})
        self.assertEqual(set(result["colors"]), {"text", "accent"})
        result["colors"]["text"] = (0, 0, 0, 1)
        self.assertEqual(preset["colors"]["text"], "#FFFFFF")
        for options in (
            {"paddding": 3},
            {"width": float("nan")},
            {"gap": -1},
            {"motion": {"speed": 0}},
            {"min_width": 100, "max_width": 50},
        ):
            with self.assertRaises(ValueError):
                normalize(options)

    def test_formatting_is_local_lossless_and_owner_unchanged(self):
        ui = Layout()
        a = self.number(ui)
        b = self.number(ui, "b")
        binding = b.binding
        style(ui, units="mm", precision=1, value_width=78)
        n = b.options["numeric"]
        self.assertEqual(n.format(155.234), "155.2 (mm)")
        self.assertEqual(n.parse(n.format(155.234), 155.234), 155.234)
        self.assertEqual(n.parse("150+5 (mm)", 155), 155)
        self.assertIs(b.binding, binding)
        self.assertNotIn("units", a.options["numeric"].presentation)

    def test_native_length_and_rotation_conversions_and_drag(self):
        ui = Layout()
        c = self.number(ui, unit="LENGTH")
        c.options["numeric"].context.scene.unit_settings.scale_length = 0.01
        style(ui, units="mm", precision=1)
        n = c.options["numeric"]
        self.assertEqual(n.format(2), "20.0 (mm)")
        self.assertEqual(n.parse("25 (mm)", 0), 2.5)
        self.assertEqual(n.display_scale(n.snapshot()), 10)
        r = self.number(ui, "r", unit="ROTATION")
        style(ui, units="deg", precision=1)
        self.assertAlmostEqual(r.options["numeric"].parse("180", 0), 3.141592653589793)

    def test_compound_preflight_is_atomic(self):
        ui = Layout()
        row = ui.row()
        a = self.number(row, "a")
        b = self.number(row, "b", unit="AREA")
        original = tuple(ui.group.children)
        with self.assertRaises(ValueError):
            style(ui, units="mm", padding=4)
        self.assertEqual(tuple(ui.group.children), original)
        self.assertNotIn("_inline_style", a.options)
        self.assertNotIn("_inline_style", b.options)

    def test_padding_margin_gap_and_hidden_hit_targets(self):
        ui = Layout()
        style(ui, scope="group", gap=9, padding=(1, 2, 3, 4))
        a = ui.label(text="a")
        style(ui, padding=(2, 3, 4, 5), margin=1)
        hidden = ui.label(text="hidden")
        style(ui, display="none")
        b = ui.label(text="b")
        ui.canvas.arrange(300)
        self.assertEqual(a.rect[:2], (18, 12))
        self.assertEqual(b.rect[1], a.rect[1] + a.rect[3] + 5 + 9)
        self.assertEqual(hidden.rect, (0, 0, 0, 0))
        self.assertNotIn(hidden, list(ui.canvas.visible_controls((0, 0, 300, 1000))))
        self.assertIs(ui.canvas.hit(a.rect[0] + 1, a.rect[1] + 1, (0, 0, 300, 1000)), a)

    def test_group_defaults_future_children_and_motion_parent_disable(self):
        ui = Layout()
        style(ui, scope="group", color="#123456", motion={"strength": 0.2})
        c = ui.label(text="a")
        style(ui, motion={"enabled": False})
        self.assertEqual(
            c.options["_inline_style"]["color"], (18 / 255, 52 / 255, 86 / 255, 1)
        )
        self.assertFalse(c.motion.settings.enabled)
        self.assertEqual(c.motion.settings.strength, 0.2)
        ui.canvas.animation.enabled = False
        d = ui.label(text="b")
        self.assertEqual(d.motion.settings.strength, 0.2)
        style(ui, motion={"enabled": True})
        self.assertEqual(d.motion.strength, 0)

    def test_wrap_constraints_and_template(self):
        ui = Layout()
        StyleSheet(geometry_variants={"dense": {"gap": 2}}).apply(ui.canvas)
        style(ui, scope="group", template="dense")
        self.assertEqual(ui.canvas.theme.gap, 2)
        c = ui.label(text="A long description to wrap into multiple lines")
        style(ui, width=100, padding=4, wrap=True)
        ui.canvas.arrange(300)
        self.assertLessEqual(c.rect[2], 92)
        self.assertGreater(len(c.options["_wrapped_lines"]), 1)

    def test_all_basic_control_kinds_keep_same_binding_and_controls(self):
        ui = Layout()
        for kind in (
            "toggle",
            "number",
            "text",
            "enum",
            "pointer",
            "search",
            "color",
            "event",
            "button",
            "label",
        ):
            b = Binding(lambda: 0, lambda v: None)
            c = ui.group.add(kind, kind, kind, binding=b, numeric=codec())
            style(ui, padding=3, margin=2, color="#FFFFFF", motion={"strength": 0.5})
            self.assertIs(c.binding, b)
        self.assertEqual(len(ui.canvas.controls), 10)
        ui.canvas.arrange(400)
        count = ui.canvas.layout_count
        ui.canvas.arrange(400)
        self.assertEqual(ui.canvas.layout_count, count)

    def test_max_height_clamps_without_expanding_short_content(self):
        ui = Layout()
        c = ui.label(text="Short")
        style(ui, max_height=100)
        ui.canvas.arrange(300)
        self.assertEqual(c.rect[3], 32)
        style(ui, max_height=20)
        ui.canvas.arrange(300)
        self.assertEqual(c.rect[3], 20)

    def test_hiding_active_edit_cancels_and_nested_palette_roles_merge(self):
        ui = Layout()
        style(ui, scope="group", colors={"text": "#FFFFFF"})
        col = ui.column()
        style(col, scope="group", colors={"accent": "#FF0000"})
        c = self.number(col)
        self.assertEqual(set(c.options["_inline_style"]["colors"]), {"text", "accent"})
        ui.canvas.active = c
        style(col, display="none")
        self.assertIsNone(ui.canvas.active)
        style(col, display="flex")
        ui.canvas.arrange(300)
        from beyond_ui import MenuEntry

        ui.canvas.context_provider = lambda target, context: (MenuEntry("copy", "Copy"),)
        self.assertTrue(ui.canvas.open_context(c, 20, 20, (0, 0, 300, 500)))
        style(col, display="none")
        self.assertIsNone(ui.canvas.context_menu)
        self.assertIsNone(ui.canvas.context_focus)
