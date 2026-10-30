import math
import unittest
from beyond_ui import Layout
from beyond_ui.bindings import Binding
from beyond_ui.widgets.base import Widget


class Sizing(unittest.TestCase):
    def test_local_zero_identity_and_nested_scale_once(self):
        ui = Layout()
        ui.scale_y = 2
        col = ui.column()
        self.assertEqual(col.scale_y, 0)
        control = col.label(text="Body")
        ui.canvas.arrange(560)
        self.assertEqual(control.rect[3], 64)
        col.scale_y = 1.5
        ui.canvas.arrange(560)
        self.assertEqual(control.rect[3], 96)
        col.scale_y = 0
        ui.scale_y = 0
        ui.canvas.arrange(560)
        self.assertEqual(control.rect[3], 32)
        self.assertEqual(ui.canvas.theme.font_size, 11)

    def test_relative_width_and_fixed_width_survive_narrow_rows(self):
        ui = Layout()
        row = ui.row(align=True)
        left, right = row.column(), row.column()
        left.scale_x = 2
        a, b = left.label(text="A"), right.label(text="B")
        ui.canvas.arrange(316)
        self.assertEqual((a.rect[2], b.rect[2]), (200, 100))
        left.ui_units_x = 3
        ui.canvas.arrange(316)
        self.assertEqual((a.rect[2], b.rect[2]), (96, 204))
        right.ui_units_x = 3
        ui.canvas.arrange(116)
        self.assertEqual((a.rect[2], b.rect[2]), (50, 50))
        self.assertEqual(a.rect[0] + a.rect[2], b.rect[0])

    def test_intrinsic_width_and_fixed_slot_not_copied_to_children(self):
        ui = Layout()
        row = ui.row()
        row.alignment = "LEFT"
        row.scale_x = 2
        col = row.column()
        self.assertEqual(col.scale_x, 0)
        self.assertEqual(col.ui_units_x, 0)
        a = col.label(text="A")
        ui.canvas.set_text_measure(lambda text, role: 40, "font")
        ui.canvas.arrange(560)
        self.assertEqual(a.rect[2], 128)
        col.ui_units_x = 2
        col.scale_x = 3
        ui.canvas.arrange(560)
        self.assertEqual(
            a.rect[2], 128
        )  # Forced units override local, not ancestor scale.

    def test_fixed_height_fits_children_and_hit_geometry(self):
        ui = Layout()
        col = ui.column()
        col.ui_units_y = 3
        a, b = col.label(text="A"), col.label(text="B")
        after = ui.label(text="After")
        ui.canvas.arrange(320)
        self.assertEqual(col.group.rect[3], 96)
        self.assertAlmostEqual(b.rect[1] + b.rect[3], 104)
        self.assertEqual(after.rect[1], 108)
        x, y, w, h = b.rect
        self.assertIs(ui.canvas.hit(x + w / 2, y + h / 2, (0, 0, 320, 240)), b)
        col.ui_units_y = 0.5
        ui.canvas.arrange(320)
        self.assertAlmostEqual(b.rect[1] + b.rect[3], 24)
        self.assertEqual(after.rect[1], 28)

    def test_resize_cancels_edit_and_cached_arrange_reads_nothing(self):
        ui = Layout()
        values, reads = [1], []
        c = ui.canvas.number(
            "number",
            "Amount",
            Binding(
                lambda: reads.append(1) or values[0], lambda x: values.__setitem__(0, x)
            ),
        )
        ui.canvas.arrange(320)
        ui.canvas._begin(c)
        ui.canvas.edit.update(4)
        ui.scale_y = 1.5
        self.assertEqual(values[0], 1)
        self.assertIsNone(ui.canvas.active)
        ui.canvas.arrange(320)
        before = ui.canvas.layout_count, len(reads)
        for _ in range(100):
            ui.canvas.arrange(320)
        self.assertEqual(before, (ui.canvas.layout_count, len(reads)))

    def test_compound_control_keeps_aspect_and_does_not_enlarge_fonts(self):
        ui = Layout()
        col = ui.column()
        col.ui_units_y = 2
        widget = Widget()
        widget.width, widget.height = 220, 110
        control = col.group.widget("compound", widget)
        ui.canvas.arrange(320)
        self.assertEqual(control.rect[2:4], (128, 64))
        col.ui_units_y = 12
        col.scale_x = col.scale_y = 2
        ui.canvas.arrange(600)
        self.assertEqual(control.rect[2:4], (220, 110))

    def test_reset_reenters_plain_path_and_registry_does_not_own_removed_groups(self):
        import gc
        import weakref

        ui = Layout()
        child = ui.column()
        child.scale_x = 2
        self.assertEqual(len(ui.canvas._sized_groups), 1)
        child.scale_x = 0
        self.assertFalse(ui.canvas._sized_groups)
        child.ui_units_y = 2
        reference = weakref.ref(child.group)
        ui.canvas.children.clear()
        del child
        gc.collect()
        self.assertIsNone(reference())
        self.assertFalse(ui.canvas._sized_groups)

    def test_validation_capabilities_and_empty_groups(self):
        ui = Layout()
        for name in ("scale_x", "scale_y", "ui_units_x", "ui_units_y"):
            self.assertTrue(ui.supports(name))
            for value in (-1, math.inf, math.nan, 4097):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(ValueError),
                ):
                    setattr(ui, name, value)
        ui.scale_x = 4096
        child = ui.column()
        child.scale_x = 2
        child.label(text="Too large")
        with self.assertRaises(ValueError):
            ui.canvas.arrange(320)
        ui = Layout()
        empty = ui.column()
        empty.ui_units_x = empty.ui_units_y = 5
        ui.canvas.arrange(320)
        self.assertEqual(ui.canvas.height, 16)


if __name__ == "__main__":
    unittest.main()
