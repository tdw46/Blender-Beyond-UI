import unittest
from types import SimpleNamespace as NS

from beyond_ui import Canvas


def send(canvas, value):
    return canvas.event(NS(type="LEFTMOUSE", value=value), 20, 20,
                        (0, 0, 300, canvas.height))


class ButtonClickThrough(unittest.TestCase):
    def test_double_click_cannot_activate_replacement_page_action(self):
        actions = []
        first = Canvas()
        first.button("next", "Next", lambda: actions.append("next"))
        first.arrange(300)
        self.assertTrue(send(first, "PRESS"))
        send(first, "RELEASE")
        # Navigation authors a new canvas with a different action at this point.
        second = Canvas()
        second.button("open", "Open full controls", lambda: actions.append("open"))
        second.arrange(300)
        self.assertTrue(send(second, "DOUBLE_CLICK"))
        send(second, "RELEASE")
        self.assertEqual(actions, ["next"])
        self.assertTrue(send(second, "PRESS"))
        self.assertEqual(actions, ["next", "open"])

    def test_explicit_double_click_action_is_preserved(self):
        values = []
        canvas = Canvas()
        canvas.button("row", "Row", None, action_event=lambda event: values.append(event.value))
        canvas.arrange(300)
        self.assertTrue(send(canvas, "DOUBLE_CLICK"))
        self.assertEqual(values, ["DOUBLE_CLICK"])


if __name__ == "__main__":
    unittest.main()
