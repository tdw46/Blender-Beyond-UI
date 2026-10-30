import unittest
from types import SimpleNamespace as NS
from beyond_ui.bindings import Binding
from beyond_ui.list_source import Item, ordered
from beyond_ui.widgets.collection_list import CollectionList


def event(kind, value="PRESS", **kw):
    return NS(type=kind, value=value, **kw)


class Lists(unittest.TestCase):
    def fixture(self, count=10000, **kw):
        state = [0]
        source = NS(
            items=tuple(Item(i, i, f"Row {i:05}", "name") for i in range(count)),
            active=Binding(lambda: state[0], lambda v: state.__setitem__(0, v)),
        )
        source.select = lambda item: source.active.write(item.index)
        widget = CollectionList(source, {}, **kw)
        widget.dimensions(11, 320)
        return widget, state

    def test_visible_cost_and_scroll(self):
        widget, state = self.fixture()
        self.assertLessEqual(len(tuple(widget.visible())), 6)
        widget.scroll_to(widget.limit)
        self.assertEqual(tuple(widget.visible())[-1][0].index, 9999)
        self.assertEqual(state, [0])
        widget.scroll_to(0)
        self.assertEqual(len(tuple(widget.visible(28, 56))), 1)
        self.assertEqual(tuple(widget.visible(28, 56))[0][0].index, 1)
        self.assertEqual(tuple(widget.visible(0, 0)), ())

    def test_wildcards_reverse_original_indices(self):
        items = [
            Item(i, i, name, "name")
            for i, name in enumerate(("Zulu", "Beta", "alpha", "Alphabet"))
        ]
        self.assertEqual(
            [x.index for x in ordered(items, "AL*", alpha=True, reverse=True)], [3, 2]
        )
        self.assertEqual([x.index for x in ordered(items, "AL*", invert=True)], [0, 1])

    def test_keyboard_selects_filtered_original_index(self):
        widget, state = self.fixture()
        widget.state["query"] = "Row 0999"
        widget.reorder()
        widget.focus()
        widget.event(event("END"), 0, 0)
        self.assertEqual(state, [9999])
        widget.event(event("HOME"), 0, 0)
        self.assertEqual(state, [9990])

    def test_resize_cancel_and_bounds(self):
        widget, _ = self.fixture(rows=3, maxrows=8)
        widget.event(event("LEFTMOUSE"), widget.width / 2, widget.viewport + 12)
        widget.event(event("MOUSEMOVE", "NOTHING"), 160, 600)
        self.assertEqual(widget.state["rows"], 8)
        widget.event(event("RIGHTMOUSE"), 160, 600)
        self.assertEqual(widget.state["rows"], 3)
        self.assertFalse(widget.capturing)

    def test_search_cancel_and_motion_disable(self):
        widget, _ = self.fixture()
        widget.search()
        widget.event(event("A", unicode="9"), 0, 0)
        self.assertEqual(widget.state["query"], "9")
        widget.event(event("RIGHTMOUSE"), 0, 0)
        self.assertEqual(widget.state["query"], "")
        widget.toggle("alpha")
        self.assertTrue(widget.motion.tracks)
        widget.motion.settings.enabled = False
        self.assertFalse(widget.motion.tracks)
        self.assertEqual(widget.motion.position(("filter", "alpha"), True), 1)

    def test_scale_is_logical_and_grid_culls(self):
        widget, _ = self.fixture(type="GRID", columns=4)
        for scale in (1, 1.5, 2):
            w, h = widget.dimensions(11 * scale, 320 * scale)
            self.assertEqual((w / scale, h / scale), (320, 166))
            self.assertEqual(widget.grid_columns, 4)
            self.assertLessEqual(len(tuple(widget.visible())), 20)
        widget.dimensions(11, 130)
        self.assertEqual(widget.grid_columns, 1)

    def test_compact_selection_and_sort_lock(self):
        widget, state = self.fixture(type="COMPACT", sort_lock=True)
        widget.event(event("LEFTMOUSE"), 310, 12)
        self.assertEqual(state, [1])
        self.assertEqual(len(tuple(widget.visible())), 1)
        widget.toggle("reverse")
        self.assertNotIn("reverse", widget.state)
