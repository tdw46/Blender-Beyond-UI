"""Pure bounded compound-slot geometry. No paint-time layout or owner reads."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from .flow import Plan
from itertools import islice


class PieRows(tuple):
    """On-demand radial definition; preserved through owner retargeting."""


@dataclass(frozen=True)
class Compound:
    kind: str
    rows: object
    align: bool = False
    options: dict = field(default_factory=dict, compare=False)


class MenuPlan(Plan):
    """Use the ordinary retained layout algorithm with menu-specific leaf lanes."""

    def natural(self, node):
        key = id(node)
        if key in self.natural_cache:
            return self.natural_cache[key]
        if not hasattr(node, "children"):
            width = node.options["natural_width"] * self.scale(node)[0]
        else:
            widths = [self.natural(c) for c in node.children]
            gap = self.gap(node)
            width = max(widths, default=0)
            if node.kind in {"row", "split"}:
                width = sum(widths) + gap * max(0, len(widths) - 1)
                if (
                    node.kind == "row"
                    and node.options.get("alignment", "EXPAND") == "EXPAND"
                    and not any(c.options.get("spacer") for c in node.children)
                ):
                    width = max(widths, default=0) * len(widths) + gap * max(
                        0, len(widths) - 1
                    )
                factor = node.options.get("factor", 0)
                if node.kind == "split" and 0 < factor < 1 and len(widths) > 1:
                    width = max(
                        widths[0] / factor, sum(widths[1:]) / (1 - factor)
                    ) + gap * (len(widths) - 1)
            elif node.kind in {"grid", "flow"}:
                cols = node.options.get("columns", 0)
                if cols > 0:
                    cols = min(cols, len(widths))
                    width = width * cols + gap * max(0, cols - 1)
            if node.kind == "box":
                width += 2 * self.theme.padding
            fixed = self.fixed(node, 0)
            if fixed is not None:
                width = fixed
        self.natural_cache[key] = max(0, width)
        return self.natural_cache[key]


class Slots:
    def __init__(self, rows, measure, row_height=23.0):
        roots = tuple(islice(rows, 9))
        if not 1 <= len(roots) <= 8:
            raise ValueError("A pie requires one to eight slots")
        self.rows, self.sizes, self.slot_leaves = [], {}, []
        self.row_height, self.measure = row_height, measure
        self.nodes, self.plans = {}, {}
        ancestors = set()
        node_count = 0

        def collect(entry, depth=0):
            nonlocal node_count
            node_count += 1
            if depth > 16 or node_count > 4096:
                raise ValueError("Compound pie exceeds depth 16 or 4096 nodes")
            group = entry.compound
            if group is None:
                index = len(self.rows)
                self.rows.append(entry)
                if entry.spacing is not None:
                    factor, _, horizontal = entry.spacing
                    options = dict(
                        natural_width=8 * factor if horizontal else 0,
                        height=row_height if horizontal else 8 * factor,
                    )
                    if horizontal:
                        options["width"] = 8 * factor
                    self.nodes[index] = SimpleNamespace(
                        kind="separator", label="", options=options
                    )
                    return index
                if entry.decorator is not None:
                    self.nodes[index] = SimpleNamespace(
                        kind="button",
                        label="",
                        options=dict(natural_width=23, width=23, height=row_height),
                    )
                    return index
                label = measure(entry.label, 12 if entry.heading else 11)
                left = 8 if entry.heading else 27
                tail = 8 + (16 if entry.children is not None else 0)
                if entry.shortcut:
                    tail += measure(entry.shortcut, 10) + 14
                tail += 50 if entry.toggle else (16 if entry.checked else 0)
                width = label + left + tail + 4
                if entry.field is not None:
                    width = max(width, (label + left + 4) / 0.44)
                self.nodes[index] = SimpleNamespace(
                    kind="button",
                    label=entry.label,
                    options=dict(
                        natural_width=max(120, width),
                        height=row_height + (8 if entry.divider else 0),
                    ),
                )
                return index
            if (
                group.kind
                not in {"row", "column", "box", "split", "grid", "flow", "spacer"}
                or id(group) in ancestors
            ):
                raise ValueError("Invalid or cyclic compound pie layout")
            ancestors.add(id(group))
            children = tuple(collect(r, depth + 1) for r in islice(group.rows, 4097))
            ancestors.remove(id(group))
            # Include an identity so identical empty groups retain independent options.
            node = (group.kind, group.align, children, node_count)
            options = dict(group.options, align=group.align)
            if group.kind == "spacer":
                self.nodes[node] = SimpleNamespace(
                    kind="spacer",
                    label="",
                    options=dict(options, natural_width=0, height=0, spacer=True),
                )
            else:
                self.nodes[node] = SimpleNamespace(
                    kind=group.kind,
                    options=options,
                    children=[self.nodes[c] for c in children],
                )
            return node

        self.roots = tuple(collect(r) for r in roots)
        if not self.rows:
            raise ValueError("Pie has no drawable contents")
        self.rows = tuple(self.rows)
        theme = SimpleNamespace(row_height=row_height, padding=4, gap=4, font_size=11)
        for root in self.roots:
            plan = MenuPlan(theme, root=self.nodes[root])
            self.plans[root] = plan
            width = plan.natural(self.nodes[root])
            height = plan.layout(self.nodes[root], width)[0]
            self.sizes[root] = (width, height)
            for leaf in self.leaves(root):
                node = self.nodes[leaf]
                self.sizes[leaf] = (
                    plan.natural(node),
                    plan.layout(node, plan.natural(node))[0],
                )
        self.rectangles, self.boxes = {}, []

    def arrange(self, node, rect):
        x, y, w, h = rect
        self.plans[node].place(self.nodes[node], x, y, w, h)

        def retain(key):
            current = self.nodes[key]
            if isinstance(key, int):
                x, y, w, h = current.rect
                inset = min(h, 8) if self.rows[key].divider else 0
                self.rectangles[key] = (x, y + inset, w, max(0, h - inset))
            else:
                if key[0] == "box":
                    self.boxes.append(current.rect)
                for child in key[2]:
                    retain(child)

        retain(node)

    def leaves(self, node):
        if isinstance(node, int):
            return (node,)
        return tuple(i for c in node[2] for i in self.leaves(c))
