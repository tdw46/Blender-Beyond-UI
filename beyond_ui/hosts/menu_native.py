"""Lazy, exact-build adapters for Blender's driver clipboard and Quick Favorites.

Derived from BVT _shoost_driver_clipboard.py and audited Blender source (see
menu-native-audit.json). No active native button, product imports or registration.
Unknown platforms/builds/source/binaries fail closed. Never called from paint.
"""

import ctypes as C
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform

_REASON = "Native menu adapter has not been admitted"


@lru_cache(maxsize=1)
def api():
    import bpy

    global _REASON
    try:
        if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
            raise RuntimeError("Native menu adapter is unqualified on this platform")
        build = bpy.app.build_hash.decode()
        if build not in {"ec6e62d40fa9", "d13f752e3b9c"}:
            raise RuntimeError(
                "Native menu adapter is unqualified for this Blender build"
            )
        manifest = json.loads(
            Path(__file__).with_name("menu-native-audit.json").read_text()
        )
        if (
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            != manifest["adapter_sha256"]
        ):
            raise RuntimeError("Native menu adapter source fingerprint mismatch")
        with open(bpy.app.binary_path, "rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != manifest["builds"][build]["executable_sha256"]:
            raise RuntimeError("Native menu adapter executable fingerprint mismatch")
        lib = C.CDLL(None)
        ptr, string = C.c_void_p, C.c_char_p
        signatures = {
            "new": (
                "_ZN7blender19ANIM_copy_as_driverEPNS_2IDEPKcS3_",
                None,
                [ptr, string, string],
            ),
            "available": ("_ZN7blender21ANIM_driver_can_pasteEv", C.c_bool, []),
            "relations": (
                "_ZN7blender24DEG_relations_tag_updateEPNS_4MainE",
                None,
                [ptr],
            ),
            "copy": (
                "_ZN7blender16ANIM_copy_driverEPNS_10ReportListEPNS_2IDEPKcis",
                C.c_bool,
                [ptr, ptr, string, C.c_int, C.c_short],
            ),
            "paste": (
                "_ZN7blender17ANIM_paste_driverEPNS_10ReportListEPNS_2IDEPKcis",
                C.c_bool,
                [ptr, ptr, string, C.c_int, C.c_short],
            ),
            "favorites": (
                "_ZN7blender26ED_screen_user_menu_ensureEPNS_8bContextE",
                ptr,
                [ptr],
            ),
            "find_property": (
                "_ZN7blender34ED_screen_user_menu_item_find_propEPNS_9ListBaseTINS_13bUserMenuItemEEEPKcS5_i",
                ptr,
                [ptr, string, string, C.c_int],
            ),
            "add_property": (
                "_ZN7blender33ED_screen_user_menu_item_add_propEPNS_9ListBaseTINS_13bUserMenuItemEEEPKcS5_S5_i",
                None,
                [ptr, string, string, string, C.c_int],
            ),
        }
        signatures.update(
            {
                "guess_keymap": (
                    "_ZN7blender22WM_keymap_guess_opnameEPKNS_8bContextEPKc",
                    ptr,
                    [ptr, string],
                ),
                "operator_type": (
                    "_ZN7blender20WM_operatortype_findEPKcb",
                    ptr,
                    [string, C.c_bool],
                ),
                "find_operator": (
                    "_ZN7blender38ED_screen_user_menu_item_find_operatorEPNS_9ListBaseTINS_13bUserMenuItemEEEPKNS_14wmOperatorTypeEPNS_10IDPropertyEPKcNS_2wm13OpCallContextE",
                    ptr,
                    [ptr, ptr, ptr, string, C.c_int8],
                ),
                "add_operator": (
                    "_ZN7blender37ED_screen_user_menu_item_add_operatorEPNS_9ListBaseTINS_13bUserMenuItemEEEPKcPKNS_14wmOperatorTypeEPKNS_10IDPropertyES5_NS_2wm13OpCallContextE",
                    None,
                    [ptr, string, ptr, ptr, string, C.c_int8],
                ),
            }
        )
        signatures.update(
            {
                "find_favorites": (
                    "_ZN7blender25ED_screen_user_menus_findEPKNS_8bContextEPj",
                    ptr,
                    [ptr, C.POINTER(C.c_uint)],
                ),
                "remove_favorite": (
                    "_ZN7blender31ED_screen_user_menu_item_removeEPNS_9ListBaseTINS_13bUserMenuItemEEEPS1_",
                    None,
                    [ptr, ptr],
                ),
            }
        )
        functions = {}
        for key, (symbol, restype, arguments) in signatures.items():
            fn = getattr(lib, symbol)
            fn.restype, fn.argtypes = restype, arguments
            functions[key] = fn
        # MEM_delete on the returned trivial pointer array uses NonTrivial=1.
        # Read the active allocator dispatcher at deletion time (guarded/lockfree).
        free_slot = C.c_void_p.in_dll(lib, "_ZN11mem_guarded8internal12mem_freeN_exE")

        def free_array(pointer):
            C.CFUNCTYPE(None, ptr, C.c_int)(free_slot.value)(pointer, 1)

        functions["free_array"] = free_array
        _REASON = ""
        return functions
    except (OSError, ValueError, KeyError, AttributeError, RuntimeError) as error:
        _REASON = str(error)
        return None


def reason():
    api()
    return _REASON


def curve(source):
    owner = source.owner()
    animation = owner.id_data.animation_data
    return (
        animation.drivers.find(owner.path_from_id(source.name), index=source.index or 0)
        if animation
        else None
    )


def driver_enabled(kind, source, target):
    import bpy

    owner = source.owner()
    meta = owner.bl_rna.properties[source.name]
    if meta.type not in {"BOOLEAN", "INT", "FLOAT", "ENUM"}:
        return False
    if getattr(meta, "is_array", False) and source.index is None:
        return False  # Whole arrays have no unambiguous driver clipboard slot.
    if owner.id_data is None or not callable(
        getattr(owner.id_data, "path_resolve", None)
    ):
        return False
    functions = api()
    if functions is None:
        return False
    if kind == "COPY_DRIVER":
        return curve(source) is not None
    if kind == "NATIVE_DRIVER":
        return True  # Read-only/non-animatable values can be driver inputs.
    return (
        kind == "PASTE_DRIVER"
        and source.editable()
        and target.editable()
        and target.commit is not None
        and meta.is_animatable
        and "from_existing" in bpy.types.AnimDataDrivers.bl_rna.functions
        and functions["available"]()
    )


def driver_apply(kind, source, target):
    import bpy

    if not driver_enabled(kind, source, target):
        raise RuntimeError("Driver clipboard action is unavailable")
    owner = source.owner()
    identity = owner.id_data
    path = owner.path_from_id(source.name)
    identity.path_resolve(path)
    index = source.index or 0
    functions = api()
    if kind == "NATIVE_DRIVER":
        full_path = path + (f"[{source.index}]" if source.index is not None else "")
        functions["new"](
            identity.as_pointer(), full_path.encode(), source.name.encode()
        )
        return
    if kind == "COPY_DRIVER":
        if not functions["copy"](None, identity.as_pointer(), path.encode(), index, 0):
            raise RuntimeError("Blender could not copy this driver")
        return
    staging = bpy.data.objects.new("Beyond UI driver clipboard staging", None)
    replacement = None
    had_animation = identity.animation_data is not None
    previous = curve(source)
    backup = None
    removed_previous = False
    try:
        if not functions["paste"](None, staging.as_pointer(), b"location", 0, 0):
            raise RuntimeError("Blender could not paste this driver")
        drivers = identity.animation_data_create().drivers
        replacement = drivers.from_existing(
            src_driver=staging.animation_data.drivers[0]
        )
        replacement.data_path, replacement.array_index = path, index
        if previous is not None:
            backup = staging.animation_data.drivers.from_existing(src_driver=previous)
            drivers.remove(previous)
            removed_previous = True
        target.commit(kind)
    except Exception:
        if replacement is not None:
            identity.animation_data.drivers.remove(replacement)
        if removed_previous:
            restored = identity.animation_data.drivers.from_existing(src_driver=backup)
            restored.data_path, restored.array_index = path, index
        if not had_animation:
            identity.animation_data_clear()
        raise
    finally:
        bpy.data.objects.remove(staging)
        functions["relations"](bpy.data.as_pointer())
        identity.update_tag()


def _favorite_menus(context):
    functions = api()
    if functions is None or context.area is None:
        return ()
    size = C.c_uint()
    pointer = functions["find_favorites"](context.as_pointer(), C.byref(size))
    if not pointer:
        return ()
    try:
        if size.value > 3:
            raise RuntimeError("Unexpected Favorites context count")
        values = C.cast(pointer, C.POINTER(C.c_void_p))
        return tuple(dict.fromkeys(values[i] for i in range(size.value) if values[i]))
    finally:
        functions["free_array"](pointer)


def property_favorite(source, context, *, remove=False):
    from ..context_paths import owner_path

    path = owner_path(source, context)
    if path is None or api() is None:
        return False
    args = (
        path.encode(),
        source.name.encode(),
        -1 if source.index is None else source.index,
    )
    found = False
    for menu in _favorite_menus(context):
        item = api()["find_property"](menu + 88, *args)
        if item:
            found = True
            if remove:
                api()["remove_favorite"](menu + 88, item)
    if remove and found:
        context.preferences.is_dirty = True
    return found


def add_property_favorite(source, context):
    from ..context_paths import owner_path

    path = owner_path(source, context)
    functions = api()
    if functions is None or path is None or context.area is None:
        raise RuntimeError("Quick Favorites is unavailable for this owner/context")
    owner = source.owner()
    # Exact DNA_userdef_types.h in both admitted builds: two pointers, char,
    # seven pad bytes, context[64], then ListBase items at byte 88. No other
    # layout is read, and the pointer is borrowed only for this explicit action.
    menu = functions["favorites"](context.as_pointer())
    if not menu:
        raise RuntimeError("Blender could not resolve this Quick Favorites menu")
    items = menu + 88
    index = -1 if source.index is None else source.index
    args = (items, path.encode(), source.name.encode(), index)
    if not functions["find_property"](*args):
        functions["add_property"](
            items, owner.bl_rna.properties[source.name].name.encode(), *args[1:]
        )
        context.preferences.is_dirty = True
    if not functions["find_property"](*args):
        raise RuntimeError("Blender did not retain the Quick Favorite")


def operator_identifier(idname):
    namespace, name = idname.split(".", 1)
    return namespace.upper() + "_OT_" + name


def keymap(context, idname):
    functions = api()
    if functions is None or context.area is None:
        return None
    pointer = functions["guess_keymap"](
        context.as_pointer(), operator_identifier(idname).encode()
    )
    config = context.window_manager.keyconfigs.user
    return (
        next((km for km in config.keymaps if km.as_pointer() == pointer), None)
        if config
        else None
    )


INVOCATIONS = (
    "INVOKE_DEFAULT",
    "INVOKE_REGION_WIN",
    "INVOKE_REGION_CHANNELS",
    "INVOKE_REGION_PREVIEW",
    "INVOKE_AREA",
    "INVOKE_SCREEN",
    "EXEC_DEFAULT",
    "EXEC_REGION_WIN",
    "EXEC_REGION_CHANNELS",
    "EXEC_REGION_PREVIEW",
    "EXEC_AREA",
    "EXEC_SCREEN",
)


def operator_favorite(idname, properties, invocation, context, *, operation="ADD"):
    from ..context_extensions import operator
    from uuid import uuid4

    functions = api()
    if functions is None or context.area is None or invocation not in INVOCATIONS:
        raise RuntimeError("Quick Favorites operator adapter is unavailable")
    op = operator(idname)
    info = op.get_rna_type()
    op_type = functions["operator_type"](operator_identifier(idname).encode(), True)
    if not op_type:
        raise ReferenceError("Operator was unregistered")
    if operation not in {"ADD", "REMOVE", "QUERY"}:
        raise ValueError(operation)
    # A short-lived public RNA key configuration owns the typed IDProperty group.
    # Native add_operator copies it; no pointer survives its removal. This only
    # runs after an explicit click, never when polling/opening/painting a menu.
    configs = context.window_manager.keyconfigs
    temporary = configs.new("Beyond UI favorite " + uuid4().hex)
    try:
        km = temporary.keymaps.new("Window")
        item = km.keymap_items.new(idname, "NONE", "PRESS")
        for key, value in properties.items():
            setattr(item.properties, key, value)
        prop_pointer = item.properties.as_pointer() if properties else None
        matches = []
        for existing in _favorite_menus(context):
            match = functions["find_operator"](
                existing + 88, op_type, prop_pointer, b"", INVOCATIONS.index(invocation)
            )
            if match:
                matches.append((existing + 88, match))
        if operation == "QUERY":
            return bool(matches)
        if operation == "REMOVE":
            for items, match in matches:
                functions["remove_favorite"](items, match)
            if matches:
                context.preferences.is_dirty = True
            return bool(matches)
        if matches:
            return True
        menu = functions["favorites"](context.as_pointer())
        if not menu:
            raise RuntimeError("Blender could not resolve Quick Favorites")
        args = (menu + 88, op_type, prop_pointer, b"", INVOCATIONS.index(invocation))
        if not functions["find_operator"](*args):
            functions["add_operator"](args[0], info.name.encode(), *args[1:])
            context.preferences.is_dirty = True
        if not functions["find_operator"](*args):
            raise RuntimeError("Blender did not retain the operator favorite")
    finally:
        configs.remove(temporary)


def add_operator_favorite(idname, properties, invocation, context):
    return operator_favorite(idname, properties, invocation, context)


@lru_cache(maxsize=1)
def _enum_api():
    if api() is None:
        return None
    # Enum callbacks can execute Python. PyDLL keeps the GIL held throughout.
    lib = C.PyDLL(None)
    pointer = getattr(lib, "_ZN7blender19pyrna_struct_as_ptrEP7_objectPKNS_9StructRNAE")
    pointer.argtypes, pointer.restype = [C.py_object, C.c_void_p], C.c_void_p
    items = getattr(
        lib,
        "_ZN7blender23RNA_property_enum_itemsEPNS_8bContextEPNS_10PointerRNAEPNS_11PropertyRNAEPPKNS_16EnumPropertyItemEPiPb",
    )
    items.argtypes = [
        C.c_void_p,
        C.c_void_p,
        C.c_void_p,
        C.POINTER(C.c_void_p),
        C.POINTER(C.c_int),
        C.POINTER(C.c_bool),
    ]
    items.restype = None
    free = C.c_void_p.in_dll(lib, "_ZN11mem_guarded8internal12mem_freeN_exE")
    return pointer, items, free


def enum_items(owner, name, context, *, include_separators=False):
    """Copy dynamic RNA items and immediately release Blender-owned temporary data."""
    from types import SimpleNamespace

    functions = _enum_api()
    if functions is None:
        return None

    class Item(C.Structure):
        _fields_ = [
            ("value", C.c_int),
            ("identifier", C.c_char_p),
            ("icon", C.c_int),
            ("name", C.c_char_p),
            ("description", C.c_char_p),
        ]

    pointer, evaluate, free = functions
    raw, count, owned = C.c_void_p(), C.c_int(), C.c_bool()
    rna = pointer(owner, owner.bl_rna.as_pointer())
    if not rna:
        raise ReferenceError("Enum owner disappeared")
    try:
        evaluate(
            context.as_pointer(),
            rna,
            owner.bl_rna.properties[name].as_pointer(),
            C.byref(raw),
            C.byref(count),
            C.byref(owned),
        )
        if not 0 <= count.value <= 4096:
            raise ValueError("Enum exceeds the bounded item limit")
        rows = C.cast(raw, C.POINTER(Item))
        decode = lambda value: value.decode("utf8", "replace") if value else ""
        return tuple(
            SimpleNamespace(
                identifier=decode(rows[i].identifier),
                name=decode(rows[i].name),
                description=decode(rows[i].description),
                icon=rows[i].icon,
                value=rows[i].value,
            )
            for i in range(count.value)
            if rows[i].identifier or include_separators
        )
    finally:
        if owned.value and raw.value:
            # RNA_enum_item_add uses raw MEM_reallocN; its allocation is Trivial.
            C.CFUNCTYPE(None, C.c_void_p, C.c_int)(free.value)(raw, 0)
