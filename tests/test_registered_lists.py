import unittest
from itertools import repeat
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.list_source import Item
from beyond_ui.registered_list import SHOW, NEVER, filter_order


class RegisteredLists(unittest.TestCase):
    def setUp(self):
        self.items = tuple(Item(i, i, str(i), "name") for i in range(4))

    def indices(self, flags=(), order=(), **kw):
        return [i.index for i in filter_order(self.items, flags, order, **kw)[0]]

    def test_filter_destination_order_and_never_show(self):
        flags = (SHOW | 7, 0, SHOW | NEVER, SHOW)
        self.assertEqual(self.indices(flags, (3, 1, 0, 2)), [3, 0])
        self.assertEqual(self.indices(flags, (3, 1, 0, 2), reverse=True), [0, 3])
        self.assertEqual(self.indices(flags, invert=True), [1])
        self.assertEqual(filter_order(self.items, flags, ())[1], flags)
        self.assertEqual(self.indices((), (), reverse=True), [3, 2, 1, 0])

    def test_bad_callback_output_is_bounded_and_rejected(self):
        for flags, order in (
            ([SHOW], []),
            (repeat(SHOW), []),
            ([SHOW, SHOW, -1, SHOW], []),
            ([SHOW, SHOW, True, SHOW], []),
            ([], [0, 1, 2, 2]),
            ([], repeat(0)),
        ):
            with self.subTest(flags=flags, order=order), self.assertRaises(ValueError):
                filter_order(self.items, flags, order)

    def test_clipped_composite_cancels_without_advancing_children(self):
        from beyond_ui.animation import Motion

        calls = []
        canvas = Canvas()
        widget = NS(
            motion=Motion(),
            route=lambda: None,
            cancel=lambda: calls.append("cancel"),
            advance=lambda clip=None: calls.append("advance") or True,
        )
        control = canvas.widget("list", widget)
        control.rect = (0, 100, 100, 50)
        calls.clear()
        self.assertFalse(canvas.advance_animations((0, 0, 100, 50)))
        self.assertEqual(calls, ["cancel"])

    def test_composite_registry_pruned_after_authoring_rollback(self):
        from beyond_ui.animation import Motion

        canvas = Canvas()
        widget = NS(
            motion=Motion(),
            route=lambda: None,
            cancel=lambda: None,
            advance=lambda clip=None: False,
            active_menu=lambda: None,
        )
        canvas.widget("list", widget)
        self.assertEqual(tuple(canvas._composites), ("list",))
        canvas.controls.pop("list")
        canvas.children.clear()
        canvas.invalidate()
        self.assertEqual(canvas._composites, {})
        self.assertIsNone(canvas.active_menu())
        self.assertFalse(canvas.advance_animations())


if __name__ == "__main__":
    unittest.main()
