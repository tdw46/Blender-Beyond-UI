"""Package-local invoke routing. Blender modules and WindowManager are never patched."""

from contextlib import contextmanager
from functools import wraps
from hashlib import sha256


class Forward:
    def __init__(self, raw, **values):
        object.__setattr__(self, "_raw", raw)
        self.__dict__.update(values)

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __setattr__(self, name, value):
        if name in self.__dict__:
            object.__setattr__(self, name, value)
        else:
            setattr(self._raw, name, value)


class WindowManager(Forward):
    def invoke_popup(self, operator, *, width=300, auto_keymap=False):
        from .hosts.bridge import BridgeUnavailable

        try:
            if auto_keymap:
                raise BridgeUnavailable("Automatic native keymap hints are not adapted")
            return self.router.dialog(
                operator, self.context, self.event, width=width, mode="PROPERTIES"
            )
        except Exception as error:
            self.router.note_fallback("invoke_popup", error)
            import bpy

            options = {"width": width}
            if (
                "auto_keymap"
                in bpy.types.WindowManager.bl_rna.functions["invoke_popup"].parameters
            ):
                options["auto_keymap"] = auto_keymap
            return self._raw.invoke_popup(operator, **options)

    def invoke_props_popup(self, operator, event):
        # Native redo replaces the preceding undo step. Calling execute directly
        # on each change would accumulate edits and silently break that contract.
        self.router.note_fallback(
            "invoke_props_popup", "Native undo/redo replacement is not yet adapted"
        )
        return self._raw.invoke_props_popup(operator, event)

    def invoke_search_popup(self, operator):
        from .hosts.bridge import BridgeUnavailable

        try:
            self.router.dialog(operator, self.context, self.event, mode="SEARCH")
        except Exception as error:
            self.router.note_fallback("invoke_search_popup", error)
            return self._raw.invoke_search_popup(operator)
        # Native API returns None; the caller returns RUNNING_MODAL itself.

    def invoke_confirm(self, operator, event, **options):
        from .hosts.bridge import BridgeUnavailable

        allowed = {"title", "message", "confirm_text", "icon", "text_ctxt", "translate"}
        if options.keys() - allowed:
            raise TypeError("Unknown invoke_confirm options")
        if options.get("icon", "NONE") not in {
            "NONE",
            "WARNING",
            "QUESTION",
            "ERROR",
            "INFO",
        }:
            raise ValueError("Unsupported confirmation icon")
        try:
            return self.router.dialog(
                operator, self.context, event, mode="CONFIRM", **options
            )
        except Exception as error:
            self.router.note_fallback("invoke_confirm", error)
            return self._raw.invoke_confirm(operator, event, **options)

    def popup_menu_pie(self, event, draw_func, *, title="", icon="NONE"):
        from .hosts.bridge import BridgeUnavailable

        try:
            self.router.menu(
                self.context, event, draw=draw_func, title=title, icon=icon, pie=True
            )
        except Exception as error:
            self.router.note_fallback("popup_menu_pie", error)
            return self._raw.popup_menu_pie(event, draw_func, title=title, icon=icon)

    def invoke_props_dialog(
        self,
        operator,
        *,
        width=300,
        title="",
        confirm_text="",
        cancel_default=False,
        text_ctxt="",
        translate=True,
    ):
        from .hosts.bridge import BridgeUnavailable

        options = dict(
            width=width,
            title=title,
            confirm_text=confirm_text,
            cancel_default=cancel_default,
            text_ctxt=text_ctxt,
            translate=translate,
        )
        try:
            return self.router.dialog(operator, self.context, self.event, **options)
        except Exception as error:
            self.router.note_fallback("invoke_props_dialog", error)
            # Older Blender releases expose fewer optional dialog arguments.
            import bpy

            parameters = bpy.types.WindowManager.bl_rna.functions[
                "invoke_props_dialog"
            ].parameters
            return self._raw.invoke_props_dialog(
                operator, **{k: v for k, v in options.items() if k in parameters}
            )

    def popup_menu(self, draw_func, *, title="", icon="NONE"):
        from .hosts.bridge import BridgeUnavailable

        try:
            self.router.menu(
                self.context, self.event, draw=draw_func, title=title, icon=icon
            )
        except Exception as error:
            self.router.note_fallback("popup_menu", error)
            return self._raw.popup_menu(draw_func, title=title, icon=icon)


