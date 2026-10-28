import unittest
from types import SimpleNamespace as NS
from beyond_ui.context_menu import Entry, Menu, Target
from beyond_ui.context_edit import Field
from beyond_ui.editing import number


def event(kind, **kwargs):
    return NS(type=kind, value="PRESS", **kwargs)


class MenuEditing(unittest.TestCase):
    def build(self, value=2):
        values = [value]

        def apply(text, original, target, context):
            if values[0] != original:
                raise ReferenceError("changed")
            values[0] = number(text)

        row = Entry("field", "Value", field=Field(lambda t, c: values[0], apply))
        return values, Menu(Target("owner"), [row], (10, 10), (0, 0, 500, 400))

    def test_deferred_edit_cancel_and_commit(self):
        values, menu = self.build()
        menu.choose(0, None)
        menu.event(event("TEXTINPUT", unicode="7/2"), 20, 20)
        self.assertEqual(values, [2])
        menu.event(event("RET"), 20, 20)
        self.assertEqual(values, [3.5])
        menu.choose(0, None)
        menu.event(event("TEXTINPUT", unicode="8"), 20, 20)
        menu.event(event("RIGHTMOUSE"), 20, 20)
        self.assertIsNone(menu.editor)
        self.assertFalse(menu.closed)
        self.assertEqual(values, [3.5])

    def test_invalid_stale_disabled_and_teardown(self):
        values, menu = self.build()
        menu.choose(0, None)
        menu.event(event("TEXTINPUT", unicode="bad"), 20, 20)
        menu.event(event("RET"), 20, 20)
        self.assertIsNotNone(menu.editor)
        self.assertTrue(menu.error)
        self.assertIsNotNone(menu.tooltip)
        values[0] = 9
        menu.event(event("RET"), 20, 20)
        self.assertEqual(menu.error, "changed")
        menu.close()
        self.assertIsNone(menu.editor)
        self.assertEqual(values, [9])

    def test_text_clipboard_and_bounded_insert_preserve_suffix(self):
        values, menu = self.build("abcdef")
        menu.choose(0, None)
        ctx = NS(window_manager=NS(clipboard="x" * 5000))
        menu.editor.text.move(2)
        menu.event(event("V", ctrl=True), 20, 20, ctx)
        self.assertEqual(len(menu.editor.text.text), 4096)
        self.assertTrue(menu.editor.text.text.endswith("cdef"))
        menu.event(event("A", ctrl=True), 20, 20, ctx)
        menu.event(event("C", ctrl=True), 20, 20, ctx)
        self.assertEqual(ctx.window_manager.clipboard, menu.editor.text.text)
        menu.close()
        self.assertEqual(values, ["abcdef"])

    def test_oversized_initial_value_is_not_truncated_by_edit(self):
        values, menu = self.build("x" * 5000)
        menu.choose(0, None)
        self.assertTrue(menu.closed)
        self.assertIn("limit", menu.error)
        self.assertEqual(len(values[0]), 5000)

    def test_mouse_caret_and_drag_selection_preserve_draft(self):
        values, menu = self.build("abcdef")
        menu.choose(0, None)
        row = next(menu.visible_rows())[1]
        left = row[0] + row[2] * 0.45 + 5
        menu.event(event("LEFTMOUSE"), left + menu.measure("ab", 11), row[1] + 5)
        self.assertIsNotNone(menu.editor)
        self.assertEqual(menu.editor.text.cursor, 2)
        menu.event(
            NS(type="MOUSEMOVE", value="NOTHING"),
            left + menu.measure("abcde", 11),
            row[1] + 5,
        )
        self.assertEqual((menu.editor.text.anchor, menu.editor.text.cursor), (2, 5))
        menu.event(NS(type="LEFTMOUSE", value="RELEASE"), left, row[1] + 5)
        self.assertFalse(menu.editor.dragging)
        menu.event(event("RIGHTMOUSE"), left, row[1] + 5)
        self.assertEqual(values, ["abcdef"])
