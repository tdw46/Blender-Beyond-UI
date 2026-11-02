import unittest
from types import SimpleNamespace as NS
from beyond_ui import integrate, Layout
from beyond_ui.layout_recording import Tape
from beyond_ui.integration import _owned_classes, _native_routes


class IntegrationTests(unittest.TestCase):
    def test_install_is_explicit_idempotent_and_restores_lifecycle(self):
        calls = []
        namespace = dict(
            __name__="consumer",
            __package__="consumer",
            register=lambda: calls.append("register"),
            unregister=lambda: calls.append("unregister"),
        )
        controller = integrate(namespace)
        self.assertEqual(calls, [])
        self.assertIs(integrate(namespace), controller)
        controller.adopt = lambda: calls.append("adopt")
        namespace["register"]()
        namespace["register"]()
        namespace["unregister"]()
        namespace["unregister"]()
        self.assertEqual(calls, ["register", "adopt", "unregister"])

    def test_owner_discovery_excludes_prefix_collisions_and_unregistered(self):
        class Base:
            pass

        owned = type(
            "Owned", (Base,), {"__module__": "addon.panels", "is_registered": True}
        )
        type("Foreign", (Base,), {"__module__": "addon_other", "is_registered": True})
        type("Pending", (Base,), {"__module__": "addon", "is_registered": False})
        self.assertEqual(_owned_classes(Base, "addon"), [owned])

    def test_native_routes_are_reported_without_running_callbacks(self):
        class Operator:
            pass

        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)

        Operator.invoke = invoke
        self.assertEqual(
            _native_routes([Operator]),
            [
                {
                    "class": "Operator",
                    "callback": "invoke",
                    "routes": ["invoke_props_dialog"],
                }
            ],
        )

    def test_reload_and_bad_options_rejected(self):
        ns = dict(__name__="consumer", register=lambda: None, unregister=lambda: None)
        with self.assertRaises(TypeError):
            integrate(ns, unknown=True)
        controller = integrate(ns)
        controller.adopt = lambda: None
        ns["register"]()
        ns["register"] = lambda: None
        with self.assertRaises(RuntimeError):
            integrate(ns)
        controller.unregister_wrapper()
        self.assertIsNot(integrate(ns), controller)

    def test_failed_adoption_unwinds_consumer(self):
        calls = []
        ns = dict(
            __name__="consumer",
            register=lambda: calls.append("register"),
            unregister=lambda: calls.append("unregister"),
        )
        controller = integrate(ns)

        def fail():
            raise RuntimeError("fixture")

        controller.adopt = fail
        with self.assertRaises(RuntimeError):
            ns["register"]()
        self.assertEqual(calls, ["register", "unregister"])
        self.assertFalse(controller.running)

    def test_tape_replay_and_structural_changes(self):
        def draw(opened):
            tape = Tape()
            row = tape.root.row(align=True)
            row.enabled = False
            row.label(text="Stable")
            if opened:
                tape.root.label(text="Conditional")
            return tape

        a, b = draw(False), draw(False)
        self.assertEqual(a.signature, b.signature)
        self.assertNotEqual(a.signature, draw(True).signature)
        layout = Layout()
        a.play(layout)
        self.assertEqual(len(layout.canvas.controls), 1)
        self.assertFalse(next(iter(layout.canvas.controls.values())).enabled)

    def test_panel_state_records_expansion_without_draw_mutation(self):
        state = {"options": False}
        tape = Tape(state)
        header, body = tape.root.panel("options")
        header.label(text="Options")
        self.assertIsNone(body)
        layout = Layout(state=state)
        tape.play(layout)
        self.assertEqual(state, {"options": False})

    def test_popup_confirm_preserves_operator_properties_and_cancel_only(self):
        for keyword in (False, True):
            tape = Tape()
            confirm = tape.root.template_popup_confirm
            props = confirm(operator="test.apply") if keyword else confirm("test.apply")
            props.tag = 3
            self.assertIsNone(confirm("", cancel_text="Cancel"))
            received = []

            def replay(operator, **kwargs):
                result = NS() if operator else None
                received.append((operator, kwargs, result))
                return result

            tape.play(NS(template_popup_confirm=replay))
            self.assertEqual(received[0][2].tag, 3)
            self.assertEqual(received[1], ("", {"cancel_text": "Cancel"}, None))

    def test_native_popup_fallback_rejects_headless_or_missing_window(self):
        from unittest.mock import patch, Mock
        from beyond_ui.registered_menu import RegisteredMenu

        for background, window in ((True, NS()), (False, None)):
            native = Mock()
            canvas = NS()
            menu = RegisteredMenu.__new__(RegisteredMenu)
            menu.layout, menu.name = NS(canvas=canvas), "TEST_PT_popup"
            with patch.dict("sys.modules", {"bpy": NS(app=NS(background=background), ops=native)}):
                self.assertFalse(menu.native_fallback(NS(window=window), "unsupported"))
            native.assert_not_called()
            self.assertEqual(native.mock_calls, [])
            self.assertIn("interactive window", canvas.menu_error)
            self.assertFalse(canvas.popup_fallbacks[0]["custom"])
