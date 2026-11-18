import unittest
from types import SimpleNamespace

from beyond_ui.callback_panel import WindowedRows
from beyond_ui.widgets.retained_board import ReorderGesture, expanding_rows, row_viewports


class RetainedBoardTests(unittest.TestCase):
    def test_reveal_keeps_original_row_members_and_exposes_horizontal_overflow(self):
        entries = [('a', 45), ('b', 60), ('c', 20)]
        collapsed, _ = expanding_rows(116, 5, entries, '')
        expanded, _ = expanding_rows(116, 5, entries, 'a')
        self.assertEqual([r[1] for r in collapsed], [r[1] for r in expanded])
        self.assertGreater(expanded[0][2], collapsed[0][2])
        metrics = row_viewports(116, expanded)
        self.assertEqual(metrics[0], metrics[1])
        self.assertGreater(metrics[0][2], 0)
        self.assertEqual(metrics[-1][2], 0)

    def test_drag_threshold_and_leaving_the_valid_drop_bounds(self):
        gesture = ReorderGesture((0, 0), [('a', (0, 0, 40, 20)), ('b', (0, 24, 40, 20))])
        self.assertFalse(gesture.update((2, 2), 25, True))
        self.assertTrue(gesture.update((15, 2), 25, True))
        self.assertEqual(gesture.drop, ('b', True))
        self.assertFalse(gesture.update((20, 3), 30, True))
        self.assertTrue(gesture.update((50, 0), 30, False))
        self.assertIsNone(gesture.drop)

    def test_windowed_rows_keep_both_ends_reachable_and_small_lists_intact(self):
        heights = []
        layout = SimpleNamespace(canvas=SimpleNamespace(theme=SimpleNamespace(row_height=24, gap=4)),
                                 group=SimpleNamespace(label=lambda *a,height: heights.append(height)),
                                 _key=lambda kind: kind)
        window = WindowedRows(16)
        values = range(1000)
        self.assertEqual(list(window.visible(layout, values)), list(values[:32]))
        self.assertTrue(window.move(27900, 300))
        tail = list(window.visible(layout, values))
        self.assertEqual(tail[-1], 999)
        self.assertLess(len(tail), 50)
        self.assertTrue(window.move(0, 300))
        self.assertEqual(list(window.visible(layout, range(5))), list(range(5)))
        self.assertTrue(all(h > 0 for h in heights))
