"""Mixed-control sizing must stay consistent as the host grows or narrows."""

import unittest
from beyond_ui import Canvas, Theme
from beyond_ui.bindings import Binding
from beyond_ui.widgets import (
    ColorPicker,
    ColorRamp,
    CurveMapping,
    DataPicker,
    MatrixView,
    Palette,
    PaletteSource,
    Progress,
)
from beyond_ui.widgets.socket import Socket
from types import SimpleNamespace as NS


def fixtures():
    bind = lambda value: Binding(lambda: value, lambda v: None)
    return [
        ColorPicker(bind((0.1, 0.2, 0.3, 1))),
        ColorRamp(bind(((0, (0, 0, 0, 1)), (1, (1, 1, 1, 1))))),
        CurveMapping(bind(((0, 0), (1, 1)))),
        DataPicker([(1, "First", "object"), (2, "Second", "object")], lambda key: None),
        MatrixView(bind(((0, 0, 0), (0, 0, 0), (1, 1, 1)))),
        Palette(
            PaletteSource(lambda: 0, lambda i: (0, 0, 0, 1), lambda: 0, lambda i: None)
        ),
        Progress(0.5),
        Progress(0.5, type="RING"),
        Progress(0.5, framed=False),
        Progress(0.5, framed=False, type="RING"),
    ]


class UIScale(unittest.TestCase):
    def test_every_compound_caption_matches_parent_and_does_not_grow_with_width(self):
        for widget in fixtures():
            canvas = Canvas()
            control = canvas.widget("control", widget)
            for width in (360, 560, 960):
                canvas.arrange(width)
                w, h = control.rect[2:]
                self.assertAlmostEqual(widget.design_font_size * w / widget.width, 11)
                self.assertAlmostEqual(w / h, widget.width / widget.height)
                self.assertLessEqual(w, 320)
            count = canvas.layout_count
            canvas.arrange(960)
            self.assertEqual(canvas.layout_count, count)

    def test_popover_keeps_same_size_inside_offset_and_tall_clips(self):
        canvas = Canvas()
        owner = canvas.add("pointer", "p")
        for clip in ((0, 0, 560, 520), (100, 80, 960, 800)):
            canvas.open_widget(DataPicker([], lambda k: None), owner, clip)
            a, b, w, h = canvas.overlay["rect"]
            self.assertEqual((w, h), (315, 236))
            self.assertGreaterEqual(a, clip[0])
            self.assertGreaterEqual(b, clip[1])
            self.assertLessEqual(a + w, clip[0] + clip[2])
            self.assertLessEqual(b + h, clip[1] + clip[3])
            self.assertIs(canvas.overlay["owner"], owner)
            self.assertEqual(canvas.overlay["widget"].glass_blur, 0.7)

    def test_open_popover_reflows_before_hit_testing_after_clip_resize(self):
        canvas = Canvas()
        owner = canvas.add("pointer", "p")
        widget = DataPicker([], lambda k: None)
        canvas.open_widget(widget, owner, (0, 0, 960, 800))
        canvas.event(NS(type="MOUSEMOVE", value="NOTHING"), 0, 0, (20, 10, 320, 250))
        a, b, w, h = canvas.overlay["rect"]
        self.assertIs(canvas.overlay["widget"], widget)
        self.assertEqual((w, h), (315, 236))
        self.assertGreaterEqual(a, 20)
        self.assertGreaterEqual(b, 10)
        self.assertLessEqual(a + w, 340)
        self.assertLessEqual(b + h, 260)

    def test_constrained_and_explicit_bounds_never_distort_or_overflow(self):
        canvas = Canvas()
        control = canvas.widget(
            "w", DataPicker([], lambda k: None), width=280, height=100
        )
        canvas.arrange(560)
        self.assertEqual(control.rect[3], 100)
        self.assertAlmostEqual(control.rect[2] / control.rect[3], 630 / 472)
        self.assertEqual(canvas.height, 116)
        canvas.open_widget(control.options["widget"], control, (30, 40, 100, 80))
        a, b, w, h = canvas.overlay["rect"]
        self.assertLessEqual(a + w, 130)
        self.assertLessEqual(b + h, 120)
        self.assertAlmostEqual(w / h, 630 / 472)

    def test_socket_stays_small_and_does_not_leave_a_panel_height_gap(self):
        canvas = Canvas()
        socket = canvas.widget("socket", Socket((1, 0, 0, 1)))
        following = canvas.label("label", "Label")
        canvas.arrange(960)
        self.assertEqual(socket.rect[2:], (20, 20))
        self.assertEqual(following.rect[1], socket.rect[1] + 20 + canvas.theme.gap)

    def test_pointer_search_and_color_routes_use_same_scale_and_logical_hits(self):
        canvas = Canvas()
        selected = []
        picker = DataPicker([(1, "First", "object")], selected.append)
        pointer = canvas.add(
            "pointer", "p", pointer_field=NS(picker=lambda c, o: picker)
        )
        search = canvas.add("search", "s", search_field=NS(open=lambda: picker))
        color = canvas.color(
            "c", "Color", Binding(lambda: (0.1, 0.2, 0.3, 1), lambda v: None)
        )
        for width in (360, 560, 960):
            canvas.arrange(width)
            for control in (pointer, search, color):
                canvas.cancel()
                x, y, w, h = control.rect
                canvas.event(
                    NS(type="LEFTMOUSE", value="PRESS"),
                    x + 10,
                    y + 10,
                    (0, 0, width, 520),
                )
                self.assertEqual(canvas.overlay["rect"][2:], (315, 236))
                if control is not color:
                    a, b, w, h = canvas.overlay["rect"]
                    canvas.event(
                        NS(type="LEFTMOUSE", value="PRESS"),
                        a + 100 * w / 630,
                        b + 175 * h / 472,
                        (0, 0, width, 520),
                    )
                    self.assertEqual(selected[-1], 1)
