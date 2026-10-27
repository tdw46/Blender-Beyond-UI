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
        widget.event(event("LEFTMOUSE"), 100, 100)
        widget.event(event("MOUSEMOVE"), 120, 60)
        self.assertNotEqual(state[0], (0.1, 0.2, 0.3, 0.4))
        widget.event(event("ESC"), 120, 60)
        self.assertEqual(state[0], (0.1, 0.2, 0.3, 0.4))
        self.assertFalse(commits)
        widget.event(event("LEFTMOUSE"), 100, 100)
        widget.event(event("LEFTMOUSE", "RELEASE"), 100, 100)
        self.assertEqual(len(commits), 1)
        self.assertEqual(state[0][3], 0.4)

    def test_color_hex_preserves_alpha(self):
        state, commits, binding = self.binding((0.1, 0.2, 0.3, 0.4))
        widget = ColorPicker(binding, linear=False)
        widget.event(event("LEFTMOUSE"), 220, 220)
        widget.text_edit.insert("#ffffff")
        widget.event(event("RET"), 220, 220)
        self.assertEqual(state[0], (1.0, 1.0, 1.0, 0.4))
        self.assertEqual(len(commits), 1)

    def test_curve_cancel_and_point_add_remove(self):
        state, commits, binding = self.binding(((0.0, 0.0), (1.0, 1.0)))
        widget = CurveMapping(binding)
        widget.event(event("LEFTMOUSE"), 74, 214)
        widget.event(event("MOUSEMOVE"), 150, 120)
        widget.event(event("ESC"), 150, 120)
        self.assertEqual(state[0], ((0.0, 0.0), (1.0, 1.0)))
        widget.event(event("LEFTMOUSE", "DOUBLE_CLICK"), 150, 120)
        self.assertEqual(len(state[0]), 3)
        widget.event(event("DEL"), 150, 120)
        self.assertEqual(len(state[0]), 2)

    def test_ramp_interpolation_and_drag_cancel(self):
        points = ((0.0, (0.0, 0.0, 0.0, 1.0)), (1.0, (1.0, 1.0, 1.0, 1.0)))
        state, commits, binding = self.binding(points)
        widget = ColorRamp(binding)
        self.assertEqual(widget.sample(0.5, points), (0.5, 0.5, 0.5, 1.0))
        widget.event(event("LEFTMOUSE"), 8, 110)
        widget.event(event("MOUSEMOVE"), 100, 110)
        widget.event(event("ESC"), 100, 110)
        self.assertEqual(state[0], points)

    def test_picker_search_identity_and_scroll(self):
        selected = []
        valid = {1, 2}
        widget = DataPicker(
            ((1, "Camera", "camera"), (2, "Cube", "object")),
            selected.append,
            valid=lambda k: k in valid,
        )
        widget.event(event("LEFTMOUSE"), 30, 20)
        widget.text_edit.insert("cube")
        widget.event(event("RET"), 30, 20)
        self.assertEqual(len(widget.filtered), 1)
        valid.remove(2)
        widget.event(event("LEFTMOUSE"), 60, 60)
        self.assertEqual(selected, [])
        widget.query = ""
        widget._filter()
        widget.event(event("LEFTMOUSE"), 60, 60)
        self.assertEqual(selected, [1])

    def test_unknown_custom_api_fails_explicitly(self):
        layout = Layout()
        with self.assertRaises(UnsupportedControl):
            layout.template_waveform(None, "scopes")
        self.assertFalse(layout.supports("template_waveform"))
        self.assertTrue(layout.supports("template_color_picker"))


if __name__ == "__main__":
    unittest.main()
