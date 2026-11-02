"""Exact-build, window-level presentation after region compositing.

The native bridge owns no Python objects. Its process-lifetime broker retains
one callback across vendored copies, with one native handle per live window.
"""
import ctypes
from contextlib import contextmanager
from .bridge import BridgeUnavailable


def attach(bridge, window, owner, draw):
    if not hasattr(bridge, 'window_overlays'):
        lib = bridge.library
        try:
            lib.bvt_probe_window_callback.argtypes = [ctypes.c_void_p]
            lib.bvt_probe_window_callback.restype = None
            lib.bvt_probe_window_add.argtypes = [ctypes.c_void_p]
            lib.bvt_probe_window_add.restype = ctypes.c_void_p
            lib.bvt_probe_window_remove.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            lib.bvt_probe_window_remove.restype = None
        except AttributeError as error:
            raise BridgeUnavailable('Window overlay presentation is unavailable') from error
        bridge.window_overlays = {}

        def present(pointer, _data):
            entry = bridge.window_overlays.get(pointer)
            if entry is None:
                return
            for callback in tuple(entry['owners'].values()):
                try:
                    callback()
                except Exception as error:
                    bridge.errors.append(repr(error))
                    bridge.errors[:] = bridge.errors[-16:]

        bridge.window_overlay_callback = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p)(present)
        lib.bvt_probe_window_callback(bridge.window_overlay_callback)
    pointer = window.as_pointer()
    entry = bridge.window_overlays.get(pointer)
    if entry is None:
        handle = bridge.library.bvt_probe_window_add(pointer)
        if not handle:
            raise BridgeUnavailable('Window overlay callback is unavailable on this build')
        entry = bridge.window_overlays[pointer] = dict(handle=handle, owners={})
    entry['owners'][owner] = draw


def detach(bridge, window, owner):
    """Remove only this host; retain the shared callback for other vendors."""
    pointer = window.as_pointer()
    entry = getattr(bridge, 'window_overlays', {}).get(pointer)
    if entry is None:
        return
    entry['owners'].pop(owner, None)
    if not entry['owners']:
        bridge.library.bvt_probe_window_remove(pointer, entry['handle'])
        del bridge.window_overlays[pointer]


@contextmanager
def scissor_scope():
    """The audited WM callback stage enters with region scissoring disabled."""
    import gpu
    gpu.state.scissor_test_set(True)
    try:
        yield
    finally:
        gpu.state.scissor_test_set(False)
