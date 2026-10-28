"""Scoped string contexts; exact-build native admission and deterministic release."""

from contextlib import contextmanager
from functools import lru_cache


@lru_cache(maxsize=1)
def api():
    import ctypes as C, hashlib, json
    from pathlib import Path
    from .menu_native import api as admission

    if admission() is None:
        raise RuntimeError("String contexts require an admitted native adapter")
    root = Path(__file__).resolve().parents[1] / "_native"
    directory = root / "macos-arm64"
    record = json.loads((directory / "menu-context.json").read_text())
    source = root / "menu_context_macos.cpp"
    binary = (directory / record["library"]).resolve()
    if (
        binary.parent != directory.resolve()
        or hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]
        or hashlib.sha256(binary.read_bytes()).hexdigest() != record["binary_sha256"]
    ):
        raise RuntimeError("String-context adapter fingerprint mismatch")
    lib = C.PyDLL(str(binary))
    lib.beyond_context_init.restype = C.c_int
    if not lib.beyond_context_init():
        raise RuntimeError("Native string-context symbols unavailable")
    lib.beyond_context_enter.argtypes = [
        C.c_void_p,
        C.POINTER(C.c_char_p),
        C.POINTER(C.c_char_p),
        C.c_int,
    ]
    lib.beyond_context_enter.restype = C.c_void_p
    lib.beyond_context_exit.argtypes = [C.c_void_p, C.c_int]
    lib.beyond_context_exit.restype = None
    lib.beyond_context_active.restype = C.c_int
    return lib


@contextmanager
def scope(context, strings):
    if not strings:
        yield
        return
    import ctypes as C, threading

    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Blender context scopes require the main thread")
    if context.window is None or not 1 <= len(strings) <= 64:
        raise RuntimeError("String contexts require a window and at most 64 values")
    keys, values = [], []
    for key, value in strings.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, str)
            or "\0" in key + value
            or len(key) > 256
            or len(value) > 4096
        ):
            raise ValueError("Invalid bounded string context")
        keys.append(key.encode())
        values.append(value.encode())
    window = context.window.as_pointer()
    area = context.area.as_pointer() if context.area else None
    lib = api()
    handle = lib.beyond_context_enter(
        context.as_pointer(),
        (C.c_char_p * len(keys))(*keys),
        (C.c_char_p * len(values))(*values),
        len(keys),
    )
    if not handle:
        raise RuntimeError("Could not create bounded string context scope")
    try:
        yield
    finally:
        try:
            restore = (
                context.window is not None
                and context.window.as_pointer() == window
                and (context.area.as_pointer() if context.area else None) == area
            )
        except (ReferenceError, RuntimeError):
            restore = False
        lib.beyond_context_exit(handle, int(restore))


@contextmanager
def override(context, values):
    """RNA overrides stay public; string overrides use the admitted typed store."""
    strings = {k: v for k, v in values.items() if isinstance(v, str)}
    pointers = {k: v for k, v in values.items() if not isinstance(v, str)}
    with context.temp_override(**pointers), scope(context, strings):
        yield
