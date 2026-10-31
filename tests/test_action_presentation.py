import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas, Layout
from beyond_ui.popover import PanelPopover


class ActionPresentationTests(unittest.TestCase):
    def test_external_field_bounds_and_optional_label_icons(self):
        from beyond_ui.scalar_geometry import entry_parts
        from beyond_ui.layout import UnsupportedControl
        from beyond_ui.menu_metrics import Metrics

        for width in (30, 100, 320, 560):
            label, field = entry_parts((15, 20, width, 32))
            self.assertLessEqual(label[0] + label[2], field[0])
            self.assertEqual(field[0] + field[2], 15 + width)
            self.assertGreaterEqual(field[2], min(width, 40))
        row = (0, 0, 224, 22.5)
        highlight = Metrics.highlight(row)
        self.assertEqual(highlight[1] + highlight[3] / 2, row[1] + row[3] / 2)
        self.assertEqual(row, (0, 0, 224, 22.5))
        ui = Layout()
        label = ui.label(text="Output", icon="FILE_FOLDER")
        self.assertEqual(label.options["icon"], "FILE_FOLDER")
        with self.assertRaises(UnsupportedControl):
            ui.label(text="Custom", icon_value=123)
        renderer = lambda *args: True
        custom = Layout(Canvas(icon_renderer=renderer))
        self.assertEqual(
            custom.label(text="Custom", icon_value=123).options["icon_value"], 123
        )

    def test_inherited_flags_are_captured_and_invalid_emboss_rejected(self):
        ui = Layout()
        ui.alert = True
        ui.emboss = "NONE_OR_STATUS"
        child = ui.row().column()
        first = child.label(text="Warning")
        child.alert = False
        child.emboss = "NONE"
        second = child.label(text="Plain")
        self.assertTrue(first.options["alert"])
        self.assertEqual(first.options["emboss"], "NONE_OR_STATUS")
        self.assertFalse(second.options["alert"])
        self.assertEqual(second.options["emboss"], "NONE")
        self.assertEqual(ui.emboss, "NONE_OR_STATUS")
        with self.assertRaises(ValueError):
            child.emboss = "UNKNOWN"

    def test_status_preparation_culls_and_does_not_poll_on_hover_or_timer(self):
        canvas = Canvas()
        calls = []
        for i in range(30):
            canvas.label(
                str(i),
                "Status",
                status_model=NS(state=lambda i=i: calls.append(i) or "KEYED"),
            )
        canvas.arrange(400)
        calls.clear()
        clip = (0, 0, 400, 40)
        canvas.refresh_status(clip)
        self.assertEqual(calls, [0])
        calls.clear()
        for kind in ("MOUSEMOVE", "TIMER"):
            canvas.event(NS(type=kind, value="NOTHING"), 20, 20, clip)
        self.assertEqual(calls, [])
        canvas.event(NS(type="A", value="PRESS"), 20, 20, clip)
        self.assertEqual(calls, [0])

    def test_cancel_footer_keeps_host_context_and_rejects_removed_owner(self):
        from beyond_ui.context_menu import Entry

        calls = []
        ui = Layout()
        ui._is_popover = True
        ui.canvas.context_provider = lambda t, c: (
            Entry("HOST", "Host action", lambda t, c: calls.append(t.key)),
        )
        ui.template_popup_confirm("", cancel_text="Cancel")
        ui.canvas.arrange(400)
        control = next(iter(ui.canvas.controls.values()))
        clip = (0, 0, 400, 300)
        x, y, w, h = control.rect
        self.assertTrue(ui.canvas.open_context(control, x + 2, y + 2, clip))
        menu = ui.canvas.context_menu
        self.assertEqual([r.key for r in menu.page.rows], ["CANCEL_POPUP", "HOST"])
        menu.choose(1, None)
        self.assertEqual(calls, [control.key])
        ui.canvas.cancel()
        self.assertTrue(ui.canvas.open_context(control, x + 2, y + 2, clip))
        menu = ui.canvas.context_menu
        ui.canvas.controls.pop(control.key)
        menu.choose(1, None)
        self.assertEqual(calls, [control.key])

    def test_popup_close_cannot_dismiss_replacement(self):
        parent, child = Canvas(), Canvas()
        owner = parent.button("owner", "Open", lambda: None)
        parent.arrange(400)
        child.label("label", "Popup")
        model = NS(
            cls=NS(bl_ui_units_x=16),
            direction="VERTICAL",
            context=None,
            available=lambda *a, **k: True,
        )
        popup = PanelPopover(model, parent, owner, child, None)
        parent.open_widget(popup, owner, (0, 0, 400, 300))
        child._popup_close()
        self.assertIsNone(parent.overlay)
        sentinel = object()
        parent.overlay = {"widget": sentinel}
        child._popup_close()
        self.assertIs(parent.overlay["widget"], sentinel)
        parent.overlay = None


if __name__ == "__main__":
    unittest.main()
