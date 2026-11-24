"""Optional accelerator for windowed, opt-in canvases on the qualified CPython ABI."""

from functools import lru_cache


@lru_cache(maxsize=1)
def native_painter():
    import sys
    if sys.platform != "win32" or sys.implementation.cache_tag != "cpython-313":
        return None

    import bpy
    if bpy.app.background or bpy.app.build_hash != b"d13f752e3b9c":
        return None

    import gpu
    if gpu.platform.backend_type_get() not in {"VULKAN", "OPENGL"}:
        return None

    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).parent
    try:
        expected = json.loads((root / "windows-panel-painter.json").read_bytes())
        for name in ("paint.py", "_win_panel.cp313-win_amd64.pyd"):
            with (root / name).open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected[name]:
                    return None
        from . import _win_panel
        from .paint import measure
    except (ImportError, OSError, KeyError, ValueError):
        return None

    # Layout and paint must use the same BLF measurement cache.
    _win_panel.measure = measure
    return _win_panel.paint
