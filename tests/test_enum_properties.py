"""Real enum transactions and full-menu input, independent of Blender."""

import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.bindings import Binding
from beyond_ui.enum_field import EnumField, Item


def event(kind):
    return NS(type=kind, value="PRESS")


class Enums(unittest.TestCase):
    def fixture(self, value="A", flag=False):
        values = [value]
        rows = [Item("A", "Alpha", value=1), Item("B", "Beta", value=2)]
        commits = []
        binding = Binding(
            lambda: values[0],
            lambda v: values.__setitem__(0, v),
            commit=lambda a, b: commits.append((a, b)),
        )
        field = EnumField(binding, lambda: rows, flag=flag)
        return values, rows, commits, binding, field

    def test_noop_and_flag_transactions_preserve_authoritative_values(self):
        values, rows, commits, binding, field = self.fixture()
        field.choose(rows[0])
        self.assertEqual(commits, [])
        field.choose(rows[1])
        self.assertEqual(commits, [("A", "B")])
        values, rows, commits, binding, field = self.fixture({"A"}, True)
        field.choose(rows[1])
        self.assertEqual(values[0], {"A", "B"})
        field.choose(rows[0])
        self.assertEqual(values[0], {"B"})
        self.assertEqual(commits[0], ({"A"}, {"A", "B"}))

    def test_failed_commit_or_rejecting_setter_restores_original(self):
        values, rows, commits, binding, field = self.fixture()

        def fail(a, b):
            raise RuntimeError("commit rejected")

        binding.commit = fail
        with self.assertRaisesRegex(RuntimeError, "commit rejected"):
            field.choose(rows[1])
        self.assertEqual(values[0], "A")
        binding.set = lambda v: None
        with self.assertRaisesRegex(ValueError, "setter rejected"):
            field.choose(rows[1])
        self.assertEqual(commits, [])

    def test_dynamic_removal_numeric_remap_and_concurrent_change_are_rejected(self):
        values, rows, commits, binding, field = self.fixture()
        original = field.snapshot()[1]
        rows[1] = Item("B", "Remapped", value=7)
        with self.assertRaises(ReferenceError):
            field.choose(original)
        rows.pop()
        with self.assertRaises(ReferenceError):
            field.choose(original)
        values[0] = "external"
        with self.assertRaises(ReferenceError):
            field.choose(rows[0], original="A")
        self.assertEqual(values[0], "external")
        self.assertEqual(commits, [])

    def test_paint_label_lookup_does_not_evaluate_dynamic_items(self):
        values, rows, commits, binding, field = self.fixture()
        calls = []
        field.items = lambda: (calls.append(True) or rows)
        field.snapshot()
        for i in range(100):
            self.assertEqual(field.format("B"), "Beta")
            self.assertTrue(field.selected("A"))
        self.assertEqual(len(calls), 1)

    def test_long_menu_opens_by_click_and_reaches_last_item(self):
        values = ["0"]
        canvas = Canvas()
        control = canvas.enum(
            "e",
            "Choices",
            Binding(lambda: values[0], lambda v: values.__setitem__(0, v)),
            items=tuple((str(i), f"Choice {i}") for i in range(200)),
        )
        canvas.arrange(360)
        clip = (0, 0, 360, 220)
        canvas.event(event("LEFTMOUSE"), 15, 15, clip)
        self.assertIsNone(canvas.overlay)
        menu = canvas.context_menu
        self.assertEqual(len(menu.page.rows), 200)
        self.assertLessEqual(len(tuple(menu.visible_rows())), 18)
        canvas.event(event("END"), 20, 50, clip)
        self.assertEqual(menu.page.highlight, 199)
        canvas.event(event("RET"), 20, 50, clip)
        self.assertEqual(values[0], "199")
        self.assertIsNone(canvas.context_menu)
        canvas.event(event("LEFTMOUSE"), 15, 15, clip)
        values[0] = "outside"
        self.assertFalse(canvas.context_menu.valid(None))
        canvas.event(event("RET"), 20, 50, clip)
        self.assertEqual(values[0], "outside")

    def test_reopening_refreshes_items_and_escape_never_commits(self):
        values, rows, commits, binding, field = self.fixture()
        canvas = Canvas()
        c = canvas.enum("e", "Dynamic", binding, items=(), enum_field=field)
        canvas.arrange(360)
        clip = (0, 0, 360, 300)
        canvas.open_enum_menu(c, clip, None)
        self.assertEqual(canvas.context_menu.page.rows[1].label, "Beta")
        canvas.event(event("ESC"), 10, 10, clip)
        rows[1] = Item("C", "Charlie", value=4)
        canvas.open_enum_menu(c, clip, None)
        self.assertEqual(canvas.context_menu.page.rows[1].key, "C")
        canvas.event(event("RIGHTMOUSE"), -1, -1, clip)
        self.assertEqual(commits, [])
        self.assertIsNone(canvas.context_menu)

    def test_raw_canvas_enum_keeps_integer_keys_including_zero(self):
        values = [1]
        canvas = Canvas()
        c = canvas.enum(
            "e",
            "Integer",
            Binding(lambda: values[0], lambda v: values.__setitem__(0, v)),
            items=((0, "Zero"), (1, "One")),
        )
        canvas.arrange(360)
        self.assertTrue(canvas.open_enum_menu(c, (0, 0, 360, 300), None))
        canvas.context_menu.choose(0, None)
        self.assertEqual(values[0], 0)
        self.assertIsInstance(values[0], int)

    def test_bounded_limit_fails_explicitly_instead_of_truncating_choices(self):
        values, rows, commits, binding, field = self.fixture()
        field.items = lambda: (Item(str(i), str(i)) for i in range(4097))
        with self.assertRaisesRegex(ValueError, "4096"):
            field.snapshot()
        field.items = lambda: (Item("A", "A"), Item("A", "Duplicate"))
        with self.assertRaisesRegex(ValueError, "unique"):
            field.snapshot()
