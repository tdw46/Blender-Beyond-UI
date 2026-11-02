import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from beyond_ui.invoke_routing import Router


class InvokeRouting(unittest.TestCase):
    def fixture(self):
        calls = []
        owned = type("Menu", (), {"__module__": "consumer.menus"})
        foreign = type("Menu", (), {"__module__": "foreign.menus"})
        lookup = lambda name: {"OWNED": owned, "FOREIGN": foreign}.get(name)
        context = NS(window_manager=NS())
        native = lambda *args, **kwargs: calls.append(("native", kwargs)) or {
            "FINISHED"
        }
        bpy = NS(
            context=context,
            ops=NS(wm=NS(call_menu=native, call_menu_pie=native)),
            types=NS(Menu=NS(bl_rna_get_subclass_py=lookup)),
        )
        router = Router(NS(owner="consumer", ui=NS()), ())
        router.menu = lambda ctx, evt, **kwargs: calls.append(("custom", kwargs))
        return router, bpy, context, calls

    def test_only_owned_menu_routes_change_and_aliases_restore(self):
        router, bpy, context, calls = self.fixture()
        namespace = dict(__name__="consumer", bpy=bpy, ops=bpy.ops)
        exec(
            'def run(op, context):\n    bpy.ops.wm.call_menu(name="OWNED")\n    ops.wm.call_menu_pie(name="FOREIGN")\n    return {"FINISHED"}',
            namespace,
        )
        with patch.dict(sys.modules, bpy=bpy):
            router.call(namespace["run"], None, context)
        self.assertEqual(
            calls,
            [
                ("custom", {"name": "OWNED", "pie": False}),
                ("native", {"name": "FOREIGN"}),
            ],
        )
        self.assertIs(namespace["bpy"], bpy)
        self.assertIs(namespace["ops"], bpy.ops)
        self.assertIs(bpy.context, context)

    def test_owned_call_panel_routes_custom_and_foreign_stays_native(self):
        router, bpy, context, calls = self.fixture()
        bpy.types.Panel = bpy.types.Menu
        bpy.ops.wm.call_panel = lambda *a, **kw: calls.append(("native_panel", kw)) or {"FINISHED"}
        router.panel = lambda c, e, **kw: calls.append(("custom_panel", kw))
        namespace = dict(__name__="consumer", bpy=bpy)
        exec('def run(op, context):\n    bpy.ops.wm.call_panel(name="OWNED")\n    bpy.ops.wm.call_panel(name="FOREIGN")\n    return {"FINISHED"}', namespace)
        with patch.dict(sys.modules, bpy=bpy):
            router.call(namespace["run"], None, context)
        self.assertEqual(calls, [("custom_panel", {"name":"OWNED"}), ("native_panel", {"name":"FOREIGN"})])
        self.assertIs(namespace["bpy"], bpy)

    def test_exception_restores_global_aliases(self):
        router, bpy, context, calls = self.fixture()
        namespace = dict(__name__="consumer", bpy=bpy)
        exec('def run(op, context):\n    raise ValueError("fixture")', namespace)
        with patch.dict(sys.modules, bpy=bpy), self.assertRaises(ValueError):
            router.call(namespace["run"], None, context)
        self.assertIs(namespace["bpy"], bpy)

    def test_inherited_foreign_callback_globals_are_not_rebound(self):
        router, bpy, context, calls = self.fixture()
        namespace = dict(__name__="shared_dependency", bpy=bpy)
        exec(
            'def run(op, context):\n    return bpy.ops.wm.call_menu(name="OWNED")',
            namespace,
        )
        with patch.dict(sys.modules, bpy=bpy):
            router.call(namespace["run"], None, context)
        self.assertEqual(calls[0][0], "native")
        self.assertIs(namespace["bpy"], bpy)

    def test_context_wrap_preserves_other_wm_methods(self):
        router, bpy, context, calls = self.fixture()
        context.window_manager.clipboard = "unmodified"
        router.dialog = lambda op, ctx, evt, **options: calls.append(options) or {
            "RUNNING_MODAL"
        }
        adapted = router.context(context, None)
        self.assertEqual(adapted.window_manager.clipboard, "unmodified")
        adapted.window_manager.clipboard = "copied"
        self.assertEqual(context.window_manager.clipboard, "copied")
        self.assertEqual(
            adapted.window_manager.invoke_props_dialog(
                object(), width=420, cancel_default=True
            ),
            {"RUNNING_MODAL"},
        )
        self.assertEqual(calls[0]["width"], 420)
        self.assertTrue(calls[0]["cancel_default"])

    def test_unavailable_host_uses_explicit_recorded_native_fallback(self):
        from beyond_ui.hosts.bridge import BridgeUnavailable

        router, bpy, context, calls = self.fixture()

        def unavailable(*args, **kwargs):
            raise BridgeUnavailable("Unqualified fixture host")

        router.menu = unavailable
        namespace = dict(__name__="consumer", bpy=bpy)
        exec(
            'def run(op, context):\n    return bpy.ops.wm.call_menu(name="OWNED")',
            namespace,
        )
        with patch.dict(sys.modules, bpy=bpy):
            self.assertEqual(router.call(namespace["run"], None, context), {"FINISHED"})
        self.assertEqual(calls[0][0], "native")
        self.assertFalse(router.fallbacks[0]["custom"])
        self.assertEqual(router.fallbacks[0]["route"], "call_menu")

    def test_popup_variants_preserve_arguments_and_return_contract(self):
        router, bpy, context, calls = self.fixture()
        op, event = object(), object()
        router.dialog = lambda o, c, e, **kw: calls.append((o, e, kw)) or {
            "RUNNING_MODAL"
        }
        wm = router.context(context, event).window_manager
        self.assertEqual(wm.invoke_popup(op, width=410), {"RUNNING_MODAL"})
        self.assertEqual(calls[-1], (op, event, {"mode": "PROPERTIES", "width": 410}))
        self.assertIsNone(wm.invoke_search_popup(op))
        self.assertEqual(calls[-1], (op, event, {"mode": "SEARCH"}))
        wm.invoke_confirm(op, event, message="Confirm", icon="QUESTION")
        self.assertEqual(calls[-1][2]["mode"], "CONFIRM")
        with self.assertRaises(ValueError):
            wm.invoke_confirm(op, event, icon="MESH_CUBE")
        wm.popup_menu_pie(event, str, title="Tools", icon="INFO")
        self.assertEqual(
            calls[-1],
            ("custom", {"draw": str, "title": "Tools", "icon": "INFO", "pie": True}),
        )

    def test_custom_draw_failure_falls_back_once_without_reexecuting_operator(self):
        router, bpy, context, calls = self.fixture()
        def failed(*args, **kwargs):
            raise RuntimeError("Custom layout failed")
        router.menu = failed
        namespace = dict(__name__="consumer", bpy=bpy)
        exec('def run(op, context):\n    return bpy.ops.wm.call_menu(name="OWNED")', namespace)
        with patch.dict(sys.modules, bpy=bpy):
            self.assertEqual(router.call(namespace["run"], None, context), {"FINISHED"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(router.fallbacks[0]["reason"], "Custom layout failed")

    def test_redo_popup_is_observable_native_route(self):
        router, bpy, context, calls = self.fixture()
        context.window_manager.invoke_props_popup = lambda o, e: {"RUNNING_MODAL"}
        wm = router.context(context, None).window_manager
        self.assertEqual(wm.invoke_props_popup(object(), object()), {"RUNNING_MODAL"})
        self.assertEqual(router.fallbacks[0]["route"], "invoke_props_popup")
        self.assertFalse(router.fallbacks[0]["custom"])

    def test_unqualified_flag_search_fails_before_opening_a_surface(self):
        from beyond_ui.dialog import SearchDialog
        from beyond_ui.hosts.bridge import BridgeUnavailable

        operator = NS(
            bl_property="choice",
            properties=NS(
                bl_rna=NS(properties={"choice": NS(type="ENUM", is_enum_flag=True)})
            ),
        )
        with self.assertRaisesRegex(BridgeUnavailable, "Flag-enum"):
            SearchDialog(NS(), operator, None, None)
