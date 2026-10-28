"""Test-only native BLF batching, admitted against the exact installed build.

Production uses public blf APIs only. These void/no-argument symbols reproduce
Blender's enclosing UI text batch in a disposable offscreen capture fixture.
"""

from contextlib import contextmanager
import ctypes, hashlib, os
from pathlib import Path


def configure():
    import bpy
    from beyond_ui.hosts.menu_native import api, reason
    from beyond_ui.gpu import menus

    assert bpy.app.build_hash.decode() in {"ec6e62d40fa9", "d13f752e3b9c"}
    assert api() is not None, reason()  # Exact source/executable admission.
    library = ctypes.CDLL(None)
    begin = getattr(library, "_ZN7blender20BLF_batch_draw_beginEv")
    end = getattr(library, "_ZN7blender18BLF_batch_draw_endEv")
    for call in (begin, end):
        call.argtypes = []
        call.restype = None
    baseline = os.environ.get("BEYOND_UI_MENU_BASELINE")
    info = dict(
        native_text_batch=True,
        baseline_sha256=None,
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    if baseline:
        source = Path(baseline).read_bytes()
        namespace = dict(
            __name__="beyond_ui.gpu.menu_motion_baseline", __package__="beyond_ui.gpu"
        )
        exec(compile(source, baseline, "exec"), namespace)
        menus.context_menu = namespace["context_menu"]
        info["baseline_sha256"] = hashlib.sha256(source).hexdigest()

    @contextmanager
    def batch():
        begin()
        try:
            yield
        finally:
            end()

    return batch, info
