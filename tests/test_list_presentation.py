import unittest
from beyond_ui import Canvas, Layout
from beyond_ui.bindings import Binding
from beyond_ui.registered_list import reflow_list_status


class ListPresentation(unittest.TestCase):
    def test_icon_rail_keeps_intrinsic_width(self):
        ui = Layout()
        row = ui.row()
        content = row.column().label(text="List content")
        rail = row.column(align=True)
        a = rail.group.button("add", "", lambda: None, icon="ADD")
        b = rail.group.button("remove", "", lambda: None, icon="REMOVE")
        ui.canvas.arrange(320)
        self.assertEqual(a.rect[2], 32)
        self.assertEqual(b.rect[2], 32)
        self.assertGreater(content.rect[2], 240)

    def test_narrow_status_reflow_preserves_controls(self):
        canvas = Canvas()
        row = canvas.row(align=True)
        toggle = row.toggle(
            "enabled", "", Binding(lambda: True, lambda v: None), width=38
        )
        value = row.add("pointer", "object", "")
        row.separator("gap")
        status = row.label("status", "No Armature")
        controls = dict(canvas.controls)
        reflow_list_status(canvas)
        canvas.arrange(190)
        self.assertEqual(canvas.controls, controls)
        self.assertEqual(toggle.rect[1], value.rect[1])
        self.assertGreater(status.rect[1], value.rect[1])
        self.assertGreater(value.rect[2], 120)
        self.assertEqual(status.options["text_inset"], 6)
        self.assertIs(status.parent, value.parent)
        self.assertEqual(status.rect[0], value.rect[0])
        self.assertLessEqual(value.parent.rect[3], 34)

    def test_wrapped_help_rows_use_body_line_height(self):
        ui = Layout()
        box = ui.box()
        a = box.row().label(text="First body line")
        b = box.row().label(text="Second body line")
        action = box.row().group.button("action", "Action", lambda: None)
        ui.canvas.arrange(300)
        self.assertAlmostEqual(a.rect[3], 18.15)
        self.assertAlmostEqual(b.rect[3], 18.15)
        self.assertEqual(action.rect[3], 32)
