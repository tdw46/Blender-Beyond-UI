"""Native panel scroll ownership survives pointer/layout movement into UI lists."""
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from beyond_ui.hosts.addon import Runtime
from beyond_ui.scroll import NativeScrollGesture, panel_scroll_region


def pointer(number, **kw):
    return NS(as_pointer=lambda: number, **kw)


def context(window=1, region=3, kind='VIEW_3D'):
    r = pointer(region, type='UI' if kind == 'VIEW_3D' else 'WINDOW',
                x=200, y=0, width=300, height=600)
    a = pointer(2, type=kind, regions=[r], spaces=NS(active=NS(show_region_ui=True)))
    # The modal invoke context need not be the current region under the pointer.
    return NS(window=pointer(window, screen=NS(areas=[a])), region=None)


def event(kind='WHEELDOWNMOUSE', x=240, y=300, value='PRESS'):
    return NS(type=kind, value=value, mouse_x=x, mouse_y=y,
              mouse_prev_y=y-8, is_direction_inverted=True)


class ScrollOwnership(TestCase):
    def setup_runtime(self):
        rt = Runtime(NS(owner='scroll.test'), ())
        host = NS(event=Mock(return_value=False))
        rt.hosts = {type('Panel', (), {}): host}
        return rt, host

    def send(self, rt, ctx, e, now):
        with patch('beyond_ui.hosts.addon.time.monotonic', return_value=now):
            return rt.dispatch_event(None, ctx, e)

    def test_native_gesture_crosses_list_without_capture_on_both_event_families(self):
        for kind in ('WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'TRACKPADPAN'):
            for area_type in ('VIEW_3D', 'PROPERTIES'):
                with self.subTest(kind=kind, area=area_type):
                    rt, host = self.setup_runtime(); ctx = context(kind=area_type)
                    self.assertEqual(self.send(rt, ctx, event(kind), 1), {'PASS_THROUGH'})
                    # After a native scroll/reflow the pointer now hits a list.
                    host.event.return_value = True
                    for n in range(1, 25):
                        self.send(rt, ctx, event('MOUSEMOVE', value='NOTHING'), 1+n*.05)
                        self.assertEqual(self.send(rt, ctx, event(kind, x=400), 1+n*.05), {'PASS_THROUGH'})
                    # Mouse move may update hover, but no continuation reached a list.
                    self.assertEqual(sum(c.args[1].type == kind for c in host.event.call_args_list), 1)
                    self.assertEqual(self.send(rt, ctx, event(kind, x=400), 2.55), {'RUNNING_MODAL'})

    def test_first_gesture_on_list_is_not_delayed(self):
        rt, host = self.setup_runtime(); host.event.return_value = True
        for now in (1, 1.01, 1.2, 2):
            self.assertEqual(self.send(rt, context(), event(), now), {'RUNNING_MODAL'})
        self.assertFalse(rt.native_scroll.windows)

    def test_explicit_click_key_or_deactivation_ends_old_ownership(self):
        for kind in ('LEFTMOUSE', 'RIGHTMOUSE', 'ESC', 'WINDOW_DEACTIVATE'):
            rt, host = self.setup_runtime(); ctx = context()
            self.send(rt, ctx, event(), 1)
            self.send(rt, ctx, event(kind), 1.01)
            host.event.return_value = True
            self.assertEqual(self.send(rt, ctx, event(), 1.02), {'RUNNING_MODAL'})

    def test_timer_and_zero_delta_tail_keep_native_ownership(self):
        rt, host = self.setup_runtime(); ctx = context()
        self.send(rt, ctx, event(), 1)
        self.send(rt, ctx, event('TIMER', value='NOTHING'), 1.1)
        host.event.return_value = True
        zero=event('TRACKPADPAN');zero.mouse_prev_y=zero.mouse_y
        self.assertEqual(self.send(rt, ctx, zero, 1.2), {'PASS_THROUGH'})
        self.assertEqual(self.send(rt, ctx, event(), 1.4), {'PASS_THROUGH'})
        self.assertEqual(self.send(rt, ctx, event(), 1.71), {'RUNNING_MODAL'})

    def test_regions_windows_and_pointer_outside_do_not_share_ownership(self):
        for other in (context(window=4), context(region=5)):
            rt, host = self.setup_runtime()
            self.send(rt, context(), event(), 1);host.event.return_value = True
            self.assertEqual(self.send(rt, other, event(), 1.1), {'RUNNING_MODAL'})
        rt, host = self.setup_runtime();ctx=context()
        self.send(rt, ctx, event(), 1)
        self.send(rt, ctx, event(x=20), 1.1)
        host.event.return_value = True
        self.assertEqual(self.send(rt, ctx, event(), 1.2), {'RUNNING_MODAL'})

    def test_all_hosts_must_decline_before_native_latch_starts(self):
        rt, host = self.setup_runtime()
        rt.hosts[type('OtherPanel', (), {})] = NS(event=Mock(return_value=True))
        self.assertEqual(self.send(rt, context(), event(), 1), {'RUNNING_MODAL'})
        self.assertFalse(rt.native_scroll.windows)

    def test_hidden_sidebar_and_region_edges(self):
        ctx=context()
        self.assertIsNone(panel_scroll_region(ctx,event(x=500)))
        self.assertEqual(panel_scroll_region(ctx,event(x=499)),(1,2,3))
        ctx.window.screen.areas[0].spaces.active.show_region_ui=False
        self.assertIsNone(panel_scroll_region(ctx,event()))

    def test_bounded_scalar_state_and_expiry(self):
        gate=NativeScrollGesture()
        for i in range(20):gate.remember((i,2,3),1)
        self.assertEqual(len(gate.windows),16)
        self.assertFalse(gate.continuing((19,2,3),2))
        gate.clear();self.assertFalse(gate.windows)
