"""Owned panel/input lifecycle behind AddonUI; only loaded on explicit register."""

import hashlib
import inspect
import time
from ..canvas import Canvas
from ..layout import Layout
from ..context_dispatch import ShortcutRegistry
from .panel import PanelHost
from ..scroll import NativeScrollGesture, SCROLL_EVENTS, panel_scroll_region


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
        self.input_errors = {}
        self.fallbacks = {}
        self.hosts, self.canvases, self.classes = {}, {}, []
        self.running = set()
        self.active = False
        self.generation = 0
        self.registry = ShortcutRegistry(config.owner)
        self.start_callback = self.start
        self.refresh_callback = self.refresh
        self.handlers = []
        self.native_scroll = NativeScrollGesture()
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
            context.window_manager.modal_handler_add(operator)
            runtime.running.add(key)
            return {"RUNNING_MODAL"}

        def modal(operator, context, event):
            if not runtime.active or operator.generation != runtime.generation:
                if operator.generation == runtime.generation:
                    runtime.running.discard(operator.window_key)
                return {"CANCELLED"}
            return runtime.dispatch_event(operator, context, event)

        def cancel(operator, context):
            if getattr(operator, "generation", None) == runtime.generation:
                runtime.running.discard(getattr(operator, "window_key", None))
                runtime.native_scroll.clear(getattr(operator, "window_key", None))

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
            runtime.native_scroll.clear()
            runtime.refresh()

        @persistent
        def before_load(*args):
            runtime.native_scroll.clear()
            runtime.generation += 1
            runtime.running.clear()
            runtime.reset_file_hosts()

        @persistent
        def after_load(*args):
            runtime.running.clear()
            runtime.schedule_start()

        for name, callback in (
            ("undo_pre", before),
            ("redo_pre", before),
            ("load_pre", before_load),
            ("load_post", after_load),
            ("load_post_fail", after_load),
        ):
            collection = getattr(bpy.app.handlers, name, None)
            if collection is None:
                continue
            collection.append(callback)
            self.handlers.append((collection, callback))
        self.schedule_start()

    def dispatch_event(self, operator, context, event):
        """An owned action failure must never terminate the window input service."""
        scroll_key = None
        window = getattr(context, "window", None)
        if event.type in SCROLL_EVENTS:
            scroll_key = panel_scroll_region(context, event)
            if scroll_key is not None:
                scroll_time = time.monotonic()
                if self.native_scroll.continuing(scroll_key, scroll_time):
                    return {"PASS_THROUGH"}
            elif window is not None:
                self.native_scroll.clear(window.as_pointer())
        elif window is not None and (
            event.type == "WINDOW_DEACTIVATE"
            or (getattr(event, "value", None) == "PRESS"
                and event.type not in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE", "TIMER"})
        ):
            # Explicit actions can open a popup/start an edit immediately.
            self.native_scroll.clear(window.as_pointer())
        for definition, host in self.hosts.items():
            try:
                if host.event(context, event):
                    return {"RUNNING_MODAL"}
            except Exception as error:
                # Blender raises RuntimeError for an operator's ERROR report,
                # including expected refusals. Keep diagnostics bounded by panel
                # and consume this event: replaying it could invoke another action.
                import traceback

                self.input_errors[definition.__name__] = {
                    "event": event.type,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
                traceback.print_exc()
                try:
                    host.invalidate()
                except Exception as cleanup_error:
                    self.input_errors[definition.__name__]["cleanup_error"] = str(cleanup_error)
                    # Even stale RNA during cancellation must not retain a hit target.
                    host.records.clear()
                self.canvases[definition].clear()
                try:
                    operator.report({"WARNING"}, "Beyond UI: " + str(error))
                    self.redraw()
                except Exception:
                    pass  # Reporting cannot take down the input service either.
                return {"RUNNING_MODAL"}
        if scroll_key is not None:
            self.native_scroll.remember(scroll_key, scroll_time)
        return {"PASS_THROUGH"}

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
        # Reserve known native space without author callbacks or binding reads.
        # Context replacement still revokes old owners immediately. Paint detects
        # re-entry and requests one authoring pass before exposing controls again.
        if (cached is not None and cached[0][:3] == fingerprint
                and host.defer_draw(native, context, cached[1])):
            return
        cache_key = getattr(definition, "cache_key", None)
        fingerprint += (cache_key(context) if cache_key else None,)
        interaction_context = (context.mode, context.space_data.as_pointer())
        if self.adopt and cached is not None and cached[0][:4] == fingerprint:
            canvas = cached[1]
            # A native redraw can change conditional accessories while a scalar
            # is being dragged. Replacing its canvas would cancel the transaction
            # (restoring the old value) and briefly change View2D's reserved
            # height. Keep this exact owner and geometry through mouse release;
            # values remain live, and the next draw authors the new structure.
            if (getattr(canvas, "_author_context", None) == interaction_context
                    and canvas.edit is not None and canvas.editor is None
                    and canvas.active is not None and canvas.active.kind == "number"
                    and not canvas.edit.closed and canvas.edit.binding.valid()):
                canvas._author_revision = None
                canvas.visible = True
                if not host.draw(native, context, canvas):
                    native.label(text="Custom panel unavailable: " + host.reason, icon="INFO")
                return
        state = self.layout_states.setdefault((definition, key), {})
        tape = None
        author_revision = None
        reuse_author = False
        if self.adopt:
            from ..layout_recording import Tape, freeze

            try:
                revision_key = getattr(definition, "beyond_ui_draw_cache_key", None)
                if revision_key is not None:
                    # Explicit consumer contract: all authored branches/text and
                    # captured owners must be represented. Bound values and live
                    # lists still refresh below; backdrop changes do not author.
                    author_revision = (
                        freeze(revision_key(context)), freeze(state),
                        context.space_data.as_pointer(), context.mode,
                        context.region.width, context.preferences.system.ui_scale,
                        context.preferences.view.language,
                        context.preferences.view.use_translate_interface,
                        context.preferences.view.use_translate_tooltips,
                    )
                    reuse_author = (
                        cached is not None and cached[0][:-1] == fingerprint
                        and getattr(cached[1], "_author_revision", None) == author_revision
                        and getattr(cached[1], "_author_tape", None) is not None
                    )
                if reuse_author:
                    tape = cached[1]._author_tape
                else:
                    tape = Tape(state)
                    self.draw_functions[definition](
                        PanelProxy(definition, tape.root, instance), context
                    )
            except Exception as error:
                self.draw_error(definition, key, native, error, context, instance)
                return
            fingerprint += (tuple(tape.signature),)
        if (not reuse_author and cached is not None and tape is not None and cached[0][:-1] == fingerprint[:-1]
                and getattr(cached[1], "_author_tape", None) is not None
                and cached[1]._author_tape.patch_display(tape)):
            self.canvases[definition][key] = fingerprint, cached[1]
            cached = self.canvases[definition][key]
        if cached is None or cached[0] != fingerprint:
            if cached is not None:
                cached[1].park()
            canvas = Canvas(shortcut_registry=self.registry)
            if self.config.stylesheet is not None:
                self.config.stylesheet.apply(
                    canvas, variant=getattr(definition, "beyond_ui_style", "")
                )
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

            layout_options = dict(self.config.layout_options)
            layout_options["property_options"] = {
                **layout_options.get("property_options", {}),
                **getattr(definition, "beyond_ui_props", {}),
            }
            layout = Layout(
                canvas=canvas,
                context=context,
                commit=commit,
                state=state,
                **layout_options,
            )
            try:
                if tape is not None:
                    tape.play(layout)
                    canvas._author_tape = tape
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
        # Clipped panels are parked after paint. Native draw is authoring them
        # again (including their reserved height), so resume before list callbacks
        # validate their parent. Otherwise an ordinary value refresh turns an
        # offscreen list into an error row and View2D clamps the scroll upward.
        # The host still gates input on its painted/clipped record and parks
        # unpainted canvases again; this does not schedule idle redraws.
        canvas.visible = True
        try:
            for control in canvas.controls.values():
                widget = control.options.get("widget")
                if hasattr(widget, "refresh_display"):
                    widget.refresh_display()
        except Exception as error:
            self.draw_error(definition, key, native, error, context, instance)
            return
        self.errors.pop(definition.__name__, None)
        self.fallbacks.pop(definition.__name__, None)
        if not host.draw(native, context, canvas):
            native.label(text="Custom panel unavailable: " + host.reason, icon="INFO")
        # List/disclosure defaults can be initialized by construction/arrange.
        # Acknowledge that completed state, not its pre-construction snapshot.
        canvas._author_revision = (
            (author_revision[0], freeze(state), *author_revision[2:])
            if author_revision is not None else None
        )
        canvas._author_context = interaction_context

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

    def reset_file_hosts(self):
        """Release file/context-scoped drawing resources before replacing Main.

        Clearing canvases alone leaves BLF glyph/GPU state and draw handlers
        alive across file loading. Integer font IDs can still measure correctly
        while rendering no glyphs. Recreate hosts once through schedule_start,
        outside painting; ordinary undo/value refreshes retain their resources.
        """
        self.refresh()
        for definition, host in tuple(self.hosts.items()):
            host.close()
            self.hosts[definition] = PanelHost(
                host.owner,
                backdrop_revision=host.backdrop_revision,
                animation=host.animation,
                glass_enabled=host.glass_enabled,
                panel_layout=host.panel_layout,
            )

    def schedule_refresh(self):
        import bpy

        if self.active and not bpy.app.timers.is_registered(self.refresh_callback):
            bpy.app.timers.register(self.refresh_callback, first_interval=0.0)

    def close(self):
        import bpy

        self.active = False
        self.native_scroll.clear()
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
            "input_errors": dict(self.input_errors),
            "native_fallbacks": dict(self.fallbacks),
            "popup_fallbacks": [entry for cache in self.canvases.values()
                                for _, canvas in cache.values()
                                for entry in getattr(canvas, "popup_fallbacks", ())][-32:],
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
