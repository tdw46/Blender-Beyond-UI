"""Opt-in exact-build native anchor, one custom canvas per owned Panel block.

A process-lifetime broker multiplexes the native callback by token; independent
vendored copies never replace one another's callbacks. Libraries stay mapped
because Blender UI blocks can retain C++ lambdas after Python unregisters.
"""

import ctypes
import hashlib
import json
from pathlib import Path
import platform
import sys
import types


class BridgeUnavailable(RuntimeError):
    pass


def load():
    import bpy

    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise BridgeUnavailable(
            "Custom embedded canvas is not qualified on this platform; use Layout"
        )
    root = Path(__file__).resolve().parents[1] / "_native"
    directory = root / "macos-arm64"
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        build = bpy.app.build_hash.decode()
        # Admission list is code-owned; editing a manifest cannot qualify a build.
        builds = {"d0cbe84903e8": 42, "ec6e62d40fa9": 51, "d13f752e3b9c": 52}
        if build not in builds or manifest["builds"].get(build) != builds[build]:
            raise BridgeUnavailable(f"Unaudited Blender build: {build}")
        source = root / "bridge_macos.cpp"
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise BridgeUnavailable("Bridge source fingerprint mismatch")
        binary = (directory / manifest["library"]).resolve()
        if binary.parent != directory.resolve():
            raise BridgeUnavailable("Bridge binary must stay in its package")
        if hashlib.sha256(binary.read_bytes()).hexdigest() != manifest["binary_sha256"]:
            raise BridgeUnavailable("Bridge binary fingerprint mismatch")
    except (OSError, KeyError, ValueError) as error:
        raise BridgeUnavailable(
            "Build the optional bridge with tools/build_bridge.py"
        ) from error
    # Share the same ABI/source across vendors, keeping callbacks and CDLL alive.
    name = "_beyond_ui_bridge_v1_" + manifest["binary_sha256"]
    state = sys.modules.get(name)
    if state is not None:
        return state
    state = types.ModuleType(name)
    state.library = ctypes.CDLL(str(binary))
    lib = state.library
    lib.bvt_probe_initialize.argtypes = [ctypes.c_int]
    lib.bvt_probe_initialize.restype = ctypes.c_int
    lib.bvt_probe_reserve.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
    ]
    lib.bvt_probe_reserve.restype = ctypes.c_int
    lib.bvt_probe_callback.argtypes = [ctypes.c_void_p]
    lib.bvt_probe_callback.restype = None
    if lib.bvt_probe_initialize(builds[build]) != builds[build]:
        raise BridgeUnavailable("Required Blender symbols are unavailable")
    state.records = {}
    state.next_token = 1
    state.errors = []
    callback_type = ctypes.CFUNCTYPE(None, ctypes.c_uint64, *([ctypes.c_int] * 4))

    def draw(token, x0, y0, x1, y1):
        record = state.records.get(token)
        if record is None:
            return
        try:
            record(x0, y0, x1, y1)
        except Exception as error:
            state.errors.append(repr(error))
            state.errors[:] = state.errors[-16:]

    state.callback = callback_type(draw)
    lib.bvt_probe_callback(state.callback)
    sys.modules[name] = state
    return state
