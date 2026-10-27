"""Portable retained UI components. No Blender, renderer or product imports.

Hosts supply row dictionaries, stable identities, property adapters and paint
callbacks. Coordinates are logical pixels; no timers or global state are owned.
"""

from collections import OrderedDict

ROW_HEIGHT = 32.0
PADDING = 12.0
RADIUS = 8.0


def ancestors(node):
    """Oldest to newest, with cycle protection for host-owned navigation."""
    result, seen = [], set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        result.append(node)
        node = node.get("parent")
    return list(reversed(result))


def grouped(rows, key):
    groups = OrderedDict()
    for row in rows:
        groups.setdefault(key(row), []).append(row)
    return groups


def matches(query, *labels):
    words = query.casefold().split()
    text = " ".join(str(label) for label in labels).casefold()
    return all(word in text for word in words)


def virtual_rows(heights, offset, viewport):
    """Yield only intersecting rows without constructing controls offscreen."""
    top = -offset
    for index, height in enumerate(heights):
        if top >= viewport:
            break
        if top + height > 0:
            yield index, top, height
        top += height


def cascade_rect(anchor, size, bounds, depth=0):
    """Keep ancestor headers visible in narrow hosts; no native layout reflow."""
    left, top, available_width, available_height = bounds
    width, height = size
    inset = min(depth * 12.0, max(0.0, (available_width - 164.0) / 2.0))
    width = min(width, available_width - inset)
    y = top + 4.0 + min(depth * 34.0, max(0.0, available_height - 100.0))
    height = min(height, max(0.0, top + available_height - y - 4.0))
    x = max(
        left, min(anchor[0] + anchor[2] - width + inset, left + available_width - width)
    )
    return x, y, width, height


def uncovered(rect, covers):
    """Clip deferred text batches against every panel above their owner."""
    regions = (rect,)
    for a, b, c, d in covers:
        result = []
        for x0, y0, x1, y1 in regions:
            left, right = max(x0, a), min(x1, c)
            bottom, top = max(y0, b), min(y1, d)
            if left >= right or bottom >= top:
                result.append((x0, y0, x1, y1))
                continue
            result.extend(
                r
                for r in (
                    (x0, y0, x1, bottom),
                    (x0, top, x1, y1),
                    (x0, bottom, left, top),
                    (right, bottom, x1, top),
                )
                if r[0] < r[2] and r[1] < r[3]
            )
        regions = tuple(result)
    return regions


def toolbar_cells(count, width, minimum=112.0, gap=4.0, row_height=32.0):
    columns = max(1, int((width + gap) / (minimum + gap)))
    cell = (width - (columns - 1) * gap) / columns
    return [
        (i % columns * (cell + gap), i // columns * row_height, cell, row_height)
        for i in range(count)
    ]


def paired_controls(width, first_minimum, second_minimum, gap=4.0, row_height=32.0):
    """Keep related controls adjacent when they fit, otherwise stack intact."""
    if first_minimum + second_minimum + gap <= width:
        first = first_minimum + (width - first_minimum - second_minimum - gap) * 0.5
        return (
            (0.0, 0.0, first, row_height),
            (first + gap, 0.0, width - first - gap, row_height),
        )
    return ((0.0, 0.0, width, row_height), (0.0, row_height, width, row_height))
