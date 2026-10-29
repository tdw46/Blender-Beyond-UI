import unittest
from types import SimpleNamespace
from beyond_ui.bindings import Binding
from beyond_ui.widgets import Palette, PaletteSource, MatrixView, Progress
from beyond_ui import Layout, Canvas


def event(kind, **kw):
    return SimpleNamespace(type=kind, value="PRESS", **kw)


class NextWidgets(unittest.TestCase):
    def palette(self, count=18):
        reads = []
        selected = [4]
        calls = []
        source = PaletteSource(
            lambda: count,
            lambda i: (reads.append(i) or (0.2, 0.5, 0.8, 1)),
            lambda: selected[0],
            lambda i: selected.__setitem__(0, i),
            add=lambda: calls.append("add"),
            remove=lambda: calls.append("remove"),
            edit=lambda i: calls.append(("edit", i)),
        )
        return Palette(source, linear=False), reads, selected, calls

    def test_palette_navigation_scrolling_and_actions(self):
        widget, reads, selected, calls = self.palette(10000)
        self.assertEqual(len(widget.visible()), 18)
        widget.event(event("LEFTMOUSE"), 40, 100)
        self.assertEqual(selected[0], 0)
        widget.event(event("RIGHT_ARROW"), 40, 100)
        self.assertEqual(selected[0], 1)
        widget.event(event("LEFTMOUSE", ctrl=True), 130, 100)
        self.assertEqual(calls, [("edit", 1)])
        widget.event(event("WHEELDOWNMOUSE"), 40, 100)
        self.assertEqual(list(widget.visible()), list(range(6, 24)))
        widget.event(event("LEFTMOUSE"), 40, 100)
        self.assertEqual(selected[0], 6)
        widget.event(event("LEFTMOUSE"), 60, 390)
        widget.event(event("LEFTMOUSE"), 120, 390)
        self.assertEqual(calls[-2:], ["add", "remove"])
        self.assertEqual(reads, [])  # Layout/hit testing never reads offscreen colors.

    def test_palette_revalidates_before_actions(self):
        widget, reads, selected, calls = self.palette()
        widget.source.valid = lambda: False
        self.assertFalse(widget.event(event("LEFTMOUSE"), 60, 390))
        self.assertEqual(calls, [])

    def test_palette_selection_does_not_scan_all_colors(self):
        from beyond_ui.widgets.rna import palette_source

        class Color:
            def __init__(self, key):
                self.key = key
                self.color = (0.2, 0.3, 0.4)
                self.strength = 1.0
                self.weight = 0.5

            def as_pointer(self):
                return self.key

        class Colors(list):
            forbid_scan = False

            def __iter__(self):
                if self.forbid_scan:
                    raise AssertionError("Selection scanned every palette color")
                return super().__iter__()

        colors = Colors(Color(i + 1) for i in range(10000))
        colors.active = colors[0]
        palette = SimpleNamespace(colors=colors, as_pointer=lambda: 2, is_editable=True)
        owner = SimpleNamespace(palette=palette, as_pointer=lambda: 1)
        commits = []
        source = palette_source(owner, "palette", lambda a, b: commits.append((a, b)))
        source.active()
        colors.forbid_scan = True
        source.select(9999)
        self.assertEqual(source.active(), 9999)
        self.assertEqual(len(commits), 1)
        self.assertNotIn("colors", commits[0][0])

    def test_progress_endpoints_invalid_values_and_input_passthrough(self):
        self.assertEqual(Progress(-1).value(), 0.0)
        self.assertEqual(Progress(2).value(), 1.0)
        for value in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                Progress(value)
        with self.assertRaises(ValueError):
            Progress(0.5, type="UNKNOWN")
        state = [0.25]
        p = Progress(lambda: state[0])
        self.assertEqual(p.value(), 0.25)
        state[0] = 0.75
        self.assertEqual(p.value(), 0.75)
        self.assertFalse(p.event(event("LEFTMOUSE"), 200, 150))
        canvas = Canvas()
        canvas.widget("p", p)
        canvas.arrange(630)
        self.assertFalse(canvas.event(event("LEFTMOUSE"), 100, 100, (0, 0, 630, 500)))
        self.assertIsNone(canvas.widget_capture)

    def test_matrix_view_is_read_only(self):
        writes = []
        matrix = MatrixView(
            Binding(lambda: ((0, 0, 0), (0, 0, 0), (1, 1, 1)), writes.append)
        )
        for kind in ("LEFTMOUSE", "MOUSEMOVE", "RET", "UP_ARROW"):
            self.assertFalse(matrix.event(event(kind), 60, 170))
        self.assertEqual(writes, [])

    def test_layout_progress_signature_and_compact_geometry(self):
        ui = Layout()
        control = ui.progress(
            factor=0.65, type="BAR", text="Preparing assets", translate=False
        )
        self.assertEqual(control.options["widget"].value(), 0.65)
        ui.canvas.arrange(336)
        self.assertEqual(control.rect[3], 33)


if __name__ == "__main__":
    unittest.main()
