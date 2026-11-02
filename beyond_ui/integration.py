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
    def __init__(self, namespace, options):
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

    def adopt(self):
        import bpy
        from .addon import AddonUI
        from .hosts.addon import Runtime

        panels = _owned_classes(bpy.types.Panel, self.owner)
        operators = _owned_classes(bpy.types.Operator, self.owner)
        menus = _owned_classes(bpy.types.Menu, self.owner)
        embedded = [
            cls
            for cls in panels
            if (cls.bl_space_type, cls.bl_region_type)
            in {("VIEW_3D", "UI"), ("PROPERTIES", "WINDOW")}
        ]
        self.report.update(
            state="registered",
            panels=[c.__name__ for c in embedded],
            other_panels=[c.__name__ for c in panels if c not in embedded],
            native_routes=_native_routes(panels + operators),
            routed_routes=[
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


def integrate(namespace, **options):
    """Call once at the end of the add-on entry module: ``integrate(globals())``.

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
    integration = Integration(namespace, options)
    integration.install()
    namespace["__beyond_ui_integration__"] = integration
    return integration
