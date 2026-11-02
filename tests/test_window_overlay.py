import unittest
from types import SimpleNamespace as NS
from beyond_ui.hosts import window_overlay
from beyond_ui.hosts.bridge import BridgeUnavailable


class Function:
    def __init__(self, callback): self.callback = callback
    def __call__(self, *args): return self.callback(*args)


class WindowOverlayTests(unittest.TestCase):
    def broker(self, admitted=True):
        calls = []
        lib = NS(
            bvt_probe_window_callback=Function(lambda callback: calls.append(('callback', callback))),
            bvt_probe_window_add=Function(lambda pointer: calls.append(('add', pointer)) or (99 if admitted else None)),
            bvt_probe_window_remove=Function(lambda *args: calls.append(('remove', args))),
        )
        return NS(library=lib, errors=[]), NS(as_pointer=lambda: 42), calls

    def test_shared_vendors_dispatch_and_independent_teardown(self):
        state, window, calls = self.broker()
        draws=[]
        window_overlay.attach(state, window, 'first', lambda: draws.append('first'))
        window_overlay.attach(state, window, 'second', lambda: draws.append('second'))
        self.assertEqual(sum(c[0]=='add' for c in calls), 1)
        state.window_overlay_callback(42, None)
        self.assertEqual(draws, ['first','second'])
        window_overlay.detach(state, window, 'first')
        draws.clear();state.window_overlay_callback(42, None)
        self.assertEqual(draws, ['second'])
        window_overlay.detach(state, window, 'second')
        window_overlay.detach(state, window, 'second')
        self.assertEqual(sum(c[0]=='remove' for c in calls), 1)
        self.assertFalse(state.window_overlays)

    def test_failed_admission_never_keeps_a_host(self):
        state, window, calls = self.broker(False)
        with self.assertRaises(BridgeUnavailable):
            window_overlay.attach(state, window, 'first', lambda: None)
        self.assertFalse(state.window_overlays)

    def test_callback_errors_are_bounded_and_do_not_skip_other_hosts(self):
        state, window, calls = self.broker()
        def broken(): raise RuntimeError('consumer error')
        draws=[]
        window_overlay.attach(state, window, 'first', broken)
        window_overlay.attach(state, window, 'second', lambda: draws.append(True))
        for _ in range(20): state.window_overlay_callback(42,None)
        self.assertEqual(len(draws),20)
        self.assertEqual(len(state.errors),16)
        window_overlay.detach(state,window,'first')
        window_overlay.detach(state,window,'second')
