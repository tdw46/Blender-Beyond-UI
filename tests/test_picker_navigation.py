import unittest
from types import SimpleNamespace
from beyond_ui import Canvas
from beyond_ui.widgets import DataPicker
from beyond_ui.widgets.metrics import PICKER


def event(kind, value="PRESS", **kwargs):
    return SimpleNamespace(type=kind, value=value, unicode="", **kwargs)


class PickerNavigation(unittest.TestCase):
    def widget(self, count=10000):
        selected = []
        valid = set(range(count))
        widget = DataPicker(
            tuple((i, f"Object {i}", "object") for i in range(count)),
            selected.append,
            selected=lambda: 0,
            valid=lambda key: key in valid,
        )
        return widget, selected, valid

    def test_navigation_pages_reveal_accept_and_stale_revalidation(self):
        widget, selected, valid = self.widget()
        self.assertFalse(widget.event(event("DOWN_ARROW"), 0, 0))
        widget.focus()
        widget.event(event("END"), 0, 0)
        self.assertEqual(widget.cursor, 9999)
        self.assertAlmostEqual(widget.rows.offset, widget.rows.height - 206)
        self.assertEqual(selected, [])
        widget.event(event("PAGE_UP"), 0, 0)
        self.assertEqual(widget.cursor, 9997)
        valid.remove(9997)
        widget.event(event("RET"), 0, 0)
        self.assertEqual(selected, [])
        widget.event(event("UP_ARROW"), 0, 0)
        widget.event(event("RET"), 0, 0)
        self.assertEqual(selected, [9996])
        widget.event(event("HOME"), 0, 0)
        self.assertEqual(widget.rows.offset, 0)
        widget.event(event("ESC"), 0, 0)
        self.assertFalse(widget.focused)

    def test_scroll_thumb_drag_cancel_and_track_paging(self):
        widget, _, _ = self.widget()
        thumb, travel, limit = widget.scrollbar()
        self.assertGreaterEqual(thumb[3], 12)
        x, y, w, h = thumb
        widget.event(event("LEFTMOUSE"), x + w / 2, y + h / 2)
        self.assertTrue(widget.capturing)
        widget.event(event("MOUSEMOVE"), x, y + h / 2 + travel)
        self.assertAlmostEqual(widget.rows.offset, limit)
        widget.event(event("ESC"), x, y)
        self.assertEqual(widget.rows.offset, 0)
        self.assertFalse(widget.capturing)
        widget.event(event("LEFTMOUSE"), x, y + h + 20)
        self.assertEqual(widget.rows.offset, 206)
        thumb, travel, limit = widget.scrollbar()
        widget.event(event("LEFTMOUSE"), x, thumb[1] + thumb[3] / 2)
        widget.event(event("MOUSEMOVE"), x, 10000)
        widget.event(event("LEFTMOUSE", "RELEASE"), x, 10000)
        self.assertEqual(widget.rows.offset, limit)
        self.assertIsNone(widget.scroll_drag)

    def test_keyboard_focus_survives_pointer_exit_but_not_outside_click_or_hide(self):
        widget, selected, _ = self.widget(10)
        canvas = Canvas()
        control = canvas.widget("picker", widget)
        canvas.arrange(646)
        clip = (0, 0, 646, canvas.height)
        canvas.event(
            event("LEFTMOUSE"), control.rect[0] + 100, control.rect[1] + 175, clip
        )
        self.assertIs(canvas.keyboard_focus, control)
        canvas.event(event("DOWN_ARROW"), -100, -100, clip)
        canvas.event(event("RET"), -100, -100, clip)
        self.assertEqual(selected, [0, 1])
        canvas.event(event("LEFTMOUSE"), -100, -100, clip)
        self.assertIsNone(canvas.keyboard_focus)
        self.assertFalse(widget.focused)
        canvas.event(
            event("LEFTMOUSE"), control.rect[0] + 100, control.rect[1] + 175, clip
        )
        canvas.park()
        self.assertIsNone(canvas.keyboard_focus)
        self.assertFalse(widget.focused)

    def test_search_enter_and_text_home_do_not_conflict(self):
        widget, selected, _ = self.widget(20)
        widget.event(event("LEFTMOUSE"), 50, 100)
        widget.text_edit.insert("Object 12")
        widget.event(event("HOME"), 0, 0)
        self.assertEqual(widget.text_edit.cursor, 0)
        self.assertIsNone(widget.cursor)
        widget.event(event("RET"), 0, 0)
        self.assertEqual(selected, [12])
        self.assertIsNone(widget.text_edit)
        self.assertFalse(widget.capturing)


if __name__ == "__main__":
    unittest.main()
