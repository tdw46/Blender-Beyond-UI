"""Explicit one-line, package-scoped integration for ordinary add-on lifecycles."""

from functools import wraps
from types import CodeType


def _native_routes(classes):
    """Bounded registration-time hint, not a claim to analyze arbitrary Python."""
    names = {
        "invoke_props_dialog",
        "invoke_popup",
        "invoke_confirm",
        "invoke_props_popup",
        "popup_menu",
        "popup_menu_pie",
        "call_menu",
        "call_menu_pie",
        "call_panel",
        "invoke_search_popup",
    }
    found = []
    for cls in classes:
        for callback in ("invoke", "execute", "draw"):
            function = getattr(cls, callback, None)
            code = getattr(function, "__code__", None)
            pending, seen, hits = [code] if code else [], set(), set()
            while pending and len(seen) < 256:
                item = pending.pop()
                if item in seen:
                    continue
                seen.add(item)
                hits.update(names.intersection(item.co_names))
                pending.extend(c for c in item.co_consts if isinstance(c, CodeType))
            if hits:
                found.append(
                    {
                        "class": cls.__name__,
                        "callback": callback,
                        "routes": sorted(hits),
                    }
                )
    return found


def _owned_classes(base, owner):
    seen, found, pending = set(), [], list(base.__subclasses__())
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
        module = getattr(cls, "__module__", "")
        if (module == owner or module.startswith(owner + ".")) and getattr(
            cls, "is_registered", False
        ):
            found.append(cls)
    return sorted(found, key=lambda cls: (cls.__module__, cls.__name__))


class Integration:
    def __init__(self, namespace, options, include_panels, exclude_panels):
        self.include_panels = include_panels
        self.exclude_panels = exclude_panels
        self.namespace = namespace
        self.owner = namespace.get("__package__") or namespace["__name__"]
        self.original_register = namespace["register"]
        self.original_unregister = namespace["unregister"]
        previous = namespace.get("__beyond_ui_integration__")
        if previous is not None:
            if self.original_register is previous.register_wrapper:
                self.original_register = previous.original_register
            if self.original_unregister is previous.unregister_wrapper:
                self.original_unregister = previous.original_unregister
        self.options = options
        self.ui = None
        self.router = None
        self.list_ids = None
        self.running = False
        self.report = {
            "state": "installed",
            "panels": [],
            "other_panels": [],
            "limits": [],
        }

    def install(self):
        @wraps(self.original_register)
        def register(*args, **kwargs):
            if self.running:
                return None
            result = self.original_register(*args, **kwargs)
            try:
                self.adopt()
            except Exception:
                self.stop()
                self.original_unregister()
                raise
            self.running = True
            return result

        @wraps(self.original_unregister)
        def unregister(*args, **kwargs):
            was_running = self.running
            try:
                self.stop()
            finally:
                if was_running:
                    result = self.original_unregister(*args, **kwargs)
            return result if was_running else None

        self.namespace["register"] = register
        self.namespace["unregister"] = unregister
        self.register_wrapper, self.unregister_wrapper = register, unregister

    def selects_panel(self, cls):
        identifier = getattr(cls, "bl_idname", "") or cls.__name__
        return (self.include_panels is None or identifier in self.include_panels) and identifier not in self.exclude_panels

    def adopt(self):
        import bpy
        from .addon import AddonUI
        from .hosts.addon import Runtime

        panels = _owned_classes(bpy.types.Panel, self.owner)
        # Package-wide callback and keymap rewriting would also intercept
        # operators launched from panels intentionally left native.
        scoped = self.include_panels is not None or bool(self.exclude_panels)
        operators = [] if scoped else _owned_classes(bpy.types.Operator, self.owner)
        menus = [] if scoped else _owned_classes(bpy.types.Menu, self.owner)
        embedded = [
            cls
            for cls in panels
            if (cls.bl_space_type, cls.bl_region_type)
            in {("VIEW_3D", "UI"), ("PROPERTIES", "WINDOW")}
            and self.selects_panel(cls)
        ]
        self.report.update(
            state="registered",
            panels=[c.__name__ for c in embedded],
            other_panels=[c.__name__ for c in panels if c not in embedded],
            native_routes=_native_routes(embedded + operators),
            routed_routes=[] if scoped else [
                "invoke_props_dialog",
                "invoke_popup",
                "invoke_confirm",
                "invoke_search_popup",
                "popup_menu",
                "popup_menu_pie",
                "call_menu",
                "call_menu_pie",
                "call_panel",
            ],
            limits=[
                "Routing covers owned invoke/execute callbacks and existing owned-menu keymaps; native panel headers, redo popups, auto-keymap hints and indirect helper calls remain explicit limits.",
                "Only supported Layout calls/modes are converted; draw errors appear in status.",
                "Exact-build embedded adapters are required for custom rendering.",
            ],
        )
        self.ui = AddonUI(self.owner, **self.options)
        if "list_identity" not in self.ui.layout_options:
            from .list_identity import StableListIDs

            self.list_ids = StableListIDs(self.owner, self.refresh)
            self.ui.layout_options["list_identity"] = self.list_ids
        if operators or menus:
            from .invoke_routing import Router

            self.router = Router(self, operators)
            self.router.register()
        if embedded:
            runtime = Runtime(self.ui, embedded, adopt=True)
            self.ui._runtime = runtime
            runtime.register()

    def stop(self):
        ui, self.ui = self.ui, None
        self.running = False
        self.report["state"] = "installed"
        router, self.router = self.router, None
        if self.list_ids is not None:
            self.list_ids.close()
            self.list_ids = None
        if router is not None:
            router.close()
        if ui is not None:
            ui.unregister()

    def refresh(self):
        """Explicit invalidation for exceptional dependencies outside draw()."""
        if self.ui is not None:
            self.ui.refresh()
        if self.router is not None and self.router.keymaps is not None:
            import bpy

            self.router.keymaps.refresh(bpy.context.window_manager)

    @property
    def status(self):
        return {
            **self.report,
            "host": self.ui.status if self.ui else None,
            "list_identity": {
                "pending": len(self.list_ids.pending),
                "errors": list(self.list_ids.errors.values()),
            }
            if self.list_ids
            else None,
            "popups": {
                "dialogs": len(self.router.dialogs),
                "menus": len(self.router.menus),
                "error": self.router.error,
                "native_fallbacks": list(self.router.fallbacks),
                "preserved_macro_dependencies": getattr(
                    self.router, "macro_dependencies", []
                ),
                "keymap_routes": len(self.router.keymaps.items)
                if self.router.keymaps
                else 0,
            }
            if self.router
            else None,
        }


