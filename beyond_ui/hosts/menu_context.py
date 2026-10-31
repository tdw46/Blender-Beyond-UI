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
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        != record["python_adapter_sha256"]
        or binary.parent != directory.resolve()
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


@lru_cache(maxsize=1)
def _property_api():
    import ctypes as C

    lib = api()  # Exact build, executable, source and dylib admission first.
    runtime = C.PyDLL(None)  # Keep the GIL for Python RNA conversion.
    pointer = getattr(
        runtime, "_ZN7blender19pyrna_struct_as_ptrEP7_objectPKNS_9StructRNAE"
    )
    pointer.argtypes, pointer.restype = [C.py_object, C.c_void_p], C.c_void_p
    find = getattr(
        runtime, "_ZN7blender24RNA_struct_find_propertyEPNS_10PointerRNAEPKc"
    )
    find.argtypes, find.restype = [C.c_void_p, C.c_char_p], C.c_void_p
    lib.beyond_context_property_enter.argtypes = [C.c_void_p, C.c_void_p, C.c_char_p]
    lib.beyond_context_property_enter.restype = C.c_void_p

    class State(C.Structure):
        # Exact BKE_context.hh: two borrowed Python dictionary pointers.
        _fields_ = [("py_context", C.c_void_p), ("py_context_orig", C.c_void_p)]

    get = getattr(runtime, "_ZN7blender15CTX_py_dict_getEPKNS_8bContextE")
    get.argtypes, get.restype = [C.c_void_p], C.c_void_p
    push = getattr(
        runtime,
        "_ZN7blender17CTX_py_state_pushEPNS_8bContextEPNS_16bContext_PyStateEPv",
    )
    push.argtypes, push.restype = [C.c_void_p, C.POINTER(State), C.py_object], None
    pop = getattr(
        runtime, "_ZN7blender16CTX_py_state_popEPNS_8bContextEPNS_16bContext_PyStateE"
    )
    pop.argtypes, pop.restype = [C.c_void_p, C.POINTER(State)], None
    return lib, pointer, find, State, get, push, pop


def custom_property(context, source):
    """Reacquire genuine Property RNA for one synchronous Python callback scope.

    No property pointer is cached. Its ID property remains owned by source.owner;
    callers must revalidate the binding before each subsequent poll/execution.
    """
    import threading
    import ctypes as C

    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Property context requires Blender's main thread")
    owner = source.owner()
    lib, pointer, find, State, get, push, pop = _property_api()
    rna = pointer(owner, owner.bl_rna.as_pointer())
    name = source.name.encode()
    expected = find(rna, name) if rna else None
    if not expected:
        raise ReferenceError("Custom property disappeared")
    handle = lib.beyond_context_property_enter(context.as_pointer(), rna, name)
    if not handle:
        raise RuntimeError("Custom property context is unavailable")
    state = None
    try:
        outer = get(context.as_pointer())
        if outer:
            # Strip only the two button keys from a COPY. Do not mutate the
            # caller's override dictionary; keep it strongly alive until pop.
            values = dict(C.cast(outer, C.py_object).value)
            values.pop("button_prop", None)
            values.pop("button_pointer", None)
            state = State()
            push(context.as_pointer(), C.byref(state), values)
        prop = context.button_prop
        if prop is None or prop.as_pointer() != expected:
            raise ReferenceError(
                "An outer property context shadowed the clicked property"
            )
        return prop
    finally:
        if state is not None:
            pop(context.as_pointer(), C.byref(state))
        lib.beyond_context_exit(handle, 1)
