import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout
from beyond_ui.bindings import Binding
from beyond_ui.scalar_geometry import entry_parts


class PanelMetrics(unittest.TestCase):
    def test_automatic_slider_is_metadata_based_and_author_can_override(self):
        from beyond_ui.scalar_geometry import slider_parts

        ui = Layout()
        ui.canvas.panel_layout = True

        def number(
            key, low=1, high=250, auto=True, slider=False, unit="NONE", integer=False
        ):
            return ui.group.number(
                key,
                "Arbitrary magnitude",
                Binding(lambda: 125, lambda v: None),
                slider_auto=auto,
                slider=slider,
                hard_min=low,
                hard_max=high,
                numeric=NS(unit=unit, integer=integer, subtype="NONE"),
            )

        automatic = number("automatic")
        entry = number("entry", auto=False)
        explicit = number("explicit", auto=False, slider=True)
        excluded = [
            number("unbounded", high=float("inf")),
            number("signed", low=-10),
            number("unit", unit="LENGTH"),
            number("integer", integer=True),
            number("factor", low=0, high=1),
        ]
        ui.canvas.arrange(300)
        self.assertTrue(automatic.options["slider"])
        self.assertTrue(explicit.options["slider"])
        self.assertFalse(entry.options["slider"])
        self.assertTrue(all(not c.options["slider"] for c in excluded))
        label, track, field = slider_parts(automatic.rect, stacked=True, label_band=26)
        self.assertEqual(label[0], automatic.rect[0])
        self.assertEqual(field[1], automatic.rect[1] + 26)
        self.assertGreater(track[2], 100)
        self.assertGreaterEqual(field[2], 48)
        ui.canvas.automatic_sliders = False
        ui.canvas.invalidate()
        ui.canvas.arrange(300)
        self.assertFalse(automatic.options["slider"])
        self.assertNotIn("_slider_stacked", automatic.options)
        self.assertTrue(explicit.options["slider"])

    def test_list_rail_uses_compact_separated_top_aligned_tools(self):
        from beyond_ui.widgets.collection_list import CollectionList

        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row()
        source = NS(items=(), active=Binding(lambda: 0, lambda v: None))
        listing = row.group.widget("list", CollectionList(source, {}, rows=4))
        rail = row.column(align=True)
        buttons = [
            rail.group.button(str(i), "", lambda: None, icon="ADD") for i in range(3)
        ]
        ui.canvas.arrange(280)
        self.assertEqual(buttons[0].rect[1], listing.rect[1])
        for b in buttons:
            self.assertEqual(b.rect[2:], (22, 22))
        self.assertEqual(buttons[1].rect[1] - buttons[0].rect[1], 26)
        self.assertGreater(listing.rect[2], 200)

    def test_slider_caption_spans_utilities_without_changing_owner(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        split = ui.split(factor=0.8, align=True)
        left, right = split.row(align=True), split.row(align=True)
        field = left.group.number(
            "magnitude",
            "Long descriptive magnitude",
            Binding(lambda: 250, lambda v: None),
            slider=True,
        )
        reset = left.group.button("reset", "", lambda: None, icon="LOOP_BACK")
        switch = right.group.toggle(
            "switch", "", Binding(lambda: False, lambda v: None)
        )
        right.label(text="mm")
        right.group.button("curve", "", lambda: None, icon="NOCURVE")
        ui.canvas.arrange(260)
        self.assertGreater(field.options["_label_span"], field.rect[2] + reset.rect[2])
        self.assertLessEqual(abs(switch.rect[1] - (field.rect[1] + 26)), 2)
        self.assertIs(
            ui.canvas.hit(switch.rect[0], field.rect[1] + 10, (0, 0, 260, 100)), field
        )

    def test_stacked_slider_track_cancel_and_numeric_entry_share_geometry(self):
        from beyond_ui.scalar_geometry import slider_parts

        value = [250.0]
        ui = Layout()
        ui.canvas.panel_layout = True
        c = ui.group.number(
            "magnitude",
            "Magnitude",
            Binding(lambda: value[0], lambda v: value.__setitem__(0, v)),
            slider=True,
            min=1,
            max=250,
            hard_min=1,
            hard_max=250,
        )
        ui.canvas.arrange(240)
        clip = (0, 0, 240, ui.canvas.height)
        label, (tx, ty, tw), field = slider_parts(c.rect, stacked=True, label_band=26)
        event = lambda kind, val="PRESS": NS(
            type=kind, value=val, shift=False, ctrl=False, alt=False, oskey=False
        )
        ui.canvas.event(event("LEFTMOUSE"), tx + tw / 2, ty, clip)
        self.assertAlmostEqual(value[0], 125.5)
        ui.canvas.event(event("RIGHTMOUSE"), tx + tw / 2, ty, clip)
        self.assertEqual(value[0], 250)
        ui.canvas.event(
            event("LEFTMOUSE", "DOUBLE_CLICK"), field[0] + 10, field[1] + 10, clip
        )
        self.assertIs(ui.canvas.active, c)
        self.assertEqual(float(ui.canvas.editor.text), 250)
        ui.canvas.event(event("ESC"), 0, 0, clip)
        self.assertEqual(value[0], 250)

    def test_split_preserves_switch_unit_and_actions(self):
        for width in (220, 260, 360, 480):
            ui = Layout()
            ui.canvas.panel_layout = True
            split = ui.split(factor=0.8, align=True)
            left = split.row(align=True)
            field = left.group.number(
                "value",
                "Apparent Focal Length",
                Binding(lambda: 250, lambda v: None),
                slider=False,
            )
            reset = left.group.button("reset", "", lambda: None, icon="LOOP_BACK")
            right = split.row(align=True)
            switch = right.group.toggle(
                "enabled", "", Binding(lambda: True, lambda v: None)
            )
            unit = right.label(text="mm")
            action = right.group.button("curve", "", lambda: None, icon="NOCURVE")
            ui.canvas.arrange(width)
            self.assertGreaterEqual(switch.rect[2], 46)
            self.assertGreaterEqual(unit.rect[2], 24)
            self.assertGreaterEqual(reset.rect[2], 24)
            self.assertGreaterEqual(action.rect[2], 24)
            self.assertGreaterEqual(field.rect[2], 64)
            for c in (field, reset, switch, unit, action):
                self.assertLessEqual(c.rect[0] + c.rect[2], width - 8 + 0.01)
            label, value = entry_parts(
                field.rect,
                label_width=field.options.get("_entry_label_width"),
                stacked=field.options.get("_entry_stacked"),
                label_band=field.options.get("_label_band", 20),
            )
            self.assertGreaterEqual(value[2], 48)
            self.assertGreaterEqual(value[3], 26)

    def test_headings_are_structural_and_exclude_inline_units(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        box = ui.box()
        heading = box.label(text="Section")
        box.group.button("b", "Action", lambda: None)
        row = box.row()
        unit = row.label(text="mm")
        row.group.button("b2", "More", lambda: None)
        ui.canvas.arrange(300)
        self.assertEqual(heading.options.get("text_role"), "title")
        self.assertNotEqual(unit.options.get("text_role"), "title")
        self.assertNotEqual(row.group.children[1].options.get("text_role"), "title")

    def test_large_integral_display_is_readable(self):
        from beyond_ui.editing import display_number

        self.assertEqual(display_number(250.0), "250")
        self.assertEqual(display_number(0.5), "0.50")

    def test_heading_wraps_and_list_tools_stay_top_aligned(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        heading = ui.title(text="Multi-Object Falloff Settings: (0=infinite)")
        row = ui.row()
        tall = row.group.label("list", "List", height=180)
        rail = row.column(align=True)
        tool = rail.group.button("add", "", lambda: None, icon="ADD")
        ui.canvas.arrange(230)
        self.assertGreater(len(heading.options["_heading_lines"]), 1)
        self.assertEqual(tall.rect[1], tool.rect[1])
