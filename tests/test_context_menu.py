import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas, MenuEntry as Entry, MenuTarget as Target, Shortcut
from beyond_ui.context_menu import Menu
from beyond_ui.bindings import Binding
from beyond_ui.widgets import (
    ColorPicker,
    ColorRamp,
    CurveMapping,
    DataPicker,
    Palette,
    PaletteSource,
    MatrixView,
    Progress,
)
from beyond_ui.widgets.context import target


def event(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


def binding(value):
    values = [value]
    return Binding(lambda: values[0], lambda v: values.__setitem__(0, v))


class ContextMenus(unittest.TestCase):
    def test_key_capture_cancellation_conflict_and_acceptance(self):
        calls = []

        def capture(target, context, event):
            if event.type == "LEFT_SHIFT":
                return False
            if event.type == "C":
                raise ValueError("Key already used")
            calls.append(event.type)
            return True

        row = Entry("key", "Assign Shortcut", capture=capture)
        menu = Menu(Target("owner"), [row], (10, 10), (0, 0, 500, 400))
        menu.choose(0, None)
        self.assertEqual(len(menu.parents), 1)
        menu.event(event("LEFT_SHIFT"), 20, 20)
        self.assertIsNotNone(menu.capture_row)
        menu.event(event("C"), 20, 20)
        self.assertFalse(menu.closed)
        self.assertEqual(calls, [])
        self.assertIn("already used", menu.page.rows[1].label)
        menu.event(event("RIGHTMOUSE"), 20, 20)
        self.assertIsNone(menu.capture_row)
        menu.choose(0, None)
        menu.event(event("K", ctrl=True), 20, 20)
        self.assertTrue(menu.closed)
        self.assertEqual(calls, ["K"])

    def test_key_capture_rechecks_target_and_capability(self):
        allowed = [True]
        calls = []
        row = Entry(
            "key",
            "Assign",
            enabled=lambda t, c: allowed[0],
            capture=lambda t, c, e: calls.append(e.type),
        )
        menu = Menu(Target("owner"), [row], (10, 10), (0, 0, 500, 400))
        menu.choose(0, None)
        allowed[0] = False
        menu.event(event("K"), 20, 20)
        self.assertTrue(menu.closed)
        self.assertEqual(calls, [])
        self.assertIsNone(menu.capture_row)

    def test_navigation_nested_back_disabled_and_shortcut(self):
        calls = []
        rows = (
            Entry(
                "locked",
                "Locked",
                lambda t, c: calls.append("bad"),
                False,
                tip="Read only",
            ),
            Entry(
                "group",
                "More",
                children=lambda t, c: (
                    Entry(
                        "copy",
                        "Copy",
                        lambda t, c: calls.append(t.part),
                        bindings=(Shortcut("C", ctrl=True),),
                    ),
                ),
            ),
        )
        menu = Menu(Target("owner", ("field", 2)), rows, (10, 10), (0, 0, 500, 400))
        menu.event(event("RET"), 20, 20)
        self.assertEqual(calls, [])
        menu.event(event("DOWN_ARROW"), 20, 20)
        menu.event(event("RIGHT_ARROW"), 20, 20)
        self.assertEqual(len(menu.parents), 1)
        self.assertEqual(menu.page.rows[0].key, "__back__")
        menu.event(event("ESC"), 20, 20)
        self.assertEqual(len(menu.parents), 0)
        self.assertEqual(menu.page.highlight, 1)
        menu.event(event("RET"), 20, 20)
        menu.event(event("C", ctrl=True), 20, 20)
        self.assertEqual(calls, [("field", 2)])
        self.assertTrue(menu.closed)
        self.assertFalse(menu.motion.advance())

    def test_revalidation_owner_scope_capability_and_error_isolation(self):
        live = [True]
        allowed = [True]
        calls = []
        errors = []
        row = Entry(
            "action",
            "Action",
            lambda t, c: calls.append("ran"),
            lambda t, c: allowed[0],
        )
        menu = Menu(
            Target("owner", valid=lambda: live[0]),
            (row,),
            (0, 0),
            (0, 0, 400, 200),
            scope=lambda c: c,
            context=1,
        )
        allowed[0] = False
        menu.choose(0, 1)
        self.assertEqual(calls, [])
        live[0] = False
        menu.choose(0, 1)
        self.assertTrue(menu.closed)
        menu = Menu(
            Target("owner"),
            (row,),
            (0, 0),
            (0, 0, 400, 200),
            scope=lambda c: c,
            context=1,
        )
        self.assertFalse(menu.event(event("RET"), 2, 2, 2))
        self.assertTrue(menu.closed)

        def fail(t, c):
            raise RuntimeError("action failed")

        menu = Menu(
            Target("owner"),
            (Entry("fail", "Fail", fail),),
            (0, 0),
            (0, 0, 400, 200),
            on_error=errors.append,
        )
        menu.choose(0, None)
        self.assertTrue(menu.closed)
        self.assertEqual(str(errors[0]), "action failed")

    def test_bounds_scroll_limits_and_outside_passthrough(self):
        rows = (Entry(str(i), str(i), divider=i % 3 == 0) for i in range(100000))
        menu = Menu(Target("owner"), rows, (999, 999), (10, 20, 180, 90))
        self.assertEqual(len(menu.page.rows), 64)
        x, y, w, h = menu.page.rect
        self.assertTrue(x >= 10 and y >= 20 and x + w <= 190 and y + h <= 110)
        menu.event(event("END"), x + 5, y + 5)
        self.assertIn(63, [i for i, _, _ in menu.visible_rows()])
        self.assertFalse(menu.event(event("WHEELUPMOUSE"), 0, 0))
        self.assertFalse(menu.event(event("TIMER"), x + 5, y + 5))
        self.assertFalse(menu.event(event("RIGHTMOUSE"), 0, 0))
        self.assertTrue(menu.closed)

    def test_canvas_dispatch_cancel_before_menu_keyboard_and_invalidation(self):
        captured = []

        def provider(t, c):
            captured.append(t)
            return (Entry("copy", "Copy", lambda t, c: None),)

        canvas = Canvas(context_provider=provider)
        b = binding(0.5)
        c = canvas.number("n", "Number", b)
        canvas.arrange(320)
        clip = (0, 0, 320, canvas.height)
        x, y, w, h = c.rect
        self.assertFalse(
            canvas.event(event("RIGHTMOUSE"), x + 1, y + 1, (x + 10, y, w - 10, h))
        )
        self.assertTrue(canvas.event(event("RIGHTMOUSE"), x + 1, y + 1, clip))
        self.assertEqual(captured[-1].part, ("number",))
        canvas.close_context()
        canvas.event(event("LEFTMOUSE"), x + 2, y + 2, clip)
        canvas.event(event("MOUSEMOVE"), x + 30, y + 2, clip)
        canvas.event(event("RIGHTMOUSE"), x + 30, y + 2, clip)
        self.assertEqual(b.read(), 0.5)
        self.assertIsNone(canvas.context_menu)
        self.assertEqual(len(captured), 1)
        canvas.event(event("F10", shift=True), x + 3, y + 3, clip)
        self.assertIsNotNone(canvas.context_menu)
        canvas.invalidate()
        self.assertIsNone(canvas.context_menu)
        canvas.park()
        self.assertFalse(canvas.event(event("RIGHTMOUSE"), x + 2, y + 2, clip))

    def test_all_compound_subtargets_and_stale_rows(self):
        color = ColorPicker(binding((0.2, 0.7, 0.9, 1)), linear=False)
        self.assertEqual(target(color, "c", 400, 140).part, ("channel", "RGB", 0))
        curve = CurveMapping(binding(((0.1, 0.1), (0.5, 0.5), (0.9, 0.9))))
        curve.selected = 1
        hit = target(curve, "curve", 250, 430)
        self.assertEqual(hit.part, ("point_field", 0, 1, 1))
        curve.binding.write(((0.1, 0.1), (0.7, 0.6), (0.9, 0.9)))
        self.assertFalse(hit.valid())
        ramp = ColorRamp(
            binding(((0, (0, 0, 0, 1)), (0.5, (1, 0, 0, 1)), (1, (1, 1, 1, 1))))
        )
        self.assertEqual(target(ramp, "r", 316, 300).part, ("stop", 1))
        live = {1, 2}
        picker = DataPicker(
            ((1, "A", "object"), (2, "B", "object")),
            lambda k: None,
            valid=lambda k: k in live,
        )
        hit = target(picker, "picker", 130, 230)
        self.assertEqual(hit.part, ("row", 2))
        live.remove(2)
        self.assertFalse(hit.valid())
        ids = [10, 20]
        palette = Palette(
            PaletteSource(
                lambda: 2,
                lambda i: (1, 0, 0),
                lambda: 0,
                lambda i: None,
                identity=lambda i: ids[i],
            )
        )
        hit = target(palette, "p", 140, 100)
        self.assertEqual(hit.part, ("swatch", 1))
        ids.reverse()
        self.assertFalse(hit.valid())
        matrix = MatrixView(binding(((0, 1, 2), (3, 4, 5), (6, 7, 8))))
        hit = target(matrix, "matrix", 240, 260)
        self.assertEqual(hit.part, ("component", 1, 1))
        self.assertEqual(hit.value(), 4)
        for kind in ("BAR", "RING"):
            hit = target(Progress(0.65, type=kind), "progress", 200, 200)
            self.assertEqual(hit.part, ("progress", kind))
            self.assertEqual(hit.value(), 0.65)

    def test_popup_keyboard_target_and_drag_cancellation(self):
        canvas = Canvas(context_provider=lambda t, c: (Entry("copy", "Copy"),))
        b = binding((0.2, 0.7, 0.9, 1.0))
        owner = canvas.color("color", "Color", b)
        canvas.arrange(640)
        widget = ColorPicker(b, linear=False)
        popup = dict(
            owner=owner,
            widget=widget,
            rect=(0, 50, 630, 472),
            context_point=(400 / 630, 140 / 472),
        )
        canvas.overlay = popup
        self.assertTrue(
            canvas.event(event("F10", shift=True), -20, -20, (0, 0, 640, 600))
        )
        self.assertEqual(canvas.context_menu.target.part, ("channel", "RGB", 0))
        canvas.close_context()
        canvas.overlay = None
        canvas = Canvas(context_provider=lambda t, c: (Entry("copy", "Copy"),))
        c = canvas.widget("picker", widget)
        canvas.arrange(640)
        a, bx, w, h = c.rect
        clip = (0, 0, 640, 600)
        x, y = a + 100 * w / 630, bx + 150 * h / 472
        before = widget.binding.read()
        canvas.event(event("LEFTMOUSE"), x, y, clip)
        self.assertIsNotNone(canvas.widget_capture)
        canvas.event(event("MOUSEMOVE"), x + 20, y + 20, clip)
        canvas.event(event("RIGHTMOUSE"), x + 20, y + 20, clip)
        self.assertEqual(widget.binding.read(), before)
        self.assertIsNone(canvas.widget_capture)
        self.assertIsNone(canvas.context_menu)

    def test_depth_bound_and_parent_click(self):
        def rows(t, c):
            return (Entry("nested", "Nested", children=rows),)

        menu = Menu(Target("owner"), rows(None, None), (10, 10), (0, 0, 500, 600))
        for _ in range(10):
            menu.choose(len(menu.page.rows) - 1, None)
        self.assertEqual(len(menu.parents), 3)
        x, y, w, h = menu.parents[0].rect
        menu.event(event("LEFTMOUSE"), x + 1, y + 1)
        self.assertEqual(menu.parents, [])

    def test_delayed_tooltip_and_control_motion_policy(self):
        schedules = []
        menu = Menu(
            Target("x"),
            (Entry("locked", "Locked", enabled=False, tip="Read only field"),),
            (10, 10),
            (0, 0, 400, 200),
            on_tip=schedules.append,
        )
        now = [0.0]
        menu.motion.clock = lambda: now[0]
        menu.event(event("MOUSEMOVE"), 20, 20)
        self.assertEqual(schedules, [0.55])
        self.assertIsNone(menu.tooltip)
        self.assertAlmostEqual(menu.reveal_tip(None), 0.55)
        now[0] = 0.6
        self.assertIsNone(menu.reveal_tip(None))
        self.assertEqual(menu.tooltip[1], ("Read only field",))
        menu.event(event("MOUSEMOVE"), 20, 20)
        self.assertEqual(schedules, [0.55])
        menu.event(event("MOUSEMOVE"), 0, 0)
        self.assertIsNone(menu.tooltip)
        self.assertIsNone(schedules[-1])
        from beyond_ui.animation import AnimationSettings

        canvas = Canvas(context_provider=lambda t, c: (Entry("x", "Action"),))
        c = canvas.button(
            "x", "Action", lambda: None, animation=AnimationSettings(enabled=False)
        )
        canvas.arrange(300)
        canvas.open_context(c, 20, 20, (0, 0, 300, 300))
        self.assertEqual(canvas.context_menu.motion.strength, 0)
        self.assertFalse(canvas.context_menu.motion.tracks)
        canvas.close_context()

    def test_generic_readonly_copy_and_no_draw_side_effect(self):
        from beyond_ui.context_menu import default_entries

        context = NS(window_manager=NS(clipboard=""))
        b = Binding(lambda: (1, 2, 3), lambda value: self.fail("write"))
        rows = default_entries(Target("matrix", binding=b), context)
        self.assertEqual(len(rows), 1)
        rows[0].action(None, context)
        self.assertEqual(context.window_manager.clipboard, "(1, 2, 3)")


if __name__ == "__main__":
    unittest.main()
