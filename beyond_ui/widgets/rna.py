"""RNA adapters with stable element identities across automatic Blender sorting."""

from ..bindings import Binding


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

    return Binding(get, set_value, valid, commit), ramp


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

    return Binding(get, set_value, valid, commit), mapping, curve
