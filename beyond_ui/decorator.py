"""Public-RNA animation decorators, scoped to the active Action and driver channels."""

from bisect import bisect_left
from .context_menu import Target


def channel_collections(data):
    animation = getattr(data, "animation_data", None)
    if animation is None:
        return (), None
    action = animation.action
    collections = []
    if action is not None:
        if hasattr(action, "layers") and getattr(action, "is_action_layered", False):
            slot = getattr(animation, "action_slot", None)
            if slot is not None:
                for layer in action.layers:
                    for strip in layer.strips:
                        get_bag = getattr(strip, "channelbag", None)
                        bag = get_bag(slot, ensure=False) if get_bag else None
                        if bag is not None:
                            collections.append(bag.fcurves)
        elif hasattr(action, "fcurves"):  # Blender 4.2 legacy Actions.
            collections.append(action.fcurves)
    return tuple(collections), animation.drivers


class Decorator:
    def __init__(self, binding, context):
        self.binding, self.source, self.context = binding, binding.context, context
        self.curves = self.drivers = ()
        self.collections = ()
        self.signature = None
        self.refresh()

    def stamp(self):
        owner = self.source.owner()
        anim = getattr(owner.id_data, "animation_data", None)
        action = anim.action if anim else None
        slot = getattr(anim, "action_slot", None)
        try:
            counts = tuple(len(c) for c in self.collections)
        except (ReferenceError, RuntimeError):
            counts = (-1,)
        return (
            action.as_pointer() if action else 0,
            slot.as_pointer() if slot else 0,
            len(anim.drivers) if anim else 0,
            counts,
        )

    def refresh(self):
        owner = self.source.owner()
        self.collections, drivers = channel_collections(owner.id_data)
        path = owner.path_from_id(self.source.name)
        match = lambda f: f.data_path == path and (
            self.source.index is None or f.array_index == self.source.index
        )
        self.curves = tuple(
            f for collection in self.collections for f in collection if match(f)
        )
        self.drivers = tuple(f for f in drivers or () if match(f))
        self.signature = self.stamp()

    def state(self):
        try:
            if self.stamp() != self.signature:
                self.refresh()
            if self.drivers:
                return "DRIVEN"
            if not self.curves:
                return "EMPTY"
            frame = self.context.scene.frame_current_final
            keyed = False
            for curve in self.curves:
                points = curve.keyframe_points
                # Binary lookup reads existing RNA; never copy or scan key arrays in paint.
                index = bisect_left(points, frame - 1e-4, key=lambda p: p.co[0])
                if index < len(points) and abs(points[index].co[0] - frame) < 1e-4:
                    keyed = True
                    value = self.binding.read()
                    if self.source.index is None and isinstance(value, tuple):
                        value = value[curve.array_index]
                    if (
                        isinstance(value, (int, float))
                        and abs(value - curve.evaluate(frame)) > 1e-5
                    ):
                        return "CHANGED"
            return "KEYED" if keyed else "ANIMATED"
        except (ReferenceError, RuntimeError, AttributeError):
            return "UNAVAILABLE"

    def editable(self, canvas):
        try:
            meta = self.source.owner().bl_rna.properties[self.source.name]
            return (
                canvas.menu_commit is not None
                and self.binding.valid()
                and self.source.editable()
                and meta.is_animatable
            )
        except (ReferenceError, RuntimeError):
            return False

    def click(self, canvas, control, context):
        if not self.editable(canvas):
            return
        self.refresh()  # Resolve exact current channels again before an action.
        state = self.state()
        if state in {"DRIVEN", "UNAVAILABLE"}:
            return
        self.source.execute(
            "DELETE_KEY" if state in {"KEYED", "CHANGED"} else "KEY",
            Target(control.key, binding=self.binding, commit=canvas.menu_commit),
            context,
        )
        self.refresh()
