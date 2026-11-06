import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas, Layout
from beyond_ui.popover import PanelPopover
from beyond_ui.bindings import Binding


def event(kind, value="PRESS"):
    return NS(type=kind, value=value)


class PopoverContracts(unittest.TestCase):
    def test_custom_context_capture_is_bounded_and_excludes_ordinary_state(self):
        from beyond_ui.popover import PanelContextCapture
        owner=NS(as_pointer=lambda:123)
        class Context:
            scene=owner
            def __getattr__(self,name):
                if name=='missing':raise AttributeError(name)
                return owner
        captured=PanelContextCapture(Context())
        self.assertIs(captured.scene,owner)
        self.assertIs(captured.transition_owner,owner)
        self.assertIsNone(getattr(captured,'missing',None))
        self.assertEqual(captured.values,{'transition_owner':owner})
        for n in range(63):getattr(captured,'owner_'+str(n))
        with self.assertRaises(ValueError):getattr(captured,'overflow')

    def fixture(self, count=30):
        parent = Canvas()
        owner = parent.button("open", "Open", lambda: None)
        parent.arrange(560)
        child = Canvas(parent.theme)
        state = [False]
        for i in range(count):
            child.toggle(
                str(i),
                "Toggle",
                Binding(lambda: state[0], lambda v: state.__setitem__(0, v)),
            )
        model = NS(
            cls=NS(bl_ui_units_x=16),
            direction="VERTICAL",
            context=None,
            available=lambda *a, **k: True,
        )
        widget = PanelPopover(model, parent, owner, child, None)
        parent.open_widget(widget, owner, (0, 0, 320, 150))
        return parent, widget, state

    def test_trackpad_scroll_follows_native_popup_without_relayout(self):
        parent, widget, state = self.fixture()
        count = widget.canvas.layout_count
        for inverted in (False, True):
            for delta, expected in ((17, 17), (0, 17), (-17, 0)):
                gesture = NS(type="TRACKPADPAN", value="NOTHING", mouse_y=100 + delta,
                             mouse_prev_y=100, is_direction_inverted=inverted)
                self.assertTrue(widget.dispatch(gesture, 50, 50))
                self.assertEqual(widget.scroll, expected)
        self.assertEqual(widget.canvas.layout_count, count)
        self.assertEqual(state, [False])

    def test_dimensions_scroll_without_changing_font_or_rebuilding(self):
        parent, widget, state = self.fixture()
        self.assertEqual(widget.width, 320)
        self.assertEqual(widget.height, 150)
        count = widget.canvas.layout_count
        widget.dispatch(event("WHEELDOWNMOUSE"), 50, 50)
        self.assertGreater(widget.scroll, 0)
        self.assertEqual(widget.canvas.layout_count, count)
        self.assertEqual(widget.canvas.theme.font_size, parent.theme.font_size)
        self.assertEqual(state, [False])

    def test_menu_metrics_survive_resize_and_parent_theme_changes(self):
        from dataclasses import replace
        from beyond_ui.menu_metrics import Metrics

        parent, widget, _ = self.fixture(2)
        widget.model.menu_theme = Metrics.theme
        widget.dimensions(11, 224, 500)
        self.assertEqual(widget.canvas.theme.row_height, 22.5)
        self.assertEqual(widget.canvas.theme.gap, 0)
        before = widget.canvas.layout_count
        widget.dimensions(11, 224, 500)
        self.assertEqual(widget.canvas.layout_count, before)
        parent.theme = replace(
            parent.theme, padding=30, row_height=64, gap=20, palette="REFERENCE"
        )
        widget.dimensions(11, 224, 500)
        self.assertEqual(widget.canvas.theme.padding, 8)
        self.assertEqual(widget.canvas.theme.row_height, 22.5)
        self.assertEqual(widget.canvas.theme.palette, "REFERENCE")
        rows = list(widget.canvas.controls.values())
        self.assertEqual(rows[1].rect[1] - rows[0].rect[1], 22.5)

    def test_scrollbar_drag_context_and_outside_passthrough(self):
        parent, widget, state = self.fixture()
        widget.dispatch(event("LEFTMOUSE"), widget.width - 6, 60)
        self.assertTrue(widget.capturing)
        widget.dispatch(event("MOUSEMOVE", "NOTHING"), widget.width - 6, 140)
        self.assertGreater(widget.scroll, 0)
        widget.dispatch(event("LEFTMOUSE", "RELEASE"), widget.width - 6, 140)
        self.assertFalse(widget.capturing)
        widget.dispatch(event("RIGHTMOUSE"), widget.width - 6, 80)
        menu = parent.active_menu()
        self.assertIsNotNone(menu)
        menu.choose(0, None)
        self.assertEqual(widget.scroll, 0)
        widget.canvas.close_context()
        self.assertFalse(widget.dispatch(event("RIGHTMOUSE"), -1, -1))
        self.assertIsNone(parent.overlay)

    def test_invalidation_tears_down_nested_edits_and_animation(self):
        parent, widget, state = self.fixture(2)
        child = widget.canvas
        control = next(iter(child.controls.values()))
        child._bind_motion(control.motion)
        control.motion.pulse("body", 0.1)
        parent.wide_numeric_motion_scale = 0.07
        self.assertEqual(child.wide_numeric_motion_scale, 0.07)
        parent.invalidate()
        self.assertIsNone(parent.overlay)
        self.assertFalse(child._moving)
        self.assertFalse(parent.advance_animations())

    def test_preview_inherits_without_becoming_commit(self):
        preview = lambda data, prop: None
        ui = Layout(preview=preview)
        child = ui.row().column()
        self.assertIs(child.preview, preview)
        self.assertIsNot(child.commit, preview)

    def test_layout_popover_flag_is_inherited(self):
        ui = Layout()
        self.assertFalse(ui.is_popover)
        ui._is_popover = True
        self.assertTrue(ui.row().column().is_popover)


class PopoverPlacementAndBindings(unittest.TestCase):
    def test_attachments_clamp_without_rescaling(self):
        from beyond_ui.popover import panel_position

        for direction in ("VERTICAL", "HORIZONTAL"):
            for owner in ((10, 10, 80, 24), (280, 170, 30, 24)):
                r = panel_position(owner, (0, 0, 320, 200), (150, 100), direction)
                self.assertGreaterEqual(r[0], 0)
                self.assertGreaterEqual(r[1], 0)
                self.assertLessEqual(r[0] + r[2], 320)
                self.assertLessEqual(r[1] + r[3], 200)
                self.assertEqual(r[2:], (150, 100))
        self.assertEqual(
            panel_position(
                (10, 10, 80, 24), (0, 0, 320, 200), (150, 100), "HORIZONTAL"
            )[0],
            94,
        )

    def test_releasing_old_shortcut_does_not_remove_new_owner(self):
        from beyond_ui.context_dispatch import ShortcutRegistry

        registry = ShortcutRegistry("popover-test")
        registry.operator_class = object()
        context = NS(window=NS(as_pointer=lambda: 1), area=NS(as_pointer=lambda: 2))
        old = registry.bind("open", context, lambda c, e: None)
        new = registry.bind("open", context, lambda c, e: None)
        registry.release(old)
        self.assertTrue(registry.available("open", context))
        registry.release(new)
        self.assertFalse(registry.commands)
