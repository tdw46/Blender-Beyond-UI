import unittest
from types import SimpleNamespace as NS

from beyond_ui.panel_geometry import available_width, measured_gutter, pixel_scale


class NativePanelGeometryTests(unittest.TestCase):
    def test_native_anchor_width_bounds_the_logical_layout(self):
        # Observed NVIDIA native panel: 420px region, 344px Extra button.
        for scale in (1, 1.5, 2):
            gutter = measured_gutter(420, 344, scale)
            width = available_width(420, scale, gutter)
            self.assertLessEqual(width * scale, 344)
            self.assertLess(344 - width * scale, scale * .5)
            self.assertLessEqual(available_width(540, scale, gutter) * scale, 464)

    def test_zoom_changes_fit_but_pan_does_not(self):
        def region(zoom, pan):
            return NS(view2d=NS(region_to_view=lambda x, y: (x / zoom, y / zoom + pan)))
        self.assertEqual(pixel_scale(region(1, -600), 1.5), 1.5)
        self.assertEqual(pixel_scale(region(1.2, -600), 1.5), 1.8)
        self.assertEqual(pixel_scale(region(1.2, -2000), 1.5), 1.8)

    def test_unavailable_view_mapping_preserves_host_scale(self):
        self.assertEqual(pixel_scale(NS(), 1.5), 1.5)
        for span in (0, float('nan'), float('inf')):
            region = NS(view2d=NS(region_to_view=lambda x, y: (x, span if y else 0)))
            self.assertEqual(pixel_scale(region, 1.5), 1.5)
        self.assertEqual(available_width(2, 1.5, 50), 1)
