import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from beyond_ui import Canvas, NativeLayout as Layout, Scope
from beyond_ui.bindings import Binding, Edit
from beyond_ui.virtual import VirtualList
from beyond_ui.editing import number, Text, parse_color_hex


class FakeLayout:
    bl_rna = SimpleNamespace(identifier="UILayout")

    def __init__(self):
        self.enabled = True
        self.calls = []

    def row(self, **kwargs):
        self.calls.append(kwargs)
        return FakeLayout()

    def panel(self, *args, **kwargs):
        return FakeLayout(), None

    def operator(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self


class Core(unittest.TestCase):
    def test_native_preserves_properties_arguments_and_return_identity(self):
        raw = FakeLayout()
        layout = Layout(raw)
        layout.enabled = False
        self.assertFalse(raw.enabled)
        self.assertIsInstance(layout.row(align=True), Layout)
        head, body = layout.panel("x")
        self.assertIsInstance(head, Layout)
        self.assertIsNone(body)
        # RNA operator-property objects are not layouts and must not be wrapped.
        raw.operator = lambda *a, **kw: sentinel
        sentinel = object()
        self.assertIs(layout.operator("test.run", future_keyword=True), sentinel)
        self.assertFalse(layout.supports("missing"))
        with self.assertRaises(AttributeError):
            layout.missing()

    def test_scope_continues_cleanup_after_error_and_is_idempotent(self):
        calls = []
        scope = Scope()
        scope.own(lambda: calls.append(1))

        def fail():
            raise RuntimeError("expected")

        scope.own(fail)
        scope.own(lambda: calls.append(2))
        with self.assertRaises(ExceptionGroup):
            scope.close()
        scope.close()
        self.assertEqual(calls, [2, 1])

    def test_transactions_cancel_and_commit_once(self):
        state = {"value": 1}
        commits = []
        binding = Binding(
            lambda: state["value"],
            lambda v: state.update(value=v),
            commit=lambda a, b: commits.append((a, b)),
        )
        edit = Edit(binding)
        edit.update(2)
        edit.update(3)
        edit.finish()
        edit.finish()
        self.assertEqual(commits, [(1, 3)])
        edit = Edit(binding)
        edit.update(7)
        edit.finish(cancel=True)
        self.assertEqual(state["value"], 3)
        self.assertEqual(commits, [(1, 3)])

    def test_stale_owner_cannot_receive_deferred_write(self):
        state = {"valid": True, "value": 0}
        binding = Binding(
            lambda: state["value"],
            lambda v: state.update(value=v),
            lambda: state["valid"],
        )
        edit = Edit(binding)
        state["valid"] = False
        with self.assertRaises(ReferenceError):
            edit.update(1)
        edit.finish(cancel=True)
        self.assertEqual(state["value"], 0)

    def test_native_adapter_does_not_mask_type_errors_or_attribute_errors(self):
        raw = FakeLayout()
        layout = Layout(raw)

        def error(**kwargs):
            raise TypeError("wrong argument")

        raw.row = error
        with self.assertRaisesRegex(TypeError, "wrong argument"):
            layout.row(bad=True)

    def test_virtualization_bounds_and_end(self):
        view = VirtualList([32] * 1000000)
        view.offset = 31999
        self.assertEqual(
            list(view.visible(65)),
            [(999, -31.0, 32.0), (1000, 1.0, 32.0), (1001, 33.0, 32.0)],
        )
        view.scroll(1e12, 64)
        self.assertEqual(len(list(view.visible(64))), 2)
        with self.assertRaises(ValueError):
            VirtualList([0])

    def test_retained_geometry_and_no_offscreen_reads(self):
        calls = []
        canvas = Canvas()
        for i in range(50):
            canvas.number(
                str(i), "Value", Binding(lambda: calls.append(1) or 0, lambda v: None)
            )
        canvas.arrange(300)
        canvas.arrange(300)
        self.assertEqual(canvas.layout_count, 1)
        visible = list(canvas.visible_controls((0, 0, 300, 64)))
        self.assertEqual(len(visible), 2)
        self.assertEqual(calls, [])
        canvas.park()
        self.assertEqual(list(canvas.visible_controls((0, 0, 300, 9999))), [])

    def test_editing_rejects_code_nonfinite_and_preserves_alpha(self):
        for text in ('__import__("os")', "1e10000", "2**100", "1/0"):
            with self.assertRaises(ValueError):
                number(text)
        self.assertEqual(number("(2+3)*4"), 20)
        self.assertEqual(
            parse_color_hex("#fff", (0, 0, 0, 0.25)), (1.0, 1.0, 1.0, 0.25)
        )
        edit = Text("old")
        edit.insert("new")
        self.assertEqual(edit.text, "new")

    def test_custom_input_undo_cancel_and_clip(self):
        value = [0.5]
        commits = []
        canvas = Canvas()
        canvas.number(
            "x",
            "Value",
            Binding(
                lambda: value[0],
                lambda v: value.__setitem__(0, v),
                commit=lambda a, b: commits.append((a, b)),
            ),
        )
        canvas.arrange(300)
        clip = (0, 0, 300, 100)

        def event(kind, value="PRESS", **kw):
            return SimpleNamespace(type=kind, value=value, unicode="", **kw)

        self.assertFalse(canvas.event(event("LEFTMOUSE"), 350, 10, clip))
        self.assertTrue(canvas.event(event("LEFTMOUSE"), 20, 20, clip))
        canvas.event(event("MOUSEMOVE"), 100, 20, clip)
        canvas.event(event("ESC"), 100, 20, clip)
        self.assertEqual(value, [0.5])
        self.assertEqual(commits, [])
        canvas.event(event("LEFTMOUSE"), 20, 20, clip)
        canvas.event(event("MOUSEMOVE"), 100, 20, clip)
        canvas.event(event("LEFTMOUSE", "RELEASE"), 100, 20, clip)
        self.assertEqual(len(commits), 1)

    def test_two_vendor_namespaces_import_without_bpy_or_global_alias(self):
        package = Path(__file__).resolve().parents[1] / "beyond_ui"
        for name in ("vendor_a.beyond_ui", "vendor_b.beyond_ui"):
            spec = importlib.util.spec_from_file_location(
                name, package / "__init__.py", submodule_search_locations=[str(package)]
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            self.assertEqual(module.Canvas().__class__.__module__, name + ".canvas")
        self.assertNotIn("bpy", sys.modules)


if __name__ == "__main__":
    unittest.main()
