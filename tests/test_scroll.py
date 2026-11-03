"""Gesture direction, zero-delta input and actual popup/list offset regressions."""
import unittest
from types import SimpleNamespace as NS
from beyond_ui.scroll import scroll_delta, scroll_step
from beyond_ui.context_menu import Menu, Target, Entry
from beyond_ui.widgets import DataPicker, Palette, PaletteSource
from beyond_ui.widgets.metrics import PICKER
from beyond_ui.widgets.collection_list import CollectionList
from beyond_ui.list_source import Item
from beyond_ui.bindings import Binding


def event(delta=0, inverted=True, kind='TRACKPADPAN'):
    return NS(type=kind, value='NOTHING', mouse_y=100 + delta, mouse_prev_y=100,
              is_direction_inverted=inverted)


class Scrolling(unittest.TestCase):
    def test_os_direction_is_already_in_delta_and_wheel_is_unchanged(self):
        for inverted in (False, True):
            self.assertEqual(scroll_delta(event(12, inverted)), 12)
            self.assertEqual(scroll_delta(event(-12, inverted)), -12)
            self.assertEqual(scroll_step(event(0, inverted)), 0)
            self.assertEqual(scroll_delta(event(inverted=inverted, kind='WHEELUPMOUSE'), 24), -24)
            self.assertEqual(scroll_delta(event(inverted=inverted, kind='WHEELDOWNMOUSE'), 24), 24)
        self.assertEqual(scroll_delta(NS(type='TRACKPADPAN')), 0)

    def test_picker_offset_and_bounds_in_both_directions(self):
        widget = DataPicker([(i, str(i)) for i in range(100)], lambda key: None)
        x, y, _, _ = PICKER['list']
        widget.event(event(14), x + 4, y + 4)
        self.assertEqual(widget.rows.offset, 14)
        widget.event(event(-4), x + 4, y + 4)
        self.assertEqual(widget.rows.offset, 10)
        widget.event(event(0), x + 4, y + 4)
        self.assertEqual(widget.rows.offset, 10)
        widget.event(event(-1000), x + 4, y + 4)
        self.assertEqual(widget.rows.offset, 0)

    def test_menu_heading_skip_follows_gesture_and_zero_is_noop(self):
        rows = [Entry(str(i), str(i), heading=(i == 2)) for i in range(100)]
        menu = Menu(Target('owner'), rows, (10, 10), (0, 0, 500, 400))
        menu.page.highlight = 1
        x, y, _, _ = menu.page.rect
        menu.event(event(8), x + 5, y + 5)
        self.assertEqual(menu.page.highlight, 3)
        menu.event(event(-8), x + 5, y + 5)
        self.assertEqual(menu.page.highlight, 1)
        menu.event(event(), x + 5, y + 5)
        self.assertEqual(menu.page.highlight, 1)

    def test_collection_and_compact_navigation(self):
        active = [3]
        source = NS(items=tuple(Item(i, i, str(i), 'name') for i in range(100)),
                    active=Binding(lambda: active[0], lambda v: active.__setitem__(0, v)))
        source.select = lambda item: source.active.write(item.index)
        for kind in ('DEFAULT', 'COMPACT'):
            widget = CollectionList(source, {}, type=kind)
            widget.dimensions(11, 320)
            widget.event(event(8), 5, 5)
            if kind == 'COMPACT':
                self.assertEqual(active[0], 4)
            else:
                self.assertEqual(widget.offset, 8)
            widget.event(event(-8), 5, 5)
            self.assertEqual(active[0], 3)
            if kind != 'COMPACT':
                self.assertEqual(widget.offset, 0)

    def test_palette_tracks_direction_without_changing_selected_value(self):
        widget = Palette(PaletteSource(count=lambda: 100, color=lambda i: (0,0,0,1),
                                      active=lambda: 0, select=lambda i: self.fail('Unexpected selection')))
        widget.event(event(8), 30, 90)
        self.assertEqual(widget.row_offset, 1)
        widget.event(event(), 30, 90)
        self.assertEqual(widget.row_offset, 1)
        widget.event(event(-8), 30, 90)
        self.assertEqual(widget.row_offset, 0)


class ListScrollChaining(unittest.TestCase):
    def widget(self, count=100, kind='DEFAULT'):
        active = [0]
        source = NS(items=tuple(Item(i, i, str(i), 'name') for i in range(count)),
                    active=Binding(lambda: active[0], lambda v: active.__setitem__(0, v)))
        source.select = lambda item: source.active.write(item.index)
        widget = CollectionList(source, {}, type=kind)
        widget.dimensions(11, 320)
        return widget, active

    def test_wheel_and_trackpad_chain_outward_at_both_edges(self):
        for mode in ('DEFAULT', 'GRID'):
            for down, up in ((event(kind='WHEELDOWNMOUSE'), event(kind='WHEELUPMOUSE')),
                             (event(12), event(-12))):
                widget, _ = self.widget(kind=mode)
                self.assertFalse(widget.event(up, 5, 5))
                self.assertTrue(widget.event(down, 5, 5))
                self.assertGreater(widget.offset, 0)
                widget.scroll_to(widget.limit)
                self.assertFalse(widget.event(down, 5, 5))
                self.assertTrue(widget.event(up, 5, 5))
                self.assertLess(widget.offset, widget.limit)

    def test_reaching_edge_does_not_scroll_both_list_and_panel(self):
        widget, _ = self.widget()
        widget.scroll_to(widget.limit-1)
        self.assertTrue(widget.event(event(100), 5, 5))
        self.assertEqual(widget.offset, widget.limit)
        self.assertFalse(widget.event(event(1), 5, 5))
        widget.scroll_to(1)
        self.assertTrue(widget.event(event(-100), 5, 5))
        self.assertEqual(widget.offset, 0)
        self.assertFalse(widget.event(event(-1), 5, 5))

    def test_empty_short_and_compact_lists_chain_without_changing_selection(self):
        for count in (0, 1):
            for mode in ('DEFAULT', 'GRID', 'COMPACT'):
                widget, active = self.widget(count, mode)
                for e in (event(10), event(-10)):
                    self.assertFalse(widget.event(e, 5, 5))
                    self.assertEqual(active[0], 0)
        widget, active = self.widget(kind='COMPACT')
        self.assertFalse(widget.event(event(-10), 5, 5))
        self.assertTrue(widget.event(event(10), 5, 5))
        self.assertEqual(active[0], 1)
        active[0] = 99
        self.assertFalse(widget.event(event(10), 5, 5))
        self.assertTrue(widget.event(event(-10), 5, 5))
        self.assertEqual(active[0], 98)

    def test_zero_delta_does_not_start_parent_scroll(self):
        for mode in ('DEFAULT', 'GRID', 'COMPACT'):
            widget, _ = self.widget(kind=mode)
            self.assertTrue(widget.event(event(0), 5, 5))
            self.assertEqual(widget.offset, 0)
