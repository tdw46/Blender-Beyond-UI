"""Retained logical layout plans. No bindings, GPU resources or RNA are read here.

Grid packing and height-balanced column flow follow Blender's interface_layout.cc;
custom control dimensions and source spacing remain in host logical units.
"""

from math import ceil


def weighted_width(widths):
    total = sum(widths)
    return sum(w * w for w in widths) / total if total else 0.0


def grid_shape(count, width, average, columns=0, row_major=False):
    if not count:
        return 0, 0
    cols = (
        columns
        if columns > 0
        else min(count, max(1, int(width / average) if average else 1))
    )
    rows = ceil(count / cols)
    modulo = -columns if columns < -1 else 0
    step = modulo or 1
    if row_major:
        if modulo and cols > modulo:
            cols -= cols % modulo
        rows = ceil(count / cols)
        cols -= ((cols - ceil(count / rows)) // step) * step
    else:
        if modulo and rows % modulo:
            rows = min(count, rows + modulo - rows % modulo)
        cols = ceil(count / rows)
        rows -= ((rows - ceil(count / cols)) // step) * step
    return cols, rows


class Plan:
    """One invalidation's measurement cache, discarded after geometry is retained."""

    def __init__(self, theme, measure=None):
        self.theme = theme
        self.measure = measure
        self.natural_cache = {}
        self.plans = {}

    def gap(self, node):
        return 0.0 if node.options.get("align") else self.theme.gap

    def natural(self, node):
        key = id(node)
        if key in self.natural_cache:
            return self.natural_cache[key]
        if not hasattr(node, "children"):
            if "width" in node.options:
                width = node.options["width"]
            elif node.options.get("spacer"):
                width = 0.0
            elif node.kind == "widget":
                width = node.options["widget"].dimensions(self.theme.font_size, 1e6)[0]
            else:
                text = (
                    self.measure(node.label, node.options.get("text_role", "body"))
                    if self.measure
                    else len(node.label)
                    * self.theme.font_size
                    * (12 / 11 if node.options.get("text_role") == "title" else 1)
                    * 0.58
                )
                minimum = {
                    "number": 280 if node.options.get("slider", True) else 130,
                    "toggle": 130,
                    "text": 160,
                    "enum": 160,
                    "pointer": 160,
                    "search": 160,
                    "color": 130,
                    "event": 160,
                    "image": 160,
                }.get(node.kind, 24)
                width = max(minimum, text + (70 if node.kind == "toggle" else 24))
        else:
            sizes = [self.natural(c) for c in node.children]
            width = (
                sum(sizes) + max(0, len(sizes) - 1) * self.gap(node)
                if node.kind in {"row", "split"}
                else max(sizes, default=0.0)
            )
            if node.kind == "box":
                width += 2 * self.theme.padding
        self.natural_cache[key] = max(0.0, width)
        return self.natural_cache[key]

    def control_size(self, node, available):
        available = max(0.0, min(available, node.options.get("width", available)))
        if node.kind == "widget":
            return node.options["widget"].dimensions(
                self.theme.font_size, available, node.options.get("height")
            )
        extra = (
            20
            if node.kind == "number"
            and node.label
            and node.options.get("slider", True)
            and available < 260
            else 0
        )
        height = node.options.get(
            "height", 8 if node.kind == "separator" else self.theme.row_height + extra
        )
        return available, max(0.0, height)

    def row_widths(self, node, width):
        children, gap = node.children, self.gap(node)
        usable = max(0.0, width - max(0, len(children) - 1) * gap)
        if node.kind == "split":
            factor = node.options.get("factor", 0) or 1 / max(1, len(children))
            return [usable * factor] + [
                usable * (1 - factor) / max(1, len(children) - 1)
            ] * (len(children) - 1)
        spacers = [bool(c.options.get("spacer")) for c in children]
        if any(spacers):
            widths = [
                0 if spacer else self.natural(c) for c, spacer in zip(children, spacers)
            ]
            total = sum(widths)
            shrink = min(1, usable / total) if total else 1
            free = max(0, usable - total) / sum(spacers)
            return [
                free if spacer else w * shrink for w, spacer in zip(widths, spacers)
            ]
        if node.options.get("alignment", "EXPAND") != "EXPAND":
            widths = [self.natural(c) for c in children]
            total = sum(widths)
            shrink = min(1, usable / total) if total else 1
            return [w * shrink for w in widths]
        fixed = [
            c.options.get("width") if not hasattr(c, "children") else None
            for c in children
        ]
        total = sum(w for w in fixed if w is not None)
        shrink = min(1, usable / total) if total else 1
        flex = max(0, usable - total) / max(1, fixed.count(None))
        return [w * shrink if w is not None else flex for w in fixed]

    def layout(self, node, width):
        key = (id(node), width)
        if key in self.plans:
            return self.plans[key]
        if not hasattr(node, "children"):
            return self.control_size(node, width)[1], ()
        padding = self.theme.padding if node.kind == "box" else 0
        available = max(0.0, width - 2 * padding)
        gap, children = self.gap(node), node.children
        cells = []
        alignment = node.options.get("alignment", "EXPAND")
        shift = {"CENTER": 0.5, "RIGHT": 1.0}.get(alignment, 0.0)
        if node.kind in {"row", "split"}:
            widths = self.row_widths(node, available)
            x = (
                max(0, available - sum(widths) - max(0, len(children) - 1) * gap)
                * shift
            )
            for child, w in zip(children, widths):
                h = self.layout(child, w)[0]
                cells.append((child, x, 0, w, h))
                x += w + gap
        elif node.kind == "grid" and children:
            natural = [self.natural(c) for c in children]
            cols, rows = grid_shape(
                len(children),
                available,
                weighted_width(natural),
                node.options["columns"],
                node.options["row_major"],
            )
            indices = [
                (i % cols, i // cols)
                if node.options["row_major"]
                else (i // rows, i % rows)
                for i in range(len(children))
            ]
            buckets = [[] for _ in range(cols)]
            for (col, row), w in zip(indices, natural):
                buckets[col].append(w)
            weights = [
                1.0 if node.options["even_columns"] else weighted_width(values)
                for values in buckets
            ]
            total = sum(weights)
            usable = max(0, available - (cols - 1) * gap)
            widths = [usable * (w / total if total else 1 / cols) for w in weights]
            heights = [0.0] * rows
            for child, (col, row) in zip(children, indices):
                heights[row] = max(heights[row], self.layout(child, widths[col])[0])
            if node.options["even_rows"]:
                heights = [max(heights)] * rows
            xs, ys = [0.0], [0.0]
            for w in widths[:-1]:
                xs.append(xs[-1] + w + gap)
            for h in heights[:-1]:
                ys.append(ys[-1] + h + gap)
            for child, (col, row) in zip(children, indices):
                cells.append((child, xs[col], ys[row], widths[col], heights[row]))
        elif node.kind == "flow" and children:
            natural = max(self.natural(c) for c in children)
            cols = node.options["columns"] or min(
                len(children), max(1, int(available / natural) if natural else 1)
            )
            w = max(0, available - (cols - 1) * gap) / cols
            heights = [self.layout(c, w)[0] for c in children]
            target = sum(heights) / cols
            col, y, used = 0, 0.0, 0.0
            for child, h in zip(children, heights):
                cells.append((child, col * (w + gap), y, w, h))
                used += h
                y += h + gap
                if col < cols - 1 and used >= target:
                    col, y, used = col + 1, 0.0, 0.0
        else:
            y = 0.0
            for child in children:
                w = (
                    available
                    if alignment == "EXPAND"
                    else min(available, self.natural(child))
                )
                h = self.layout(child, w)[0]
                cells.append((child, (available - w) * shift, y, w, h))
                y += h + gap
        result = (
            max((y + h for _, x, y, w, h in cells), default=0) + 2 * padding,
            cells,
        )
        self.plans[key] = result
        return result

    def place(self, node, x, y, width):
        if not hasattr(node, "children"):
            w, h = self.control_size(node, width)
            node.rect = (x, y, w, h)
            return
        height, cells = self.layout(node, width)
        node.rect = (x, y, width, height)
        padding = self.theme.padding if node.kind == "box" else 0
        for child, a, b, w, h in cells:
            self.place(child, x + padding + a, y + padding + b, w)
