import unittest
from types import SimpleNamespace as NS

from beyond_ui import Canvas, Layout
from beyond_ui.bindings import Binding
from beyond_ui.context_menu import Entry
from beyond_ui.popover import PanelPopover


def event(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


class PopupFocusTests(unittest.TestCase):
    def fixture(self, *, initial=True, padding=0):
        parent, child = Canvas(), Canvas()
        owner = parent.button("open", "Open", lambda: None)
        parent.arrange(560)
        values, calls = ["Before"], []
        for i in range(padding):
            child.label(str(i), "Padding")
        field = child.text(
            "text",
            "Name",
            Binding(lambda: values[0], lambda x: values.__setitem__(0, x)),
            activate_init=initial,
            context_menu=lambda target, context: (
                Entry("COPY", "Copy", lambda t, c: None),
            ),
        )
        action = child.button(
            "apply",
            "Apply",
            lambda: calls.append(values[0]) or {"FINISHED"},
            active_default=True,
            operator_button=True,
        )
        model = NS(
            cls=NS(bl_ui_units_x=16),
            direction="VERTICAL",
            context=None,
            available=lambda *a, **k: True,
        )
        popup = PanelPopover(model, parent, owner, child, None)
        parent.open_widget(popup, owner, (0, 0, 320, 160))
        popup.opened(None)
        return parent, popup, field, action, values, calls

    def test_initial_edit_is_selected_revealed_once_and_never_executes(self):
        parent, popup, field, action, values, calls = self.fixture(padding=20)
        canvas = popup.canvas
        self.assertIs(canvas.active, field)
        self.assertEqual((canvas.editor.anchor, canvas.editor.cursor), (0, 6))
        self.assertGreater(popup.scroll, 0)
        self.assertEqual(calls, [])
        canvas.editor.insert("Changed")
        popup.opened(None)
        self.assertEqual(canvas.editor.text, "Changed")
        self.assertEqual(values, ["Before"])
        popup.dispatch(event("RET"), 20, 20)
        self.assertEqual(values, ["Changed"])
        self.assertEqual(calls, [])
        popup.dispatch(event("NUMPAD_ENTER"), 20, 20)
        self.assertEqual(calls, ["Changed"])
        self.assertIsNone(parent.overlay)
        self.assertFalse(canvas.visible)
        self.assertEqual(popup.focus.defaults, ())

    def test_cancel_edit_before_context_and_popup_dismissal(self):
        parent, popup, field, action, values, calls = self.fixture()
        popup.canvas.editor.insert("Discard")
        popup.dispatch(event("RIGHTMOUSE"), 20, 20)
        self.assertIsNone(popup.canvas.edit)
        self.assertIsNotNone(parent.overlay)
        self.assertEqual(values, ["Before"])
        popup.dispatch(event("APP"), 20, 20)
        self.assertIsNotNone(popup.canvas.context_menu)
        popup.dispatch(event("ESC"), 20, 20)
        self.assertIsNone(popup.canvas.context_menu)
        popup.dispatch(event("ESC"), 20, 20)
        self.assertIsNone(parent.overlay)
        self.assertEqual(calls, [])

    def test_invalid_number_retains_edit_instead_of_running_default(self):
        parent, popup, field, action, values, calls = self.fixture()
        popup.canvas.cancel()
        n = [1.0]
        field.kind = "number"
        field.binding = Binding(lambda: n[0], lambda x: n.__setitem__(0, x))
        popup.focus.initialized = False
        popup.opened(None)
        popup.canvas.editor.insert("nope")
        popup.dispatch(event("RET"), 20, 20)
        self.assertIs(popup.canvas.active, field)
        self.assertEqual(n, [1.0])
        self.assertEqual(calls, [])

    def test_return_repetition_modifiers_disabled_and_replaced_controls(self):
        parent, popup, field, action, values, calls = self.fixture(initial=False)
        for e in (
            event("RET", is_repeat=True),
            event("RET", "RELEASE"),
            event("RET", ctrl=True),
        ):
            popup.dispatch(e, 20, 20)
        self.assertEqual(calls, [])
        action.options["enabled"] = False
        popup.dispatch(event("RET"), 20, 20)
        self.assertEqual(calls, [])
        action.options["enabled"] = True
        popup.canvas.controls.pop(action.key)
        popup.canvas.button(action.key, "Replacement", lambda: calls.append("wrong"))
        popup.dispatch(event("RET"), 20, 20)
        self.assertEqual(calls, [])

    def test_stale_active_field_cancels_without_writing(self):
        parent, popup, field, action, values, calls = self.fixture()
        popup.canvas.editor.insert("Wrong")
        field.options["enabled"] = False
        popup.dispatch(event("RET"), 20, 20)
        self.assertIsNone(popup.canvas.edit)
        self.assertEqual(values, ["Before"])
        self.assertEqual(calls, [])
        self.assertIn("no longer available", parent.menu_error)

    def test_guard_errors_and_cancelled_operator_keep_popup(self):
        parent, popup, field, action, values, calls = self.fixture(initial=False)

        def stale(ctx):
            raise ReferenceError("Owner changed")

        action.options["activation_guard"] = stale
        popup.dispatch(event("RET"), 20, 20)
        self.assertEqual(calls, [])
        self.assertEqual(parent.menu_error, "Owner changed")
        action.options.pop("activation_guard")
        action.action = lambda: {"CANCELLED"}
        popup.dispatch(event("RET"), 20, 20)
        self.assertIsNotNone(parent.overlay)

    def test_context_menu_return_never_runs_default(self):
        parent, popup, field, action, values, calls = self.fixture(initial=False)
        popup.canvas.open_context(field, 20, 20, popup.clip)
        popup.dispatch(event("RET"), 20, 20)
        self.assertEqual(calls, [])

    def test_default_cannot_close_replacement_overlay(self):
        parent, popup, field, action, values, calls = self.fixture(initial=False)
        replacement = {"widget": object()}

        def replace_overlay():
            parent.overlay = replacement
            return {"FINISHED"}

        action.action = replace_overlay
        popup.dispatch(event("RET"), 20, 20)
        self.assertIs(parent.overlay, replacement)

    def test_disabled_initial_field_does_not_start_an_edit(self):
        parent, popup, field, action, values, calls = self.fixture()
        popup.canvas.cancel()
        popup.focus.initialized = False
        field.options["enabled"] = False
        popup.opened(None)
        self.assertIsNone(popup.canvas.edit)
        self.assertEqual(values, ["Before"])
        self.assertEqual(calls, [])

    def test_flags_are_local_snapshots_and_supported(self):
        ui = Layout()
        self.assertTrue(ui.supports("activate_init"))
        self.assertTrue(ui.supports("active_default"))
        ui.activate_init = ui.active_default = True
        self.assertTrue(ui._options()["activate_init"])
        child = ui.column()
        self.assertFalse(child.activate_init)
        self.assertFalse(child.active_default)
