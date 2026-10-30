import math
import unittest
from types import SimpleNamespace as NS

from beyond_ui import Canvas, Layout
from beyond_ui.bindings import Binding
from beyond_ui.flow import grid_shape


class Flow(unittest.TestCase):
    def test_split_factor_zero_auto_and_remainder(self):
        for factor, expected in (
            (0, (96, 96, 96)),
            (0.25, (72, 108, 108)),
            (1, (288, 0, 0)),
        ):
            ui = Layout()
            split = ui.split(factor=factor)
            controls = [split.column().label(text=str(i)) for i in range(3)]
            ui.canvas.arrange(312)
            self.assertEqual(tuple(round(c.rect[2], 6) for c in controls), expected)
            self.assertEqual(controls[-1].rect[0] + controls[-1].rect[2], 304)
        for bad in (-1, 1.1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                Layout().split(factor=bad)

    def test_grid_order_and_negative_multiples(self):
        for major in (True, False):
            ui = Layout()
            grid = ui.grid_flow(columns=3, row_major=major, even_columns=True)
            controls = [grid.label(text=str(i)) for i in range(6)]
            ui.canvas.arrange(324)
            self.assertEqual(controls[0].rect, (8, 8, 100, 32))
            self.assertEqual(
                controls[1].rect, (112, 8, 100, 32) if major else (8, 44, 100, 32)
            )
            self.assertEqual(ui.canvas.height, 84)
        self.assertEqual(grid_shape(10, 500, 90, -2, True), (4, 3))
        self.assertEqual(grid_shape(12, 500, 90, -2, False), (3, 4))
        self.assertEqual(grid_shape(10, 500, 90, 10**9, True), (10, 1))
        self.assertEqual(grid_shape(0, 500, 0), (0, 0))

    def test_grid_weighted_columns_and_even_rows(self):
        ui = Layout()
        grid = ui.grid_flow(columns=2, row_major=True)
        controls = [
            grid.group.label(str(i), str(i), width=w, height=h)
            for i, (w, h) in enumerate(((50, 20), (100, 30), (50, 40), (100, 20)))
        ]
        ui.canvas.arrange(170)
        self.assertEqual(controls[0].rect, (8, 8, 50, 20))
        self.assertEqual(controls[1].rect, (62, 8, 100, 30))
        self.assertEqual(controls[2].rect[1], 42)
        grid.group.options["even_rows"] = True
        ui.canvas.invalidate()
        ui.canvas.arrange(170)
        self.assertEqual(controls[2].rect[1], 52)
        self.assertEqual(ui.canvas.height, 100)

    def test_flow_balances_height_and_reflows_nested_groups(self):
        ui = Layout()
        flow = ui.column_flow(columns=2)
        a = flow.group.label("a", "Tall", height=80)
        b = flow.column().label(text="Short")
        c = flow.column().label(text="Short")
        ui.canvas.arrange(320)
        self.assertEqual(a.rect[:2], (8, 8))
        self.assertEqual(b.rect[:2], (162, 8))
        self.assertEqual(c.rect[:2], (162, 44))
        self.assertEqual(ui.canvas.height, 96)

    def test_spacer_flex_and_not_a_hit_target(self):
        ui = Layout()
        row = ui.row()
        left = row.label(text="L")
        row.separator_spacer()
        right = row.label(text="R")
        ui.canvas.arrange(400)
        self.assertEqual(left.rect[0], 8)
        self.assertEqual(right.rect[0] + right.rect[2], 392)
        self.assertEqual(len(list(ui.canvas.visible_controls((0, 0, 400, 100)))), 2)
        self.assertIsNone(ui.canvas.hit(200, 20, (0, 0, 400, 100)))
        with self.assertRaises(ValueError):
            ui.separator_spacer()

    def test_align_and_direction(self):
        ui = Layout()
        row = ui.row(align=True)
        a, b = row.label(text="A"), row.label(text="B")
        col = ui.column(align=True)
        c, d = col.label(text="C"), col.label(text="D")
        ui.canvas.arrange(316)
        self.assertEqual(a.rect[0] + a.rect[2], b.rect[0])
        self.assertEqual(c.rect[1] + c.rect[3], d.rect[1])
        self.assertEqual(row.direction, "HORIZONTAL")
        self.assertEqual(ui.split().direction, "VERTICAL")
        self.assertEqual(ui.direction, "HORIZONTAL")
        self.assertEqual(col.direction, "VERTICAL")
        self.assertTrue(ui.supports("direction"))
        with self.assertRaises(AttributeError):
            row.direction = "VERTICAL"

    def test_grid_direction_preserves_versioned_rna_convention(self):
        from unittest.mock import patch

        for version, expected in (
            ((4, 2, 0), "VERTICAL"),
            ((4, 4, 0), "VERTICAL"),
            ((4, 5, 0), "HORIZONTAL"),
            ((5, 2, 2), "HORIZONTAL"),
        ):
            with patch.dict("sys.modules", {"bpy": NS(app=NS(version=version))}):
                self.assertEqual(Layout().grid_flow().direction, expected)
        with patch.dict("sys.modules", {"bpy": None}):
            self.assertEqual(Layout().grid_flow().direction, "VERTICAL")

    def test_inert_attributes_do_not_claim_capability(self):
        ui = Layout()
        for name in (
            "activate_init",
            "active_default",
            "alert",
            "emboss",
            "scale_x",
            "scale_y",
            "ui_units_x",
            "ui_units_y",
        ):
            self.assertFalse(ui.supports(name), name)
        for name in (
            "enabled",
            "active",
            "alignment",
            "direction",
            "split",
            "grid_flow",
            "column_flow",
        ):
            self.assertTrue(ui.supports(name), name)

    def test_disabled_ancestor_reenable_and_edit_cancellation(self):
        ui = Layout()
        row = ui.row()
        state = [1.0]
        commits = []
        binding = Binding(
            lambda: state[0],
            lambda v: state.__setitem__(0, v),
            commit=lambda a, b: commits.append((a, b)),
        )
        control = row.group.number("n", "Value", binding)
        ui.canvas.arrange(360)
        ui.canvas._begin(control)
        ui.canvas.edit.update(2)
        ui.enabled = False
        self.assertEqual(state[0], 1)
        self.assertFalse(commits)
        self.assertIsNone(ui.canvas.active)
        row.enabled = True
        self.assertFalse(control.enabled)
        self.assertIsNone(ui.canvas.hit(20, 20, (0, 0, 360, 100)))
        ui.enabled = True
        self.assertTrue(control.enabled)
        row.active = False
        self.assertFalse(control.enabled)
        row.active = True
        self.assertTrue(control.enabled)

    def test_alignment_uses_intrinsic_width_without_font_scaling(self):
        for alignment, shift in (("LEFT", 0), ("CENTER", 0.5), ("RIGHT", 1)):
            ui = Layout()
            row = ui.row()
            row.alignment = alignment
            ui.canvas.set_text_measure(lambda text, role: 40, "font")
            a, b = row.label(text="A"), row.label(text="B")
            ui.canvas.arrange(316)
            self.assertEqual(a.rect, (8 + (300 - 132) * shift, 8, 64, 32))
            self.assertEqual(b.rect[0], a.rect[0] + 68)
            self.assertEqual(ui.canvas.theme.font_size, 11)
        with self.assertRaises(ValueError):
            ui.alignment = "JUSTIFY"

    def test_automatic_grid_reflows_without_changing_control_identity(self):
        ui = Layout()
        grid = ui.grid_flow(row_major=True, even_columns=True)
        controls = [
            grid.group.button(str(i), "Action", lambda: None, width=100)
            for i in range(8)
        ]
        ui.canvas.arrange(220)
        self.assertEqual(controls[2].rect[1], 44)
        ui.canvas.arrange(430)
        self.assertEqual(controls[2].rect[1], 8)
        self.assertEqual(controls[4].rect[1], 44)
        self.assertIs(ui.canvas.controls["2"], controls[2])

    def test_no_binding_reads_and_retained_measurements(self):
        reads, measures = [], []
        canvas = Canvas()
        ui = Layout(canvas)
        grid = ui.grid_flow(columns=0)
        for i in range(100):
            grid.group.number(
                str(i), "Opacity", Binding(lambda: reads.append(1), lambda v: None)
            )
        canvas.set_text_measure(lambda t, r: measures.append(t) or 50, "font1")
        canvas.arrange(560)
        self.assertEqual(len(measures), 100)
        self.assertFalse(reads)
        count = canvas.layout_count
        for _ in range(100):
            canvas.arrange(560)
        self.assertEqual(canvas.layout_count, count)
        self.assertEqual(len(measures), 100)
        canvas.arrange(320)
        self.assertEqual(canvas.layout_count, count + 1)
        self.assertFalse(reads)

    def test_reflow_preserves_binding_owner_and_context_target(self):
        events = []
        canvas = Canvas(context_provider=lambda t, c: events.append(t) or ())
        ui = Layout(canvas)
        grid = ui.grid_flow(columns=0, row_major=True)
        controls = [
            grid.group.button(str(i), "Action", lambda: None) for i in range(20)
        ]
        for width in (280, 560, 900):
            canvas.arrange(width)
            c = controls[7]
            x, y, w, h = c.rect
            self.assertIs(canvas.hit(x + w / 2, y + h / 2, (0, 0, width, 1000)), c)
            canvas.open_context(c, x, y, (0, 0, width, 1000), context=NS())
            self.assertEqual(events[-1].key, c.key)


if __name__ == "__main__":
    unittest.main()
