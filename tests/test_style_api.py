import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout, StyleSheet, style, prop
from beyond_ui.bindings import Binding
from beyond_ui.layout_recording import Tape
from beyond_ui.style_api import normalize
from test_numeric import codec


class InlineStyleTests(unittest.TestCase):
    def test_help_accessory_centers_on_stacked_value_instead_of_whole_field(self):
        from beyond_ui.scalar_geometry import slider_parts
        for width in (240, 320, 480):
            ui = Layout()
            ui.canvas.panel_layout = True
            row = ui.row()
            style(row, scope="group", gap=7, align_items="value")
            col = row.column()
            field = self.number(col)
            style(col, slider=True, label_position="top", font_size=11)
            accessory = row.column()
            style(accessory, scope="group", width=24)
            help_button = accessory.group.button("help", "", lambda: None, icon="QUESTION")
            style(accessory, width=24, height=24)
            ui.canvas.arrange(width)
            value = slider_parts(field.rect, True, stacked=field.options["_slider_stacked"],
                                 label_band=field.options.get("_label_band", 24))[2]
            self.assertAlmostEqual(help_button.rect[1]+help_button.rect[3]/2, value[1]+value[3]/2)
            self.assertEqual(help_button.rect[3], 24)

    def test_value_surface_excludes_caption_and_preserves_owner(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        c = self.number(ui)
        binding = c.binding
        style(ui, slider=True, label_width=120, label_position="left",
              surface="field", surface_region="value", padding=(3, 0))
        ui.canvas.arrange(360)
        rect, _ = ui.canvas._style_surfaces[0]
        self.assertGreater(rect[0], c.rect[0] + 120)
        self.assertIs(c.binding, binding)
        self.assertEqual(len(ui.canvas.controls), 1)
        ui.canvas.arrange(180)
        rect, _ = ui.canvas._style_surfaces[0]
        self.assertTrue(c.options["_slider_stacked"])
        self.assertGreater(rect[1], c.rect[1])
        style(ui, display="none")
        ui.canvas.arrange(180)
        self.assertEqual(ui.canvas._style_surfaces, [])

    def test_group_surface_does_not_restyle_children(self):
        ui = Layout()
        row = ui.row()
        style(row, scope="group", surface="card", surface_color="#12345680", padding=4)
        c = row.label(text="Child")
        ui.canvas.arrange(360)
        self.assertEqual(ui.canvas._style_surfaces[0][0], row.group.rect)
        self.assertNotIn("surface_color", c.options.get("_inline_style", {}))

    def test_text_button_padding_keeps_icon_tools_compact(self):
        from beyond_ui.flow import Plan

        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row()
        text = row.group.button("text", "ON", lambda: None)
        icon = row.group.button("icon", "", lambda: None, icon="ADD")
        ui.canvas.arrange(360)
        self.assertGreaterEqual(text.rect[3], ui.canvas.theme.font_size + 12)
        self.assertEqual(icon.rect[3], ui.canvas.theme.icon_button_size)
        plan = Plan(ui.canvas.theme, panel_layout=True)
        before = plan.natural(text)
        style(row, scope="group", button_padding=(8, 20))
        ui.canvas.arrange(360)
        self.assertGreaterEqual(text.rect[3], ui.canvas.theme.font_size + 16)
        self.assertGreater(Plan(ui.canvas.theme).natural(text), before)

    def test_visual_presets_preserve_box_padding_and_follow_theme_changes(self):
        from beyond_ui.flow import Plan

        ui = Layout()
        box = ui.box()
        child = box.label(text="Existing content")
        ui.canvas.arrange(360)
        original = child.rect
        style(box, scope="group", color="#FFFFFF")
        ui.canvas.arrange(360)
        self.assertEqual(child.rect, original)
        style(box, scope="group", margin=3)
        plan = Plan(ui.canvas.theme)
        self.assertEqual(plan.insets(box.group), (plan.box_padding + 3,) * 4)
        from dataclasses import replace

        plan.theme = replace(plan.theme, box_padding=12)
        self.assertEqual(plan.insets(box.group), (15,) * 4)
        style(box, scope="group", padding=0)
        self.assertEqual(plan.insets(box.group), (3,) * 4)

    def test_style_previous_compound_targets_its_spacing_and_future_children(self):
        ui = Layout()
        row = ui.row()
        a = row.label(text="One")
        b = row.label(text="Two")
        style(ui, gap=13, padding=4, color="#FFFFFF")
        self.assertIs(ui.group.children[-1], row.group)
        c = row.label(text="Three")
        self.assertIn("color", c.options["_inline_style"])
        ui.canvas.arrange(360)
        self.assertAlmostEqual(b.rect[0] - a.rect[0] - a.rect[2], 13)
        self.assertAlmostEqual(c.rect[0] - b.rect[0] - b.rect[2], 13)

    def test_repeated_constraint_updates_fail_atomically(self):
        ui = Layout()
        c = ui.label(text="Stable")
        style(ui, min_width=100, color="#FFFFFF")
        group = ui.group.children[-1]
        before = dict(group.options)
        with self.assertRaises(ValueError):
            style(ui, max_width=80, color="#FF0000")
        self.assertEqual(group.options, before)
        self.assertEqual(c.options["_inline_style"]["color"], (1, 1, 1, 1))
        style(ui, max_width=120)
        ui.canvas.arrange(360)
        self.assertLessEqual(c.rect[2], 120)

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
            {"list_row_padding": 25},
            {"list_row_align": "middle"},
        ):
            with self.assertRaises(ValueError):
                normalize(options)
        self.assertEqual(normalize(list_row_padding=(3, 8))["list_row_padding"], (3, 8, 3, 8))

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

        ui.canvas.context_provider = lambda target, context: (
            MenuEntry("copy", "Copy"),
        )
        self.assertTrue(ui.canvas.open_context(c, 20, 20, (0, 0, 300, 500)))
        style(col, display="none")
        self.assertIsNone(ui.canvas.context_menu)
        self.assertIsNone(ui.canvas.context_focus)

    def test_inline_slider_reflows_without_changing_value_hit_geometry(self):
        from beyond_ui.scalar_geometry import slider_parts

        ui = Layout()
        ui.canvas.panel_layout = True
        c = self.number(ui)
        style(ui, slider=True, label_position="left", label_width=100, value_width=42)
        ui.canvas.arrange(360)
        self.assertFalse(c.options["_slider_stacked"])
        label, track, field = slider_parts(
            c.rect,
            stacked=False,
            label_width=c.options["_slider_label_width"],
            value_width=42,
        )
        self.assertEqual(label[2], 100)
        self.assertEqual(field[2], 42)
        self.assertGreater(track[0], label[0] + label[2])
        ui.canvas.arrange(170)
        self.assertTrue(c.options["_slider_stacked"])
        self.assertGreater(c.rect[3], 24)

    def test_explicit_label_column_and_paired_field_alignment(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row()
        style(row, scope="group", label_width=60, gap=10)
        a, b = self.number(row, "a"), self.number(row, "b")
        ui.canvas.arrange(360)
        self.assertEqual(a.options["_entry_label_width"], 60)
        self.assertEqual(b.options["_entry_label_width"], 60)
        self.assertEqual(b.rect[0] - a.rect[0] - a.rect[2], 10)
        ui.canvas.arrange(180)
        self.assertTrue(a.options["_entry_stacked"])
        self.assertTrue(b.options["_entry_stacked"])

    def test_styled_list_keeps_compact_toolbar_and_intrinsic_padding(self):
        from test_collection_list import Lists

        ui = Layout()
        ui.canvas.panel_layout = True
        widget, _ = Lists().fixture(10)
        row = ui.row()
        row.group.widget("list", widget)
        style(row, margin=2)
        rail = row.column()
        tool = rail.group.button("tool", "", lambda: None, icon="ADD")
        ui.canvas.arrange(360)
        self.assertTrue(tool.options["_list_tool"])
        self.assertEqual(tool.rect[2:], (22, 22))
        ui2 = Layout()
        row2 = ui2.row()
        a = row2.label(text="One")
        style(row2, flex_grow=1)
        b = row2.label(text="Two")
        style(row2, flex_grow=2)
        ui2.canvas.arrange(360)
        self.assertAlmostEqual(b.rect[2], a.rect[2] * 2)

    def test_section_surface_includes_decorative_trailing_icon(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.box().row()
        header = row.group.add(
            "toggle",
            "section",
            "Section",
            binding=Binding(lambda: True, lambda value: None),
            bool_button=True,
            icon="TRIA_DOWN",
        )
        icon = row.label(text="", icon="INFO")
        ui.canvas.arrange(360)
        self.assertTrue(header.options["section_disclosure"])
        surface = header.options["_section_rect"]
        self.assertEqual(surface, row.group.rect)
        self.assertGreater(surface[2], header.rect[2])
        self.assertGreaterEqual(surface[0] + surface[2], icon.rect[0] + icon.rect[2])
