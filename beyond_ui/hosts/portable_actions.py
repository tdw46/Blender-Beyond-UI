"""Uniform C action ABI, shared by exact-header native packages on every OS."""

import ctypes as C
from .bridge import BridgeUnavailable


def library():
    from . import portable
    from .bridge import broker

    try:
        lib, manifest = portable.load()
    except BridgeUnavailable:
        return None
    return broker(
        lib, manifest["binary_sha256"], manifest["family"], portable=True
    ).library


def function(lib, name, result, arguments):
    fn = getattr(lib, name)
    fn.restype = result
    fn.argtypes = arguments
    return fn


def actions(lib):
    p, s, i = C.c_void_p, C.c_char_p, C.c_int
    signatures = {
        "new": ("driver_new", None, [p, s, s]),
        "available": ("driver_available", C.c_bool, []),
        "copy": ("driver_copy", C.c_bool, [p, p, s, i, C.c_short]),
        "paste": ("driver_paste", C.c_bool, [p, p, s, i, C.c_short]),
        "relations": ("relations", None, [p]),
        "favorites": ("favorites", p, [p]),
        "favorite_items": ("favorite_items", p, [p]),
        "find_property": ("find_property", p, [p, s, s, i]),
        "add_property": ("add_property", None, [p, s, s, s, i]),
        "find_favorites": ("find_favorites", p, [p, C.POINTER(C.c_uint)]),
        "remove_favorite": ("remove_favorite", None, [p, p]),
        "guess_keymap": ("guess_keymap", p, [p, s]),
        "operator_type": ("operator_type", p, [s, C.c_bool]),
        "find_operator": ("find_operator", p, [p, p, p, s, i]),
        "add_operator": ("add_operator", None, [p, s, p, p, s, i]),
    }
    result = {
        key: function(lib, "bui_" + name, restype, args)
        for key, (name, restype, args) in signatures.items()
    }

    # Keep the actual current override context for the isolated native-action
    # route used by older Windows builds. Existing callers pass a reports slot.
    def contextual(callback):
        def call(_reports, owner, path, index, flags):
            import bpy

            return callback(bpy.context.as_pointer(), owner, path, index, flags)

        return call

    result["copy"] = contextual(result["copy"])
    result["paste"] = contextual(result["paste"])
    free = function(lib, "bui_free", None, [p, i])
    result["free_array"] = lambda pointer: free(pointer, 1)
    return result


def enum_api(lib):
    p = C.c_void_p
    pointer = function(lib, "bui_rna_pointer", p, [C.py_object, p])
    items = function(
        lib,
        "bui_enum_items",
        None,
        [p, p, p, C.POINTER(p), C.POINTER(C.c_int), C.POINTER(C.c_bool)],
    )
    free = function(lib, "bui_free", None, [p, C.c_int])
    return pointer, items, lambda value: free(value, 0)


def property_api(lib):
    p = C.c_void_p

    class State(C.Structure):
        _fields_ = [("py_context", p), ("py_context_orig", p)]

    size = function(lib, "bui_py_state_size", C.c_size_t, [])
    if size() != C.sizeof(State):
        raise BridgeUnavailable("Python context-state ABI mismatch")
    pointer = function(lib, "bui_rna_pointer", p, [C.py_object, p])
    find = function(lib, "bui_rna_find", p, [p, C.c_char_p])
    function(lib, "beyond_context_property_enter", p, [p, p, C.c_char_p])
    get = function(lib, "bui_py_dict", p, [p])
    push = function(lib, "bui_py_push", None, [p, C.POINTER(State), C.py_object])
    pop = function(lib, "bui_py_pop", None, [p, C.POINTER(State)])
    return lib, pointer, find, State, get, push, pop
