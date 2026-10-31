import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.context_menu import Entry, Target, Menu
from beyond_ui.pie_menu import PieMenu, DIRECTIONS, sector


def event(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


def point(menu, index=0):
    _, (x, y, w, h), _ = next(r for r in menu.visible_rows() if r[0] == index)
    return x + w / 2, y + h / 2


class Release(unittest.TestCase):
    def build(self, **kw):
        calls = []
        menu = Menu(
            Target("owner"),
            (Entry("a", "Action", lambda t, c: calls.append(t.key), **kw),),
            (20, 20),
            (0, 0, 640, 400),
        )
        return menu, calls

    def test_action_runs_only_on_matching_release(self):
        menu, calls = self.build()
        p = point(menu)
        menu.event(event("LEFTMOUSE"), *p)
        self.assertEqual(calls, [])
        menu.event(event("RET"), *p)
        menu.event(event("TIMER", "NOTHING"), *p)
        self.assertEqual(calls, [])
        self.assertTrue(menu.event(event("LEFTMOUSE", "RELEASE"), *p))
        self.assertEqual(calls, ["owner"])
        self.assertIsNone(menu.pending_click)

    def test_cancel_drag_out_and_stale_row_never_dispatch(self):
        for mode in ("ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE", "outside", "replace"):
            menu, calls = self.build()
            p = point(menu)
            menu.event(event("LEFTMOUSE"), *p)
            if mode == "replace":
                menu.page.rows = (replace(menu.page.rows[0], label="New owner"),)
            elif mode != "outside":
                menu.event(event(mode), *p)
                self.assertTrue(menu.closed)
            if not menu.closed:
                menu.event(
                    event("LEFTMOUSE", "RELEASE"),
                    *(p if mode == "replace" else (-1, -1)),
                )
            self.assertEqual(calls, [], mode)
            self.assertIsNone(menu.pending_click)

    def test_disabled_or_removed_owner_revalidated_at_release(self):
        allowed = [True]
        menu, calls = self.build(enabled=lambda t, c: allowed[0])
        p = point(menu)
        menu.event(event("LEFTMOUSE"), *p)
        allowed[0] = False
        menu.event(event("LEFTMOUSE", "RELEASE"), *p)
        self.assertEqual(calls, [])
        allowed[0] = True
        menu.event(event("LEFTMOUSE"), *p)
        menu.target = Target("owner", valid=lambda: False)
        menu.event(event("LEFTMOUSE", "RELEASE"), *p)
        self.assertTrue(menu.closed)
        self.assertEqual(calls, [])

    def test_replacement_menu_survives_and_does_not_receive_release(self):
        canvas = Canvas()
        calls = []
        successor = Menu(
            Target("second"),
            (Entry("second", "Second", lambda t, c: calls.append(2)),),
            (20, 20),
            (0, 0, 640, 400),
        )
        first = Menu(
            Target("first"),
            (
                Entry(
                    "first",
                    "First",
                    lambda t, c: setattr(canvas, "context_menu", successor),
                ),
            ),
            (20, 20),
            (0, 0, 640, 400),
        )
        canvas.context_menu = first
        p = point(first)
        canvas.event(event("LEFTMOUSE"), *p, first.clip)
        canvas.event(event("LEFTMOUSE", "RELEASE"), *p, first.clip)
        self.assertIs(canvas.context_menu, successor)
        self.assertEqual(calls, [])
        self.assertIsNone(successor.pending_click)


class Pies(unittest.TestCase):
    def build(self, **kw):
        self.calls = []
        rows = tuple(
            Entry(str(i), f"Action {i}", lambda t, c, i=i: self.calls.append(i))
            for i in range(8)
        )
        return PieMenu(Target("owner"), rows, (320, 220), (0, 0, 640, 440), **kw)

    def test_eight_directions_dead_zone_and_release(self):
        for i, (dx, dy) in enumerate(DIRECTIONS):
            self.assertEqual(sector((0, 0), dx * 100, dy * 100), i)
            menu = self.build(trigger="Q")
            x, y = menu.origin
            menu.event(event("MOUSEMOVE", "NOTHING"), x + dx * 80, y + dy * 80)
            self.assertEqual(menu.page.highlight, i)
            self.assertEqual(self.calls, [])
            menu.event(event("Q", "RELEASE"), x + dx * 80, y + dy * 80)
            self.assertEqual(self.calls, [i])
            self.assertTrue(menu.closed)
        self.assertIsNone(sector((0, 0), 4, 4))

    def test_center_release_enters_click_mode(self):
        menu = self.build(trigger="Q")
        menu.event(event("Q", "RELEASE"), *menu.origin)
        self.assertFalse(menu.closed)
        self.assertIsNone(menu.trigger)
        p = point(menu, 3)
        menu.event(event("LEFTMOUSE"), *p)
        self.assertEqual(self.calls, [])
        menu.event(event("LEFTMOUSE", "RELEASE"), *p)
        self.assertEqual(self.calls, [3])

    def test_visible_petals_win_over_angular_sectors(self):
        for i in range(8):
            menu = self.build(trigger="Q")
            menu.event(event("MOUSEMOVE", "NOTHING"), *point(menu, i))
            menu.event(event("Q", "RELEASE"), *point(menu, i))
            self.assertEqual(self.calls, [i])

    def test_geometry_edges_fallback_and_bounded_input(self):
        menu = self.build()
        rects = tuple(menu.visible_rows())
        for _, (x, y, w, h), _ in rects:
            self.assertTrue(0 <= x < x + w <= 640)
            self.assertTrue(0 <= y < y + h <= 440)
        self.assertEqual(len(menu.surfaces(menu.page)), 8)
        rows = menu.page.rows
        small = PieMenu(Target("owner"), rows, (0, 0), (0, 0, 280, 300))
        self.assertEqual(small.layout_mode, "LIST_FALLBACK")
        self.assertEqual(len(small.surfaces(small.page)), 1)
        from itertools import repeat

        with self.assertRaises(ValueError):
            PieMenu(Target("owner"), repeat(rows[0]), (0, 0), (0, 0, 640, 440))
        for dead in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.build(dead_zone=dead)

    def test_context_back_keyboard_and_disabled_settings(self):
        menu = self.build()
        rows = list(menu.page.rows)
        rows[0] = replace(
            rows[0],
            context=lambda t, c: (
                Entry("copy", "Copy owner", lambda t, c: self.calls.append(t.key)),
            ),
        )
        menu.page.rows = tuple(rows)
        menu.event(event("RIGHTMOUSE"), *point(menu))
        self.assertFalse(menu.radial())
        menu.event(event("ESC"), 0, 0)
        self.assertTrue(menu.radial())
        menu.motion.settings.enabled = False
        menu.motion.pulse("reveal")
        self.assertEqual(menu.motion.strength, 0)
        menu.event(event("NUMPAD_9", is_repeat=True), 0, 0)
        self.assertEqual(self.calls, [])
        menu.event(event("NUMPAD_9"), 0, 0)
        self.assertEqual(self.calls, [5])

    def test_canvas_host_trigger_and_stale_owner(self):
        canvas = Canvas()
        valid = [True]
        calls = []
        self.assertTrue(
            canvas.open_pie(
                Target("owner", valid=lambda: valid[0]),
                [Entry("a", "Action", lambda t, c: calls.append(1))],
                (320, 200),
                (0, 0, 640, 400),
                trigger="Q",
            )
        )
        valid[0] = False
        canvas.event(event("Q", "RELEASE"), 200, 200, (0, 0, 640, 400))
        self.assertEqual(calls, [])
        self.assertIsNone(canvas.context_menu)


if __name__ == "__main__":
    unittest.main()
