from types import SimpleNamespace
import unittest
from beyond_ui.bindings import Binding
from beyond_ui.widgets import ColorPicker, ColorRamp, CurveMapping, DataPicker
from beyond_ui import Layout, UnsupportedControl


def event(kind, value="PRESS", **kw):
    return SimpleNamespace(type=kind, value=value, unicode=kw.pop("unicode", ""), **kw)


class Widgets(unittest.TestCase):
    def binding(self, value):
        state = [value]
        commits = []
        return (
            state,
            commits,
            Binding(
                lambda: state[0],
                lambda v: state.__setitem__(0, v),
                commit=lambda a, b: commits.append((a, b)),
            ),
        )

    def test_color_hue_sv_cancel_and_single_commit(self):
        state, commits, binding = self.binding((0.1, 0.2, 0.3, 0.4))
        widget = ColorPicker(binding, linear=False)
        widget.event(event("LEFTMOUSE"), 180, 220)
        widget.event(event("MOUSEMOVE"), 240, 180)
        self.assertNotEqual(state[0], (0.1, 0.2, 0.3, 0.4))
        widget.event(event("ESC"), 240, 180)
        self.assertEqual(state[0], (0.1, 0.2, 0.3, 0.4))
        self.assertFalse(commits)
        widget.event(event("LEFTMOUSE"), 180, 220)
        widget.event(event("LEFTMOUSE", "RELEASE"), 180, 220)
        self.assertEqual(len(commits), 1)
        self.assertEqual(state[0][3], 0.4)

    def test_color_hex_preserves_alpha(self):
        state, commits, binding = self.binding((0.1, 0.2, 0.3, 0.4))
        widget = ColorPicker(binding, linear=False)
        widget.event(event("LEFTMOUSE"), 420, 420)
        widget.text_edit.insert("#ffffff")
        widget.event(event("RET"), 420, 420)
        self.assertEqual(state[0], (1.0, 1.0, 1.0, 0.4))
        self.assertEqual(len(commits), 1)

    def test_curve_cancel_and_point_add_remove(self):
        state, commits, binding = self.binding(((0.0, 0.0), (1.0, 1.0)))
        widget = CurveMapping(binding)
        widget.event(event("LEFTMOUSE"), 141, 395)
        widget.event(event("MOUSEMOVE"), 300, 250)
        widget.event(event("ESC"), 300, 250)
        self.assertEqual(state[0], ((0.0, 0.0), (1.0, 1.0)))
        widget.event(event("LEFTMOUSE", "DOUBLE_CLICK"), 300, 250)
        self.assertEqual(len(state[0]), 3)
        widget.event(event("DEL"), 300, 250)
        self.assertEqual(len(state[0]), 2)

    def test_ramp_interpolation_and_drag_cancel(self):
        points = ((0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (1.0, 1.0, 1.0, 1.0)))
        state, commits, binding = self.binding(points)
        widget = ColorRamp(binding)
        self.assertEqual(widget.sample(0.5, points), (0.5, 0.5, 0.5, 1.0))
        widget.event(event("LEFTMOUSE"), 30, 310)
        widget.event(event("MOUSEMOVE"), 120, 310)
        widget.event(event("ESC"), 120, 310)
        self.assertEqual(state[0], points)

    def test_picker_search_identity_and_scroll(self):
        selected = []
        valid = {1, 2}
        widget = DataPicker(
            ((1, "Camera", "camera"), (2, "Cube", "object")),
            selected.append,
            valid=lambda k: k in valid,
        )
        widget.event(event("LEFTMOUSE"), 50, 100)
        widget.text_edit.insert("cube")
        widget.event(event("RET"), 50, 100)
        self.assertEqual(len(widget.filtered), 1)
        self.assertEqual(selected, [2])
        selected.clear()
        valid.remove(2)
        widget.event(event("LEFTMOUSE"), 100, 175)
        self.assertEqual(selected, [])
        widget.query = ""
        widget._filter()
        widget.event(event("LEFTMOUSE"), 100, 175)
        self.assertEqual(selected, [1])

    def test_reference_hit_regions_and_title_roles(self):
        from beyond_ui import Canvas
        from beyond_ui.widgets.metrics import CURVE, PICKER

        state, commits, binding = self.binding(((0.1, 0.2), (0.5, 0.5), (0.9, 0.8)))
        curve = CurveMapping(binding)
        curve.selected = 1
        x, y, w, h = CURVE["fields"][0]
        curve.event(event("LEFTMOUSE"), x + w / 2, y + h / 2)
        curve.text_edit.insert("0.75")
        curve.event(event("RET"), 0, 0)
        self.assertEqual(state[0][1], (0.75, 0.5))
        self.assertEqual(len(commits), 1)
        actions = []
        picker = DataPicker(
            (),
            lambda key: None,
            create=lambda: actions.append("create"),
            duplicate=lambda: actions.append("duplicate"),
            unlink=lambda: actions.append("unlink"),
        )
        for x, y, w, h in PICKER["actions"]:
            picker.event(event("LEFTMOUSE"), x + w / 2, y + h / 2)
        self.assertEqual(actions, ["create", "duplicate", "unlink"])
        canvas = Canvas()
        canvas.title("title", "Title")
        canvas.widget("curve", curve)
        canvas.arrange(330)
        rect = canvas.controls["curve"].rect
        self.assertAlmostEqual(rect[2] / rect[3], 630 / 472)
        self.assertEqual(canvas.controls["title"].options["text_role"], "title")
        layout = Layout()
        header, body = layout.panel("p")
        label = header.label(text="Other panel")
        self.assertEqual(label.options["text_role"], "title")
        self.assertIsNotNone(body)

    def test_shared_skin_transparency_and_color_rounding(self):
        from beyond_ui.gpu import style, skin
        from beyond_ui.editing import color_hex

        palette = style.theme_palette(None)
        self.assertEqual(palette["selected"], skin.ROLES["selected"][0])
        self.assertLess(palette["field"][3], 1.0)
        self.assertLess(palette["card"][3], 1.0)
        self.assertEqual(color_hex((0.2, 0.7, 0.9, 1.0), False), "#33B3E6")

    def test_unknown_custom_api_fails_explicitly(self):
        layout = Layout()
        with self.assertRaises(UnsupportedControl):
            layout.template_waveform(None, "scopes")
        self.assertFalse(layout.supports("template_waveform"))
        self.assertTrue(layout.supports("template_color_picker"))


if __name__ == "__main__":
    unittest.main()
