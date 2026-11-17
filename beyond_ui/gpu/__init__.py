"""Lazy GPU primitives. Invoke only on Blender's main thread in a draw context."""

import sys


def is_windows_vulkan():
    if sys.platform != "win32":
        return False
    import bpy
    import gpu

    return not bpy.app.background and gpu.platform.backend_type_get() == "VULKAN"
