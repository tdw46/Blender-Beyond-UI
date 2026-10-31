import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.context_menu import Entry


def event(kind, value="PRESS"):
    return NS(type=kind, value=value)


class HoldTests(unittest.TestCase):
    def setup(self, hold=True):
        self.now = [0.0]
        self.calls = []
        self.context = NS()
        self.clip = (0, 0, 400, 500)
        self.canvas = Canvas()
        self.model = NS(
            context=self.context,
            pie=False,
            rows=lambda ctx: (
                (Entry("child", "Child", lambda t, c: self.calls.append("child")),),
                lambda: True,
            ),
        )
        self.control = self.canvas.button(
            "button",
            "Hold",
            lambda: self.calls.append("primary"),
            hold_menu=self.model if hold else None,
            release_action=True,
        )
        self.canvas.arrange(400)
        self.control.motion.clock = lambda: self.now[0]
        self.point = (20, 20)

    def send(self, kind, value="PRESS", point=None, context=None):
        return self.canvas.event(
            event(kind, value),
            *(point or self.point),
            self.clip,
            context=context or self.context,
        )

    def test_quick_release_executes_once_not_on_press(self):
        self.setup()
        self.send("LEFTMOUSE")
        self.assertEqual(self.calls, [])
        self.now[0] = 0.199
        self.send("LEFTMOUSE", "RELEASE")
        self.send("LEFTMOUSE", "RELEASE")
        self.assertEqual(self.calls, ["primary"])
        self.assertFalse(self.canvas.advance_animations(context=self.context))

    def test_hold_opens_while_motion_disabled_and_owns_release(self):
        self.setup()
        self.canvas.animation.enabled = False
        self.send("LEFTMOUSE")
        self.assertTrue(self.canvas.advance_animations(context=self.context))
        self.now[0] = 0.2
        self.canvas.advance_animations(context=self.context)
        menu = self.canvas.context_menu
        self.assertIsNotNone(menu)
        self.assertEqual(menu.motion.strength, 0)
        _, (x, y, w, h), _ = next(menu.visible_rows())
        self.send("LEFTMOUSE", "RELEASE", (x + 5, y + 5))
        self.assertEqual(self.calls, [])
        self.assertIs(self.canvas.context_menu, menu)
        self.send("LEFTMOUSE", point=(x + 5, y + 5))
        self.send("LEFTMOUSE", "RELEASE", (x + 5, y + 5))
        self.assertEqual(self.calls, ["child"])

    def test_late_release_cannot_run_primary_after_deadline(self):
        self.setup()
        self.send("LEFTMOUSE")
        self.now[0] = 1
        self.send("LEFTMOUSE", "RELEASE")
        self.assertEqual(self.calls, [])
        self.assertIsNotNone(self.canvas.context_menu)
        self.assertIsNone(self.canvas._button_press)

    def test_drag_off_cancel_disable_replacement_and_context_change(self):
        for change in ("move", "cancel", "disable", "replace", "context"):
            with self.subTest(change=change):
                self.setup()
                self.send("LEFTMOUSE")
                if change == "move":
                    self.send("MOUSEMOVE", "NOTHING", (500, 500))
                if change == "cancel":
                    self.send("RIGHTMOUSE")
                if change == "disable":
                    self.control.options["enabled"] = False
                if change == "replace":
                    self.canvas.controls.pop("button")
                self.send(
                    "LEFTMOUSE",
                    "RELEASE",
                    context=NS(mode="EDIT") if change == "context" else None,
                )
                self.assertEqual(self.calls, [])
                self.assertIsNone(self.canvas.context_menu)

    def test_release_only_button_never_schedules_hold_work(self):
        self.setup(False)
        self.send("LEFTMOUSE")
        self.now[0] = 1
        self.assertFalse(self.canvas.advance_animations(context=self.context))
        self.send("LEFTMOUSE", "RELEASE")
        self.assertEqual(self.calls, ["primary"])

    def test_release_drives_source_motion_and_invalidations_drop_hold(self):
        self.setup()
        self.control.motion.region("body", self.control.rect)
        self.send("LEFTMOUSE")
        self.assertEqual(self.control.motion.pressed, "body")
        self.now[0] = 0.1
        self.send("LEFTMOUSE", "RELEASE")
        self.assertIsNone(self.control.motion.pressed)
        self.assertTrue(self.control.motion.advance())
        self.send("LEFTMOUSE")
        self.canvas.invalidate()
        self.now[0] = 0.4
        self.assertFalse(self.canvas.advance_animations(context=self.context))
        self.assertIsNone(self.canvas.context_menu)
        self.assertEqual(self.calls, ["primary"])

    def test_closed_host_discards_pending_deadline(self):
        self.setup()
        self.send("LEFTMOUSE")
        self.canvas.park()
        self.now[0] = 1
        self.assertFalse(self.canvas.advance_animations(context=self.context))
        self.assertIsNone(self.canvas.context_menu)
        self.assertEqual(self.calls, [])
