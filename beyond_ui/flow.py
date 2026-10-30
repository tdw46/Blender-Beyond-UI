"""Retained logical layout plans. No bindings, GPU resources or RNA are read here.

Grid packing and height-balanced column flow follow Blender's interface_layout.cc;
custom control dimensions and source spacing remain in host logical units.
"""

from math import ceil, isfinite


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

    def __init__(self, theme, measure=None, root=None):
        self.theme = theme
        self.measure = measure
        self.natural_cache = {}
        self.plans = {}
        self.slot_ratios = {}
        self.sized = root is not None
        self.scales = {}
        self.ancestors = {}
        if root is not None:
            self.prepare(root)
        else:
            self.place = self.place_plain
            self.control_size = self.control_size_plain

    def prepare(self, node, sx=1.0, sy=1.0):
        self.ancestors[id(node)] = (sx, sy)
        if hasattr(node, "children"):
            sx *= node.options.get("scale_x", 0) or 1.0
            sy *= node.options.get("scale_y", 0) or 1.0
        if not all(isfinite(v) and 0 < v <= 4096 for v in (sx, sy)):
            raise ValueError("Combined layout scale must be positive and at most 4096")
        self.scales[id(node)] = (sx, sy)
        for child in getattr(node, "children", ()):
            self.prepare(child, sx, sy)

    def scale(self, node):
        return self.scales.get(id(node), (1.0, 1.0))

    def fixed(self, node, axis):
        if not hasattr(node, "children"):
            if axis == 0 and "width" in node.options:
                return node.options["width"] * self.scale(node)[0]
            return None
        if not node.children:
            return None
        units = node.options.get("ui_units_x" if axis == 0 else "ui_units_y", 0)
        if units:
            # A source logical unit is one ordinary row, not an artboard pixel.
            return (
                units
                * self.theme.row_height
                * self.ancestors.get(id(node), (1, 1))[axis]
            )
        return None

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
        if self.sized:
            if not hasattr(node, "children"):
                width *= self.scale(node)[0]
            fixed = self.fixed(node, 0)
            if fixed is not None:
                width = fixed
        self.natural_cache[key] = max(0.0, width)
        return self.natural_cache[key]

    def control_size_plain(self, node, available):
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

    def control_size(self, node, available):
        sx, sy = self.scale(node) if self.sized else (1.0, 1.0)
        fixed = node.options.get("width")
        available = max(
            0.0, min(available, fixed * sx if fixed is not None else available)
        )
        if node.kind == "widget":
            w, h = node.options["widget"].dimensions(
                self.theme.font_size, available, node.options.get("height")
            )
            return min(available, w * sx), h * sy
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
        return available, max(0.0, height * sy)

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
        fixed = (
            [self.fixed(c, 0) for c in children]
            if self.sized
            else [
                c.options.get("width") if not hasattr(c, "children") else None
                for c in children
            ]
        )
        total = sum(w for w in fixed if w is not None)
        shrink = min(1, usable / total) if total else 1
        if not self.sized:
            flex = max(0, usable - total) / max(1, fixed.count(None))
            return [w * shrink if w is not None else flex for w in fixed]
        weights = [
            self.scale(c)[0] if w is None else 0 for c, w in zip(children, fixed)
        ]
        flex = max(0, usable - total) / max(1e-30, sum(weights))
        return [
            w * shrink if w is not None else flex * weight
            for w, weight in zip(fixed, weights)
        ]

    def layout(self, node, width):
        fixed_width = self.fixed(node, 0) if self.sized else None
        if fixed_width is not None:
            width = min(width, fixed_width)
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
        height = max((y + h for _, x, y, w, h in cells), default=0) + 2 * padding
        fixed_height = self.fixed(node, 1) if self.sized else None
        slot_ratio = 1.0
        if fixed_height is not None and cells:
            # Fit the explicit slot without changing typography or logical ownership.
            # Compound controls re-fit uniformly during placement.
            inset = min(padding, fixed_height / 2)
            ratio = max(0, fixed_height - 2 * inset) / max(1e-30, height - 2 * padding)
            slot_ratio = ratio
            cells = [(c, x, y * ratio, w, h * ratio) for c, x, y, w, h in cells]
            height = fixed_height
        result = (height, cells)
        if slot_ratio != 1.0:
            self.slot_ratios[key] = slot_ratio
        self.plans[key] = result
        return result

    def place_plain(self, node, x, y, width):
        """Keep ordinary layouts on the small unconstrained placement path."""
        if not hasattr(node, "children"):
            w, h = self.control_size(node, width)
            node.rect = (x, y, w, h)
            return
        height, cells = self.layout(node, width)
        node.rect = (x, y, width, height)
        padding = self.theme.padding if node.kind == "box" else 0
        for child, a, b, w, h in cells:
            self.place(child, x + padding + a, y + padding + b, w)

    def place(self, node, x, y, width, allocated_height=None):
        fixed_width = self.fixed(node, 0) if self.sized else None
        if fixed_width is not None:
            width = min(width, fixed_width)
        if not hasattr(node, "children"):
            w, h = self.control_size(node, width)
            if node.kind == "widget" and (
                allocated_height is not None or self.scale(node) != (1.0, 1.0)
            ):
                w, h = node.options["widget"].dimensions(
                    self.theme.font_size,
                    w,
                    h if allocated_height is None else allocated_height,
                )
            elif allocated_height is not None:
                h = allocated_height
            node.rect = (x, y, w, h)
            return
        height, cells = self.layout(node, width)
        ratio = (
            allocated_height / height
            if allocated_height is not None and height
            else 1.0
        )
        node.rect = (x, y, width, height * ratio)
        padding = min(self.theme.padding, height / 2) if node.kind == "box" else 0
        child_scale = ratio * self.slot_ratios.get((id(node), width), 1.0)
        for child, a, b, w, h in cells:
            allocated = (
                self.layout(child, w)[0] * child_scale if child_scale != 1.0 else None
            )
            self.place(child, x + padding + a, y + (padding + b) * ratio, w, allocated)
