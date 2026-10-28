"""RNA adapters with stable element identities across automatic Blender sorting."""

from ..bindings import Binding, rna_binding
from dataclasses import replace


def color_ramp(data, property, commit):
    owner_pointer = data.as_pointer()
    ramp = getattr(data, property)
    pointer = ramp.as_pointer()
    elements = list(ramp.elements)

    def valid():
        try:
            return (
                data.as_pointer() == owner_pointer
                and getattr(data, property).as_pointer() == pointer
                and {e.as_pointer() for e in ramp.elements}
                == {e.as_pointer() for e in elements}
            )
        except (ReferenceError, AttributeError):
            return False

    def get():
        return tuple((float(e.position), tuple(e.color)) for e in elements)

    def set_value(values):
        if not valid():
            raise ReferenceError("Color ramp owner or element identities changed")
        if not 2 <= len(values) <= 32:
            raise ValueError("A color ramp requires 2 to 32 stops")
        while len(elements) > len(values):
            ramp.elements.remove(elements.pop())
        while len(elements) < len(values):
            elements.append(ramp.elements.new(0.5))
        # Track the actual elements, not their automatically re-sorted indices.
        for element, (position, color) in zip(elements, values):
            element.position = position
            element.color = color

    def context_target(hit):
        if hit.part[0] in {"stop", "position", "color", "remove"}:
            index = hit.part[1]
            element = elements[index]
            pointer = element.as_pointer()

            def resolve():
                return element if valid() and element.as_pointer() == pointer else None

            prop = "color" if hit.part[0] == "color" else "position"
            binding = rna_binding(resolve, prop, commit=commit)
            return replace(hit, binding=binding)
        return hit

    return Binding(get, set_value, valid, commit, context_target=context_target), ramp


def curve_mapping(data, property, commit, channel):
    owner_pointer = data.as_pointer()
    mapping = getattr(data, property)
    pointer = mapping.as_pointer()
    tracked = {i: list(curve.points) for i, curve in enumerate(mapping.curves)}

    def current_index():
        return min(channel[0], len(mapping.curves) - 1)

    def curve():
        return mapping.curves[current_index()]

    def valid():
        try:
            return (
                data.as_pointer() == owner_pointer
                and getattr(data, property).as_pointer() == pointer
                and len(mapping.curves) == len(tracked)
                and all(
                    {p.as_pointer() for p in c.points}
                    == {p.as_pointer() for p in tracked[i]}
                    for i, c in enumerate(mapping.curves)
                )
            )
        except (ReferenceError, AttributeError):
            return False

    def get():
        return tuple(tuple(point.location) for point in tracked[current_index()])

    def set_value(values):
        if not valid():
            raise ReferenceError("Curve owner or point identities changed")
        if len(values) < 2:
            raise ValueError("A curve requires at least two points")
        selected = curve()
        points = tracked[current_index()]
        while len(points) > len(values):
            selected.points.remove(points.pop())
        while len(points) < len(values):
            points.append(selected.points.new(0.5, 0.5))
        for point, location in zip(points, values):
            point.location = location
        mapping.update()

    def context_target(hit):
        if hit.part[0] in {"point", "point_field"}:
            channel_index, index = hit.part[1:3]
            point = tracked[channel_index][index]
            pointer = point.as_pointer()

            def resolve():
                return (
                    point
                    if valid()
                    and current_index() == channel_index
                    and point.as_pointer() == pointer
                    else None
                )

            component = hit.part[3] if hit.part[0] == "point_field" else None
            binding = rna_binding(
                resolve,
                "handle_type" if component == 2 else "location",
                index=component if component in (0, 1) else None,
                commit=commit,
            )
            binding.context.update = mapping.update
            return replace(hit, binding=binding)
        return hit

    return (
        Binding(get, set_value, valid, commit, context_target=context_target),
        mapping,
        curve,
    )


def matrix_components(data, property, resolve=None):
    """Read-only RNA is valid input; cache decomposition, never modify the matrix."""
    from math import degrees, isfinite

    resolve = resolve or (lambda: data)
    pointer = data.as_pointer()
    meta = data.bl_rna.properties[property]
    if (
        meta.type != "FLOAT"
        or meta.subtype != "MATRIX"
        or tuple(meta.array_dimensions[:2]) != (4, 4)
    ):
        raise TypeError("template_matrix requires a 4x4 FLOAT MATRIX property")
    cache = [None, None]

    def current():
        owner = resolve()
        if owner is None or owner.as_pointer() != pointer:
            raise ReferenceError("Matrix owner changed")
        return owner

    def valid():
        try:
            return property in current().bl_rna.properties
        except (ReferenceError, AttributeError, RuntimeError):
            return False

    def get():
        from mathutils import Matrix

        values = tuple(
            tuple(float(v) for v in row) for row in getattr(current(), property)
        )
        if not all(isfinite(v) for row in values for v in row):
            raise ValueError("Matrix contains non-finite values")
        if values != cache[0]:
            location, rotation, scale = Matrix(values).decompose()
            cache[:] = [
                values,
                (
                    tuple(location),
                    tuple(degrees(v) for v in rotation.to_euler("XYZ")),
                    tuple(scale),
                ),
            ]
        return cache[1]

    def reject(value):
        raise TypeError("template_matrix is read-only")

    return Binding(get, reject, valid)


