import unittest
from types import SimpleNamespace as NS
from beyond_ui.context_menu import Entry, Target, Menu, Shortcut
from beyond_ui.bindings import rna_binding
from beyond_ui.registered_menu import retarget


def event(kind, **kw):
    return NS(type=kind, value="PRESS", **kw)


class RowContext(unittest.TestCase):
    def test_invalid_inline_context_cancels_without_swallowing_outside_right_click(
        self,
    ):
        from beyond_ui import Canvas

        canvas = Canvas()

        def invalid(context):
            raise ReferenceError("Stale menu")

        control = canvas.button("menu", "Menu", lambda: None, activation_guard=invalid)
        canvas._context_guarded = True
        canvas.arrange(300)
        canvas.active = control
        self.assertFalse(canvas.event(event("RIGHTMOUSE"), -1, -1, (0, 0, 300, 200)))
        self.assertIsNone(canvas.active)

    def test_large_menu_refresh_polls_visible_rows_and_rechecks_hidden_actions(self):
        counts = []
        allowed = [True] * 1000
        calls = []

        def enabled(index):
            counts.append(index)
            return allowed[index]

        rows = tuple(
            Entry(
                str(i),
                f"Action {i}",
                lambda t, c, i=i: calls.append(i),
                enabled=lambda t, c, i=i: enabled(i),
                bindings=(Shortcut("K"),) if i == 999 else (),
            )
            for i in range(1000)
        )
        menu = Menu(
            Target("owner"),
            rows,
            (20, 20),
            (0, 0, 500, 400),
            row_limit=1000,
            visible_refresh=True,
        )
        counts.clear()
        menu.event(NS(type="MOUSEMOVE", value="NOTHING"), 30, 80)
        self.assertLessEqual(len(counts), 19)
        allowed[999] = False
        menu.choose(999, None)
        self.assertEqual(calls, [])
        allowed[999] = True
        menu.event(event("K"), 30, 80)
        self.assertEqual(calls, [999])

    def menu(self):
        calls = []
        row = Entry(
            "row",
            "Owner",
            enabled=False,
            context=lambda t, c: (
                Entry("copy", "Copy", lambda t, c: calls.append(t.key)),
            ),
        )
        return Menu(Target("exact-owner"), (row,), (20, 20), (0, 0, 500, 400)), calls

    def test_disabled_row_can_expose_readonly_context_actions(self):
        menu, calls = self.menu()
        _, rect, _ = next(menu.visible_rows())
        menu.event(event("RIGHTMOUSE"), rect[0] + 5, rect[1] + 5)
        self.assertEqual(len(menu.parents), 1)
        self.assertEqual(menu.page.rows[0].key, "__back__")
        menu.choose(1, None)
        self.assertEqual(calls, ["exact-owner"])

    def test_keyboard_context_back_and_outside_passthrough(self):
        menu, calls = self.menu()
        self.assertTrue(menu.event(event("F10", shift=True), -10, -10))
        self.assertEqual(len(menu.parents), 1)
        menu.event(event("LEFT_ARROW"), 0, 0)
        self.assertEqual(len(menu.parents), 0)
        self.assertFalse(menu.event(event("RIGHTMOUSE"), -10, -10))
        self.assertTrue(menu.closed)
        self.assertEqual(calls, [])

    def test_retarget_nested_actions_keep_ownership_and_revalidate(self):
        valid = [True]
        calls = []
        owner = Target("actual", valid=lambda: valid[0])
        rows = retarget(
            (
                Entry(
                    "nested",
                    "Nested",
                    children=lambda t, c: (
                        Entry("write", "Write", lambda t, c: calls.append(t.key)),
                    ),
                ),
            ),
            owner,
        )
        menu = Menu(Target("outer"), rows, (20, 20), (0, 0, 500, 400))
        menu.choose(0, None)
        valid[0] = False
        menu.choose(1, None)
        self.assertEqual(calls, [])
        self.assertFalse(menu.page.available[1])
        valid[0] = True
        menu.choose(1, None)
        self.assertEqual(calls, ["actual"])

    def test_original_id_is_validated_before_embedded_resolve(self):
        dead = [False]
        reads = []

        def pointer():
            if dead[0]:
                raise ReferenceError("ID removed")
            return 10

        data = NS(as_pointer=pointer)
        obj = NS(
            id_data=data,
            as_pointer=lambda: 20,
            value=1,
            bl_rna=NS(properties={"value": NS(is_readonly=False)}),
        )

        def resolve():
            reads.append(True)
            if dead[0]:
                raise AssertionError("Dereferenced freed embedded RNA")
            return obj

        binding = rna_binding(resolve, "value")
        count = len(reads)
        dead[0] = True
        self.assertFalse(binding.valid())
        self.assertFalse(binding.context.valid())
        with self.assertRaises(ReferenceError):
            binding.write(4)
        self.assertEqual(len(reads), count)