class Router:
    def __init__(self, integration, operators):
        self.integration = integration
        self.config = integration.ui
        self.operators = tuple(sorted(operators, key=lambda cls: len(cls.__mro__)))
        self.registration_pending = set()
        self.in_place = set()
        self.patches = []
        self.originals = {}
        self.dialogs = {}
        self.menus = {}
        self.pending = None
        self.active = False
        self.error = None
        self.fallbacks = []
        self.driver = None
        self.handlers = []
        self.keymaps = None
        self.idname = (
            "bui"
            + sha256((integration.owner + ":popups").encode()).hexdigest()[:16]
            + ".popup"
        )
        from .context_dispatch import ShortcutRegistry

        self.registry = ShortcutRegistry(integration.owner + ":popups")

    def context(self, context, event):
        wm = WindowManager(
            context.window_manager, router=self, context=context, event=event
        )
        return Forward(context, window_manager=wm)

    def note_fallback(self, route, error):
        entry = {"route": route, "reason": str(error), "custom": False}
        if entry not in self.fallbacks:
            self.fallbacks[:] = [*self.fallbacks[-31:], entry]

    @contextmanager
    def scope(self, function, context, event):
        """Rebind only aliases in this callback's own globals for its synchronous call."""
        import bpy

        facade_context = self.context(context, event)
        wm = Forward(bpy.ops.wm)
        for name in ("call_menu", "call_menu_pie", "call_panel"):
            native = getattr(bpy.ops.wm, name, None)
            if native is None:
                continue

            def menu(*args, _name=name, _native=native, **kwargs):
                base = bpy.types.Panel if _name == "call_panel" else bpy.types.Menu
                cls = base.bl_rna_get_subclass_py(kwargs.get("name", ""))
                module = getattr(cls, "__module__", "")
                owner = self.integration.owner
                if cls is None or not (
                    module == owner or module.startswith(owner + ".")
                ):
                    return _native(*args, **kwargs)
                from .hosts.bridge import BridgeUnavailable

                try:
                    if _name == "call_panel":
                        if kwargs.get("keep_open", False):
                            raise BridgeUnavailable("Persistent call_panel keep_open is not adapted")
                        self.panel(context, event, name=kwargs["name"])
                    else:
                        self.menu(
                            context, event, name=kwargs["name"],
                            pie=_name == "call_menu_pie",
                        )
                except Exception as error:
                    self.note_fallback(_name, error)
                    return _native(*args, **kwargs)
                return {"FINISHED"}

            wm.__dict__[name] = menu
        ops = Forward(bpy.ops, wm=wm)
        facade = Forward(bpy, context=facade_context, ops=ops)
        namespace = getattr(function, "__globals__", {})
        module = namespace.get("__name__", "")
        owner = self.integration.owner
        if not (module == owner or module.startswith(owner + ".")):
            namespace = {}  # Inherited third-party helpers keep their own globals.
        changed = []
        for key, value in tuple(namespace.items()):
            replacement = (
                facade
                if value is bpy
                else ops
                if value is bpy.ops
                else facade_context
                if value is bpy.context
                else None
            )
            if replacement is not None:
                changed.append((key, value, replacement))
                namespace[key] = replacement
        try:
            yield facade_context
        finally:
            for key, old, replacement in changed:
                if namespace.get(key) is replacement:
                    namespace[key] = old

    def call(self, function, operator, context, event=None):
        with self.scope(function, context, event) as adapted:
            result = (
                function(operator, adapted, event)
                if event is not None
                else function(operator, adapted)
            )
        if isinstance(result, set) and "FINISHED" in result:
            refresh = getattr(self.integration, "refresh", None)
            if refresh is not None:
                refresh()
        return result

    def register(self):
        import bpy

        from .macro_safety import protected_operators

        protected, references = protected_operators(self.operators)
        self.macro_dependencies = references
        self.operators = tuple(cls for cls in self.operators if cls not in protected)
        for cls in protected:
            self.note_fallback(
                "macro-step:" + cls.bl_idname,
                "Preserved registered macro child RNA; its own popup callbacks keep native routing",
            )

        # Existing modal RNA must survive adoption/reload: unregistering it
        # destroys running instances, timers and consumer-held references.
        from .operator_lifecycle import modal_registration_policy

        self.in_place, ancestors = modal_registration_policy(self.operators)
        self.operators = tuple(cls for cls in self.operators if cls not in ancestors)
        for cls in ancestors:
            self.note_fallback(
                "modal-ancestor:" + cls.bl_idname,
                "Preserved registered modal descendant RNA; new popup callbacks require native routing",
            )

        router = self
        self.registry.register()
        self.active = True
        snapshots = [
            (
                cls,
                {
                    key: getattr(cls, key, None)
                    for key in ("invoke", "execute", "modal", "cancel")
                },
                {
                    key: cls.__dict__.get(key)
                    for key in ("invoke", "execute", "modal", "cancel")
                },
            )
            for cls in self.operators
        ]
        for cls, originals, own in snapshots:
            self.originals[cls] = originals
            replacements = {}
            for key in ("invoke", "execute"):
                original = originals[key]
                if original is None:
                    continue

                def make(function, invocation):
                    @wraps(function)
                    def invoke(op, context, event):
                        return router.call(function, op, context, event)

                    @wraps(function)
                    def execute(op, context):
                        return router.call(function, op, context)

                    return invoke if invocation else execute

                replacements[key] = make(original, key == "invoke")

            def make_modal(originals):
                def modal(op, context, event):
                    if getattr(op, "_beyond_ui_popup_cancelled", False):
                        op._beyond_ui_popup_cancelled = False
                        return {"CANCELLED"}
                    key = op.as_pointer()
                    dialog = router.dialogs.get(key)
                    if dialog is None:
                        return (
                            originals["modal"](op, context, event)
                            if originals["modal"]
                            else {"CANCELLED"}
                        )
                    try:
                        accepted = dialog.dispatch(context, event)
                        if accepted is None:
                            return {"RUNNING_MODAL"}
                        router.dialogs.pop(key, None)
                        dialog.close()
                        if accepted and originals["execute"]:
                            return router.call(originals["execute"], op, context)
                        dialog.cancel_once(originals["cancel"], context)
                        return {"CANCELLED"}
                    except Exception as error:
                        router.error = f"{type(error).__name__}: {error}"
                        router.dialogs.pop(key, None)
                        dialog.close()
                        dialog.cancel_once(originals["cancel"], context)
                        return {"CANCELLED"}

                return modal

            replacements["modal"] = make_modal(originals)

            def make_cancel(original):
                def cancel(op, context):
                    if getattr(op, "_beyond_ui_popup_cancelled", False):
                        op._beyond_ui_popup_cancelled = False
                        return
                    dialog = router.dialogs.pop(op.as_pointer(), None)
                    if dialog:
                        dialog.close()
                        dialog.cancel_once(original, context)
                    elif original:
                        original(op, context)

                return cancel

            replacements["cancel"] = make_cancel(originals["cancel"])
            self.patches.append((cls, own, replacements))

        # RNA discovers callbacks at registration. Remove descendants first:
        # re-registering a base underneath live descendants invalidates callbacks.
        # Snapshot inherited methods before patching any base to avoid wrapping
        # an already-adapted inherited method a second time.
        for cls in reversed(self.operators):
            if cls not in self.in_place:
                bpy.utils.unregister_class(cls)
                self.registration_pending.add(cls)
        for cls, own, replacements in self.patches:
            for key, value in replacements.items():
                setattr(cls, key, value)
            if cls not in self.in_place:
                bpy.utils.register_class(cls)
                self.registration_pending.discard(cls)

        def invoke(op, context, event):
            host, router.pending = router.pending, None
            if host is None and op.menu_name:
                from .hosts.bridge import BridgeUnavailable

                if not router.owns_menu(op.menu_name):
                    return {"CANCELLED"}
                try:
                    host = router.menu(
                        context, event, name=op.menu_name, pie=op.pie, start=False
                    )
                except Exception as error:
                    route = "call_menu_pie" if op.pie else "call_menu"
                    router.note_fallback("keymap:" + route, error)
                    return getattr(bpy.ops.wm, route)(
                        "INVOKE_DEFAULT", name=op.menu_name
                    )
            if host is None:
                return {"CANCELLED"}
            router.menus[op.as_pointer()] = host
            context.window_manager.modal_handler_add(op)
            return {"RUNNING_MODAL"}

        def modal(op, context, event):
            key = op.as_pointer()
            host = router.menus.get(key)
            if host is None:
                return {"CANCELLED"}
            if not router.active or not host.alive(context):
                router.menus.pop(key, None)
                host.close()
                return {"CANCELLED"}
            host.event(context, event)
            if host.canvas.context_menu is None:
                router.menus.pop(key, None)
                host.close()
                return {"FINISHED"}
            return {"RUNNING_MODAL"}

        def cancel(op, context):
            host = router.menus.pop(op.as_pointer(), None)
            if host:
                host.close()

        self.driver = type(
            self.idname.replace(".", "_OT_"),
            (bpy.types.Operator,),
            dict(
                __module__=self.integration.owner,
                bl_idname=self.idname,
                bl_label="Custom Popup",
                bl_options={"INTERNAL"},
                __annotations__={
                    "menu_name": bpy.props.StringProperty(),
                    "pie": bpy.props.BoolProperty(),
                },
                invoke=invoke,
                modal=modal,
                cancel=cancel,
            ),
        )
        bpy.utils.register_class(self.driver)
        from .invoke_keymaps import KeymapRoutes

        self.keymaps = KeymapRoutes(self)
        self.keymaps.refresh(bpy.context.window_manager)
        from bpy.app.handlers import persistent

        @persistent
        def invalidate(*args):
            router.dismiss()

        for key in ("load_pre", "undo_pre", "redo_pre"):
            collection = getattr(bpy.app.handlers, key)
            collection.append(invalidate)
            self.handlers.append((collection, invalidate))

    def host(self, context):
        from .hosts.floating import FloatingHost

        # Bound ownership: a new surface replaces this add-on's existing menus.
        if len(self.dialogs) + len(self.menus) >= 8:
            raise RuntimeError("Too many concurrent custom popups")
        return FloatingHost(
            self.integration.owner + ":popup",
            context,
            animation=self.config.animation,
            registry=self.registry,
            stylesheet=self.config.stylesheet,
        )

    def owns_menu(self, name):
        import bpy

        cls = bpy.types.Menu.bl_rna_get_subclass_py(name)
        module = getattr(cls, "__module__", "")
        return module == self.integration.owner or module.startswith(
            self.integration.owner + "."
        )

    def dialog(self, operator, context, event, **options):
        from .dialog import Dialog, SearchDialog
        import bpy

        if type(operator) not in self.operators:
            raise ValueError("Cannot adapt another add-on's operator dialog")
        if options.pop("translate", True):
            ctxt = options.pop("text_ctxt", "") or getattr(
                operator, "bl_translation_context", "*"
            )
            translate = bpy.app.translations.pgettext_iface
            for name in ("title", "confirm_text", "message"):
                if options.get(name):
                    options[name] = translate(options[name], ctxt)
        else:
            options.pop("text_ctxt", None)
        host = self.host(context)
        try:
            operator._beyond_ui_popup_cancelled = False
            mode = options.pop("mode", "DIALOG")
            dialog = (SearchDialog if mode == "SEARCH" else Dialog)(
                host,
                operator,
                context,
                event,
                context_menu=self.config.context_menu,
                **(
                    {}
                    if mode == "SEARCH"
                    else {"mode": mode, "layout_options": self.config.layout_options}
                ),
                **options,
            )
            self.dialogs[operator.as_pointer()] = dialog
            context.window_manager.modal_handler_add(operator)
            return {"RUNNING_MODAL"}
        except Exception as error:
            host.close()
            from .layout import UnsupportedControl
            from .hosts.bridge import BridgeUnavailable

            if self.config.native_fallback and isinstance(error, UnsupportedControl):
                raise BridgeUnavailable(str(error)) from error
            raise

    def menu(
        self,
        context,
        event,
        *,
        name=None,
        draw=None,
        title="",
        icon="NONE",
        pie=False,
        start=True,
    ):
        from .layout import Layout
        from .registered_menu import RegisteredMenu
        from .context_menu import Entry
        import bpy

        host = self.host(context)
        try:

            def commit(before, after):
                if self.config.commit:
                    self.config.commit(before, after)
                elif (
                    not bpy.ops.ed.undo_push.poll()
                    or "FINISHED"
                    not in bpy.ops.ed.undo_push(message="Custom Menu Property")
                ):
                    raise RuntimeError("Menu property undo is unavailable")

            ui = Layout(
                host.canvas, context, commit=commit, **self.config.layout_options
            )
            host.canvas.context_provider = self.config.context_menu
            if name:
                model = RegisteredMenu(ui, name)
            else:
                cls = type(
                    "CallbackMenu", (), {"bl_label": title, "draw": staticmethod(draw)}
                )

                class CallbackMenu(RegisteredMenu):
                    lookup = staticmethod(lambda key: cls)

                model = CallbackMenu(ui, "callback")
                if title and not pie:
                    collect = model.rows

                    def headed(context):
                        rows, valid = collect(context)
                        return (
                            Entry("popup-title", title, heading=True, icon=icon),
                            *rows,
                        ), valid

                    model.rows = headed
            if pie:
                model.pie_title = title
                model.pie_icon = icon
                original_rows = model.rows

                def rows(context):
                    result = original_rows(context)
                    model.pie = True
                    return result

                model.rows = rows
            owner = host.canvas.button("menu-owner", title, None, menu_model=model)
            x, y = host.anchor(event)
            owner.rect = (x, y, 1, 1)
            if not host.canvas.open_operator_menu(
                owner,
                host.clip,
                context,
                anchor=(x, y),
                trigger=event.type
                if event is not None and event.value == "PRESS"
                else None,
            ):
                raise RuntimeError(host.canvas.menu_error)
            if host.canvas.context_menu is None:
                for entry in getattr(host.canvas, "popup_fallbacks", ()):
                    self.note_fallback("call_menu", entry["reason"])
                host.close()
                return None
            if not start:
                return host
            self.pending = host
            namespace, key = self.idname.split(".")
            result = getattr(getattr(bpy.ops, namespace), key)("INVOKE_DEFAULT")
            if "RUNNING_MODAL" not in result:
                raise RuntimeError("Custom menu input did not start")
        except Exception:
            self.pending = None
            host.close()
            raise

    def panel(self, context, event, *, name):
        from .layout import Layout
        from .popover import RegisteredPanel
        from .hosts.bridge import BridgeUnavailable
        import bpy

        host = self.host(context)
        try:
            def commit(before, after):
                if self.config.commit:
                    self.config.commit(before, after)
                elif bpy.ops.ed.undo_push.poll():
                    bpy.ops.ed.undo_push(message="Custom Panel Property")
                else:
                    raise RuntimeError("Panel property undo is unavailable")
            layout = Layout(host.canvas, context, commit=commit, **self.config.layout_options)
            host.canvas.context_provider = self.config.context_menu
            model = RegisteredPanel(layout, name)
            owner = host.canvas.button("panel-owner", model.label, None)
            model.attach(owner)
            x, y = host.anchor(event)
            owner.rect = (x, y, 1, 1)
            if not host.canvas.open_panel(owner, host.clip, context):
                raise BridgeUnavailable(host.canvas.menu_error or "Panel could not open")
            if host.canvas.overlay is None:
                for entry in getattr(host.canvas, "popup_fallbacks", ()):
                    self.note_fallback("call_panel", entry["reason"])
                host.close()
                return None
            self.pending = host
            namespace, key = self.idname.split(".")
            if "RUNNING_MODAL" not in getattr(getattr(bpy.ops, namespace), key)("INVOKE_DEFAULT"):
                raise RuntimeError("Custom panel input did not start")
            return host
        except Exception:
            self.pending = None
            host.close()
            raise

    def dismiss(self):
        import bpy

        for key, dialog in tuple(self.dialogs.items()):
            self.dialogs.pop(key, None)
            dialog.outcome = False
            dialog.close()
            try:
                dialog.operator._beyond_ui_popup_cancelled = True
                dialog.cancel_once(
                    self.originals[type(dialog.operator)]["cancel"], bpy.context
                )
            except Exception as error:
                self.error = f"Cancellation: {error}"
        for host in tuple(self.menus.values()):
            host.close()
        self.menus.clear()

    def close(self):
        import bpy

        self.active = False
        self.dismiss()
        self.dialogs.clear()
        for collection, callback in self.handlers:
            if callback in collection:
                collection.remove(callback)
        self.handlers.clear()
        if self.keymaps is not None:
            # Blender may have regenerated effective user-keymap copies since
            # registration. Restore those owner-local routes as well.
            self.keymaps.refresh(bpy.context.window_manager)
            self.keymaps.close()
            self.keymaps = None
        if self.driver is not None and self.driver.is_registered:
            bpy.utils.unregister_class(self.driver)
        self.driver = None
        restore = [
            (
                cls,
                originals,
                replacements,
                cls.is_registered or cls in self.registration_pending,
            )
            for cls, originals, replacements in self.patches
        ]
        for cls, *_ in reversed(restore):
            if cls.is_registered and cls not in self.in_place:
                bpy.utils.unregister_class(cls)
        for cls, originals, replacements, registered in restore:
            for key in replacements:
                if cls.__dict__.get(key) is replacements[key]:
                    if originals[key] is None:
                        delattr(cls, key)
                    else:
                        setattr(cls, key, originals[key])
            if registered and cls not in self.in_place:
                bpy.utils.register_class(cls)
        self.patches.clear()
        self.registration_pending.clear()
        self.in_place.clear()
        self.originals.clear()
        self.registry.close()
