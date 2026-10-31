"""Owned panel/input lifecycle behind AddonUI; only loaded on explicit register."""

import hashlib
import inspect
from ..canvas import Canvas
from ..layout import Layout
from ..context_dispatch import ShortcutRegistry
from .panel import PanelHost


class PanelProxy:
    def __init__(self, definition, layout, instance=None):
        self._definition, self.layout = definition, layout
        self._instance = instance

    def __getattr__(self, name):
        try:
            value = inspect.getattr_static(self._definition, name)
        except AttributeError:
            if self._instance is not None:
                return getattr(self._instance, name)
            raise
        # RNA descriptors need a real Blender instance; Python helper methods
        # need the proxy so nested self.layout calls are still recorded.
        if not inspect.isfunction(value) and not isinstance(
            value, (classmethod, staticmethod, property)
        ):
            if self._instance is not None:
                return getattr(self._instance, name)
        return (
            value.__get__(self, self._definition)
            if hasattr(value, "__get__")
            else value
        )


class Runtime:
    def __init__(self, config, definitions, *, adopt=False):
        self.config, self.definitions = config, tuple(definitions)
        self.adopt = adopt
        self.draw_functions = {d: d.draw for d in self.definitions}
        self.draw_patches = []
        self.layout_states = {}
        self.errors = {}
        self.fallbacks = {}
        self.hosts, self.canvases, self.classes = {}, {}, []
        self.running = set()
        self.active = False
        self.generation = 0
        self.registry = ShortcutRegistry(config.owner)
        self.start_callback = self.start
        self.refresh_callback = self.refresh
        self.handlers = []
        self.input_id = (
            "bui" + hashlib.sha256(config.owner.encode()).hexdigest()[:16] + ".input"
        )

    def register(self):
        import bpy

        if not self.definitions or len(set(self.definitions)) != len(self.definitions):
            raise ValueError("Supply unique Panel definitions")
        for cls in self.definitions:
            if not issubclass(cls, bpy.types.Panel):
                raise TypeError("Panel definitions must subclass bpy.types.Panel")
            if getattr(cls, "is_registered", False) and not self.adopt:
                raise ValueError(
                    "Do not register custom panels with bpy before AddonUI"
                )
            if (cls.bl_space_type, cls.bl_region_type) not in {
                ("VIEW_3D", "UI"),
                ("PROPERTIES", "WINDOW"),
            }:
                raise ValueError(
                    "Embedded panels support VIEW_3D/UI and PROPERTIES/WINDOW"
                )
        self.registry.register()
        runtime = self

        def invoke(operator, context, event):
            key = context.window.as_pointer()
            if not runtime.active or key in runtime.running:
                return {"CANCELLED"}
            if not any(h.bridge for h in runtime.hosts.values()):
                return {"CANCELLED"}
            operator.generation = runtime.generation
            operator.window_key = key
            runtime.running.add(key)
            context.window_manager.modal_handler_add(operator)
            return {"RUNNING_MODAL"}

        def modal(operator, context, event):
            if not runtime.active or operator.generation != runtime.generation:
                if operator.generation == runtime.generation:
                    runtime.running.discard(operator.window_key)
                return {"CANCELLED"}
            return (
                {"RUNNING_MODAL"}
                if any(h.event(context, event) for h in runtime.hosts.values())
                else {"PASS_THROUGH"}
            )

        def cancel(operator, context):
            if getattr(operator, "generation", None) == runtime.generation:
                runtime.running.discard(getattr(operator, "window_key", None))

        op = type(
            self.input_id.replace(".", "_OT_"),
            (bpy.types.Operator,),
            {
                "__module__": self.config.owner,
                "bl_idname": self.input_id,
                "bl_label": "Enable Panel Input",
                "bl_options": {"INTERNAL"},
                "invoke": invoke,
                "modal": modal,
                "cancel": cancel,
                "poll": classmethod(lambda cls, ctx: ctx.window is not None),
            },
        )
        bpy.utils.register_class(op)
        self.classes.append(op)
        for definition in self.definitions:
            host = PanelHost(
                self.config.owner + ":" + definition.__name__,
                animation=self.config.animation,
            )
            self.hosts[definition] = host
            self.canvases[definition] = {}

            def make_draw(definition):
                def draw(panel, context):
                    if not runtime.active or isinstance(panel.layout, Layout):
                        return runtime.draw_functions[definition](panel, context)
                    return runtime.draw(
                        definition, panel.layout, context, instance=panel
                    )

                return draw

            if self.adopt:
                own = definition.__dict__.get("draw")
                wrapped = make_draw(definition)
                self.draw_patches.append((definition, own, wrapped))
                definition.draw = wrapped
            else:
                generated = type(
                    definition.__name__,
                    (definition,),
                    {
                        "__module__": definition.__module__,
                        "draw": make_draw(definition),
                    },
                )
                bpy.utils.register_class(generated)
                self.classes.append(generated)
        self.active = True
        from bpy.app.handlers import persistent

        @persistent
        def before(*args):
            runtime.refresh()

        @persistent
        def before_load(*args):
            runtime.generation += 1
            runtime.running.clear()
            runtime.refresh()

        @persistent
        def after_load(*args):
            runtime.running.clear()
            runtime.schedule_start()

        for name, callback in (
            ("undo_pre", before),
            ("redo_pre", before),
            ("load_pre", before_load),
            ("load_post", after_load),
        ):
            collection = getattr(bpy.app.handlers, name)
            collection.append(callback)
            self.handlers.append((collection, callback))
        self.schedule_start()

    def schedule_start(self):
        import bpy

        if (
            self.active
            and not bpy.app.background
            and not bpy.app.timers.is_registered(self.start_callback)
        ):
            bpy.app.timers.register(self.start_callback, first_interval=0.0)

    def start(self):
        import bpy

        if not self.active:
            return None
        for host in self.hosts.values():
            host.start()
        if any(h.bridge for h in self.hosts.values()):
            namespace, name = self.input_id.split(".")
            op = getattr(getattr(bpy.ops, namespace), name)
            for window in bpy.context.window_manager.windows:
                if window.as_pointer() not in self.running:
                    with bpy.context.temp_override(window=window):
                        op("INVOKE_DEFAULT")
        self.redraw()
        return None

    def draw(self, definition, native, context, *, instance=None):
        host = self.hosts[definition]
        if host.bridge is None:
            native.label(text="Beyond UI: " + host.reason, icon="INFO")
            if self.adopt and instance is not None:
                self.draw_functions[definition](instance, context)
            return
        if context.window.as_pointer() not in self.running:
            native.operator(self.input_id, text="Enable Panel Input")
        key = host._key(context)
        # Active context changes revoke all captured RNA rather than guessing names.
        fingerprint = tuple(
            getattr(context, n).as_pointer()
            if getattr(context, n, None) is not None
            else 0
            for n in ("scene", "view_layer", "object")
        )
        cache_key = getattr(definition, "cache_key", None)
        fingerprint += (cache_key(context) if cache_key else None,)
        cache = self.canvases[definition]
        if key not in cache and len(cache) >= 64:
            # Window/region churn cannot retain an unbounded set of RNA/GPU owners.
            host.invalidate()
            for _, old_canvas in cache.values():
                old_canvas.park()
            cache.clear()
            self.layout_states = {
                k: v for k, v in self.layout_states.items() if k[0] is not definition
            }
        cached = cache.get(key)
        state = self.layout_states.setdefault((definition, key), {})
        tape = None
        if self.adopt:
            from ..layout_recording import Tape

            tape = Tape(state)
            try:
                self.draw_functions[definition](
                    PanelProxy(definition, tape.root, instance), context
                )
            except Exception as error:
                self.draw_error(definition, key, native, error, context, instance)
                return
            fingerprint += (tuple(tape.signature),)
        if cached is None or cached[0] != fingerprint:
            if cached is not None:
                cached[1].park()
            canvas = Canvas(shortcut_registry=self.registry)
            if self.config.context_menu is not None:
                canvas.context_provider = self.config.context_menu

            def commit(before, after):
                if self.config.commit:
                    self.config.commit(before, after)
                else:
                    import bpy

                    if (
                        not bpy.ops.ed.undo_push.poll()
                        or "FINISHED"
                        not in bpy.ops.ed.undo_push(message=definition.bl_label)
                    ):
                        raise RuntimeError(
                            "Undo is unavailable; provide a consumer commit callback"
                        )
                self.redraw()

            layout = Layout(
                canvas=canvas,
                context=context,
                commit=commit,
                state=state,
                **self.config.layout_options,
            )
            try:
                if tape is not None:
                    tape.play(layout)
                else:
                    self.draw_functions[definition](
                        PanelProxy(definition, layout), context
                    )
            except Exception as error:
                canvas.park()
                if not self.adopt:
                    raise
                self.draw_error(definition, key, native, error, context, instance)
                return
            self.canvases[definition][key] = fingerprint, canvas
        else:
            canvas = cached[1]
        self.errors.pop(definition.__name__, None)
        self.fallbacks.pop(definition.__name__, None)
        if not host.draw(native, context, canvas):
            native.label(text="Custom panel unavailable: " + host.reason, icon="INFO")

    def draw_error(self, definition, key, native, error, context=None, instance=None):
        self.errors[definition.__name__] = f"{type(error).__name__}: {error}"
        # Never leave a previous canvas interactive beneath an error message.
        self.hosts[definition].invalidate()
        cached = self.canvases[definition].pop(key, None)
        if cached is not None:
            cached[1].park()
        from ..layout import UnsupportedControl
        from ..list_identity import PendingListIdentity

        if isinstance(error, PendingListIdentity):
            self.errors.pop(definition.__name__, None)
            native.label(text="Preparing custom list…", icon="INFO")
            return
        if (
            self.config.native_fallback
            and isinstance(error, UnsupportedControl)
            and instance is not None
        ):
            self.errors.pop(definition.__name__, None)
            self.fallbacks[definition.__name__] = {
                "reason": error.control,
                "custom": False,
            }
            native.label(text="Beyond UI: native compatibility", icon="INFO")
            self.draw_functions[definition](instance, context)
            return
        native.label(text="Beyond UI unsupported: " + str(error), icon="ERROR")

    def redraw(self):
        import bpy

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in {"VIEW_3D", "PROPERTIES"}:
                    area.tag_redraw()

    def refresh(self):
        for host in self.hosts.values():
            host.invalidate()
        for cache in self.canvases.values():
            for _, canvas in cache.values():
                canvas.park()
            cache.clear()
        self.layout_states.clear()
        self.errors.clear()
        self.fallbacks.clear()
        self.registry.commands.clear()
        self.redraw()
        return None

    def schedule_refresh(self):
        import bpy

        if self.active and not bpy.app.timers.is_registered(self.refresh_callback):
            bpy.app.timers.register(self.refresh_callback, first_interval=0.0)

    def close(self):
        import bpy

        self.active = False
        for callback in (self.start_callback, self.refresh_callback):
            if bpy.app.timers.is_registered(callback):
                bpy.app.timers.unregister(callback)
        for collection, callback in self.handlers:
            if callback in collection:
                collection.remove(callback)
        self.handlers.clear()
        for host in self.hosts.values():
            host.close()
        self.hosts.clear()
        self.layout_states.clear()
        for definition, original, wrapped in self.draw_patches:
            if definition.__dict__.get("draw") is wrapped:
                if original is None:
                    delattr(definition, "draw")
                else:
                    definition.draw = original
        self.draw_patches.clear()
        self.canvases.clear()
        self.running.clear()
        for cls in reversed(self.classes):
            if cls.is_registered:
                bpy.utils.unregister_class(cls)
        self.classes.clear()
        self.registry.close()

    def status(self):
        return {
            "registered": self.active,
            "draw_errors": dict(self.errors),
            "native_fallbacks": dict(self.fallbacks),
            "panels": {
                d.__name__: {
                    "available": h.bridge is not None,
                    "reason": h.reason,
                    "menus": h.menu_adapter_reason,
                    "property_contributions": h.menu_context_reason,
                }
                for d, h in self.hosts.items()
            },
        }