def palette_source(
    data, property, commit, *, brush=None, edit=None, resolve=None, value_mode=False
):
    """Visible-only color access; full snapshots occur only during mutation/undo."""
    from .palette import PaletteSource

    resolve = resolve or (lambda: data)
    owner_pointer = data.as_pointer()
    palette = getattr(data, property)
    if palette is None:
        raise ValueError("Palette property is empty")
    pointer = palette.as_pointer()
    active_cache = [None, -1]

    def valid():
        try:
            owner = resolve()
            return (
                owner is not None
                and owner.as_pointer() == owner_pointer
                and getattr(owner, property).as_pointer() == pointer
                and getattr(palette, "is_editable", True)
            )
        except (AttributeError, ReferenceError, RuntimeError):
            return False

    def checked():
        if not valid():
            raise ReferenceError("Palette owner changed")
        return palette.colors

    def active():
        colors = checked()
        item = colors.active
        if item is None:
            return -1
        key = item.as_pointer()
        index = active_cache[1]
        if (
            active_cache[0] == key
            and 0 <= index < len(colors)
            and colors[index].as_pointer() == key
        ):
            return index
        index = next((i for i, c in enumerate(colors) if c.as_pointer() == key), -1)
        active_cache[:] = [key, index]
        return index

    def selection_state():
        return {
            "active": active(),
            "brush": (float(brush.read()) if value_mode else tuple(brush.read()))
            if brush and brush.valid()
            else None,
        }

    def snapshot():
        state = selection_state()
        state["colors"] = tuple(
            (tuple(c.color), float(c.strength), float(c.weight)) for c in checked()
        )
        return state

    def select(index):
        colors = checked()
        if not 0 <= index < len(colors):
            return
        before = selection_state()
        colors.active = colors[index]
        active_cache[:] = [colors[index].as_pointer(), index]
        if brush and brush.valid():
            brush.write(
                float(colors[index].weight)
                if value_mode
                else tuple(colors[index].color)
            )
        after = selection_state()
        if before != after:
            commit(before, after)

    def add():
        colors = checked()
        before = snapshot()
        index = active()
        color = (
            tuple(brush.read())[:3]
            if brush and brush.valid() and not value_mode
            else tuple(colors[index].color)
            if index >= 0
            else (1.0, 1.0, 1.0)
        )
        item = colors.new()
        item.color = color
        if value_mode:
            item.weight = (
                float(brush.read())
                if brush and brush.valid()
                else float(colors[index].weight)
                if index >= 0
                else 0.0
            )
        colors.active = item
        active_cache[:] = [item.as_pointer(), len(colors) - 1]
        commit(before, snapshot())

    def remove():
        colors = checked()
        index = active()
        if index < 0:
            return
        before = snapshot()
        colors.remove(colors[index])
        if colors:
            colors.active = colors[min(index, len(colors) - 1)]
        active_cache[:] = [None, -1]
        commit(before, snapshot())

    def edit_color(index):
        colors = checked()
        item = colors[index]
        key = item.as_pointer()

        def color_valid():
            try:
                return (
                    valid()
                    and index < len(colors)
                    and colors[index].as_pointer() == key
                )
            except (ReferenceError, RuntimeError):
                return False

        def color_set(value):
            item.color = value[:3]

        if edit:
            edit(Binding(lambda: tuple(item.color), color_set, color_valid, commit))

    def context_target(hit):
        if hit.part[0] != "swatch":
            return hit
        index = hit.part[1]
        item = checked()[index]
        pointer = item.as_pointer()

        def resolve_item():
            colors = checked()
            if index >= len(colors) or colors[index].as_pointer() != pointer:
                raise ReferenceError("Palette swatch owner changed")
            return colors[index]

        binding = rna_binding(
            resolve_item, "color" if not value_mode else "weight", commit=commit
        )
        return replace(hit, binding=binding)

    return PaletteSource(
        lambda: len(checked()),
        lambda i: tuple(checked()[i].color),
        active,
        select,
        valid,
        add,
        remove,
        edit_color if edit else None,
        lambda i: checked()[i].weight,
        lambda i: checked()[i].as_pointer(),
        context_target,
    )
