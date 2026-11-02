"""Deferred native reservations never expose stale controls or poll for visibility."""
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from beyond_ui.hosts.panel import PanelHost


def pointer(n):
    return NS(as_pointer=lambda: n)


class PanelDefer(unittest.TestCase):
    def setUp(self):
        self.context = NS(window=pointer(1), area=pointer(2), region=pointer(3), scene=pointer(4))
        self.context.region.width = self.context.region.height = 100
        self.context.region.tag_redraw = Mock()
        self.host = PanelHost('test')
        self.host._request_resume = Mock()
        self.canvas = NS(visible=False, height=240, park=Mock())
        self.record = dict(canvas=self.canvas, scene=4, valid=False, painted=False, deferred=True)
        self.key = (1, 2, 3)
        self.host.records[self.key] = self.record

    def paint(self, rect):
        with patch.dict(sys.modules, bpy=NS(context=self.context)):
            self.host._paint(self.key, *rect)

    def test_reentry_wakes_once_without_painting_or_enabling_stale_bindings(self):
        self.paint((0, 120, 80, 160))
        self.host._request_resume.assert_not_called()
        self.canvas.park.assert_not_called()  # Already parked; no repeat child traversal.
        self.paint((0, 90, 80, 130))  # Even one visible portion requests refresh.
        self.paint((0, 90, 80, 130))
        self.host._request_resume.assert_called_once_with(self.key)
        self.assertTrue(self.record['resume'])
        self.assertFalse(self.record['valid'])
        self.assertFalse(self.canvas.visible)

    def test_deferral_requires_same_parked_owner_and_no_pending_reentry(self):
        self.host.draw = Mock(return_value=True)
        self.assertTrue(self.host.defer_draw(None, self.context, self.canvas))
        self.host.draw.assert_called_once_with(None, self.context, self.canvas, deferred=True)
        for field, value in [('valid', True), ('resume', True), ('scene', 5), ('canvas', object())]:
            before = self.record.get(field)
            self.record[field] = value
            self.assertFalse(self.host.defer_draw(None, self.context, self.canvas), field)
            self.record[field] = before
        self.canvas.visible = True
        self.assertFalse(self.host.defer_draw(None, self.context, self.canvas))

    def test_cached_reservation_never_measures_or_arranges(self):
        self.context.area.type = 'VIEW_3D'
        self.context.region.type = 'UI'
        self.context.preferences = NS(system=NS(ui_scale=2), view=NS())
        self.host.bridge = NS(next_token=20, records={}, library=NS(bvt_probe_reserve=Mock(return_value=1)))
        self.record['token'] = 19
        self.canvas.arrange = Mock(side_effect=AssertionError('Must not reflow offscreen'))
        self.assertTrue(self.host.defer_draw(NS(column=lambda: pointer(9)), self.context, self.canvas))
        self.host.bridge.library.bvt_probe_reserve.assert_called_once_with(9, 60, 480, 20)
        self.canvas.arrange.assert_not_called()
        self.assertFalse(self.canvas.visible)
        self.assertTrue(self.record['deferred'])

    def test_resume_callback_is_one_shot_and_ignores_revoked_records(self):
        self.context.window.screen = NS(areas=[self.context.area])
        self.context.area.regions = [self.context.region]
        self.context.window_manager = NS(windows=[self.context.window])
        self.host._resume_keys.add(self.key)
        self.record['resume'] = True
        with patch.dict(sys.modules, bpy=NS(context=self.context)):
            self.assertIsNone(self.host._resume_layouts())
            self.assertFalse(self.host._resume_keys)
            self.context.region.tag_redraw.assert_called_once_with()
            self.host._resume_keys.add(self.key)
            self.host.records.clear()
            self.assertIsNone(self.host._resume_layouts())
            self.context.region.tag_redraw.assert_called_once_with()
