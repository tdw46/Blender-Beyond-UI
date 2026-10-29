"""Source slider geometry, independent number entry and switch transactions."""

import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.bindings import Binding
from beyond_ui.scalar_geometry import slider_parts, switch_rect
from beyond_ui.animation import Motion


def ev(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, unicode=kw.pop("unicode", ""), **kw)


class ScalarControls(unittest.TestCase):
    def fixture(self, width=560, integer=False):
        state = [0.25]
        commits = []
        c = Canvas()
        n = c.number(
            "opacity",
            "Opacity",
            Binding(
                lambda: state[0],
                lambda v: state.__setitem__(0, v),
                commit=lambda a, b: commits.append((a, b)),
            ),
            min=0.0,
            max=1.0,
            hard_min=-2.0,
            hard_max=2.0,
            integer=integer,
        )
        c.arrange(width)
        return c, n, state, commits, (0, 0, width, 500)

    def test_track_absolute_drag_cancel_and_single_commit(self):
        c, n, state, commits, clip = self.fixture()
        _, (x, y, w), _ = slider_parts(n.rect)
        c.event(ev("LEFTMOUSE"), x + w * 0.75, y, clip)
        self.assertAlmostEqual(state[0], 0.75)
        c.event(ev("MOUSEMOVE", "NOTHING"), x + w * 2, y, clip)
        self.assertEqual(state[0], 1)
        c.event(ev("RIGHTMOUSE"), x + w, y, clip)
        self.assertEqual(state[0], 0.25)
        self.assertEqual(commits, [])
        c.event(ev("LEFTMOUSE"), x + w * 0.5, y, clip)
        c.event(ev("LEFTMOUSE", "RELEASE"), x + w * 0.5, y, clip)
        self.assertEqual(commits, [(0.25, 0.5)])
        self.assertIsNone(c.editor)

    def test_number_entry_is_independent_and_can_exceed_soft_range(self):
        c, n, state, commits, clip = self.fixture()
        _, _, (x, y, w, h) = slider_parts(n.rect)
        c.event(ev("LEFTMOUSE"), x + w / 2, y + h / 2, clip)
        c.event(ev("LEFTMOUSE", "RELEASE"), x + w / 2, y + h / 2, clip)
        self.assertIsNotNone(c.editor)
        self.assertEqual(state[0], 0.25)
        c.event(ev("TEXTINPUT", unicode="1.5"), x, y, clip)
        c.event(ev("RET"), x, y, clip)
        self.assertEqual(state[0], 1.5)
        self.assertEqual(len(commits), 1)

    def test_narrow_rows_stack_and_share_track_hit_geometry(self):
        for width in (180, 240, 560):
            c, n, state, _, clip = self.fixture(width)
            label, (x, y, w), field = slider_parts(n.rect)
            self.assertLess(x + w, field[0])
            self.assertLessEqual(field[0] + field[2], n.rect[0] + n.rect[2])
            if width < 260:
                self.assertLessEqual(label[1] + label[3], y - 12)
            c.event(ev("LEFTMOUSE"), x + w * 0.5, y, clip)
            self.assertAlmostEqual(state[0], 0.5)
            c.cancel()

    def test_switch_retargets_without_jumping_and_stops(self):
        now = [0.0]
        m = Motion(clock=lambda: now[0])
        m.retarget("body", False, True)
        self.assertEqual(m.position("body", True), 0)
        now[0] = 0.1
        old = m.position("body", True)
        self.assertGreater(old, 0)
        self.assertLess(old, 1)
        m.retarget("body", True, False)
        self.assertAlmostEqual(m.position("body", False), old)
        shape = m.sample("body")[0]
        self.assertAlmostEqual(shape[0] * shape[1], 1)
        m.settings.enabled = False
        self.assertEqual(m.position("body", False), 0)
        self.assertFalse(m.advance())
        m.settings.enabled = True
        m.retarget("body", False, True)
        now[0] = 2
        self.assertFalse(m.advance())
        self.assertEqual(m.positions, {})

    def test_boolean_click_commits_once_and_park_clears_travel(self):
        c = Canvas()
        value = [False]
        commits = []
        n = c.toggle(
            "b",
            "Viewport",
            Binding(
                lambda: value[0],
                lambda v: value.__setitem__(0, v),
                commit=lambda a, b: commits.append((a, b)),
            ),
        )
        c.arrange(300)
        r = switch_rect(n.rect)
        c.event(ev("LEFTMOUSE"), r[0] + r[2] / 2, r[1] + r[3] / 2, (0, 0, 300, 100))
        self.assertEqual(commits, [(False, True)])
        self.assertIn("body", n.motion.positions)
        c.park()
        self.assertFalse(n.motion.positions)

    def test_alpha_track_field_and_context_share_new_geometry(self):
        from beyond_ui.widgets import ColorPicker
        from beyond_ui.widgets.metrics import COLOR
        from beyond_ui.widgets.context import target

        value = [(0.1, 0.2, 0.3, 0.4)]
        commits = []
        b = Binding(
            lambda: value[0],
            lambda v: value.__setitem__(0, v),
            commit=lambda a, b: commits.append((a, b)),
        )
        widget = ColorPicker(b, linear=False)
        x, y, w, h = COLOR["alpha_track"]
        widget.event(ev("LEFTMOUSE"), x + w * 0.75, y + h / 2)
        self.assertEqual(value[0][:3], (0.1, 0.2, 0.3))
        self.assertAlmostEqual(value[0][3], 0.75)
        widget.event(ev("RIGHTMOUSE"), x, y)
        self.assertAlmostEqual(value[0][3], 0.4)
        x, y, w, h = COLOR["alpha_field"]
        widget.event(ev("LEFTMOUSE"), x + w / 2, y + h / 2)
        widget.text_edit.insert(".6")
        widget.event(ev("RET"), x, y)
        self.assertAlmostEqual(value[0][3], 0.6)
        self.assertEqual(len(commits), 1)
        t = target(widget, "color", x + w / 2, y + h / 2)
        self.assertEqual(t.part, ("channel", "ALPHA", 3))
        self.assertAlmostEqual(t.value(), 0.6)

    def test_hue_slider_number_entry_preserves_other_channels(self):
        from beyond_ui.widgets import ColorPicker
        from beyond_ui.widgets.metrics import COLOR
        from beyond_ui.widgets.context import target
        from beyond_ui.editing import color_hsv

        value = [(0.2, 0.4, 0.6, 0.7)]
        b = Binding(lambda: value[0], lambda v: value.__setitem__(0, v))
        widget = ColorPicker(b, linear=False)
        _, sat, val = color_hsv(value[0], False)
        x, y, w, h = COLOR["hue_field"]
        widget.event(ev("LEFTMOUSE"), x + w / 2, y + h / 2)
        widget.text_edit.insert(".8")
        widget.event(ev("RET"), x, y)
        hue, s, v = color_hsv(value[0], False)
        self.assertAlmostEqual(hue, 0.8)
        self.assertAlmostEqual(s, sat)
        self.assertAlmostEqual(v, val)
        self.assertEqual(value[0][3], 0.7)
        self.assertEqual(
            target(widget, "c", x + w / 2, y + h / 2).part, ("channel", "HSV", 0)
        )
        before = value[0]
        x, y, w, h = COLOR["hue_track"]
        widget.event(ev("LEFTMOUSE"), x + w * 0.25, y + h / 2)
        widget.event(ev("RIGHTMOUSE"), x, y)
        self.assertEqual(value[0], before)