def _panel_ids(value):
    if isinstance(value, str):
        value = (value,)
    ids = frozenset(value)
    if not all(isinstance(identifier, str) and identifier for identifier in ids):
        raise ValueError("Panel filters require Blender panel identifiers")
    return ids


def integrate(namespace, *, include_panels=None, exclude_panels=(), **options):
    """Call once at the end of the add-on entry module: ``integrate(globals())``.

    By default all eligible panels are adopted. Use include_panels for an
    allowlist (an empty list selects none), or exclude_panels for exceptions.
    Filters use bl_idname, with the class name as Blender's default. When both
    are supplied, exclusions win. Filtered integrations leave package-wide
    operator callbacks and keymaps native.

    Wraps that module's functions; never patches bpy.utils, sys.path or other
    packages. No Blender classes/timers are registered until its register runs.
    """
    if not isinstance(namespace, dict) or not all(
        callable(namespace.get(n)) for n in ("register", "unregister")
    ):
        raise ValueError(
            "Place integrate(globals()) after register/unregister definitions"
        )
    existing = namespace.get("__beyond_ui_integration__")
    if existing is not None:
        if (
            namespace["register"] is existing.register_wrapper
            and namespace["unregister"] is existing.unregister_wrapper
        ):
            return existing
        if existing.running:
            raise RuntimeError("Unregister the add-on before reloading its integration")
    # Validate options without importing bpy or creating any registration state.
    from .addon import AddonUI

    owner = namespace.get("__package__") or namespace.get("__name__")
    AddonUI(owner, **options)
    integration = Integration(namespace, options, None if include_panels is None else _panel_ids(include_panels), _panel_ids(exclude_panels))
    integration.install()
    namespace["__beyond_ui_integration__"] = integration
    return integration
