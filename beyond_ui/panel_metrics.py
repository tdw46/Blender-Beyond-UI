"""Responsive panel presentation; inferred structure, never product label matching.

Applied by PanelHost during retained layout, not during paint. Authored controls,
RNA owners and order remain intact. Menu and list-child layout is independent.
"""

# Logical CSS-like design tokens. Font size remains unchanged.
FIELD_HEIGHT = 26.0
BUTTON_HEIGHT = 20.0
ICON_BUTTON_SIZE = 24.0
LIST_TOOL_SIZE = 22.0
ICON_SIZE = 14.0
LABEL_BAND = 26.0
GAP = 4.0


def auto_slider(control):
    """Conservative metadata-only default; explicit True/False always wins."""
    from math import isfinite

    if control.kind != "number" or not control.options.get("slider_auto"):
        return False
    numeric = control.options.get("numeric")
    if numeric is None or numeric.integer or numeric.unit != "NONE":
        return False
    low, high = (
        control.options.get("hard_min", -float("inf")),
        control.options.get("hard_max", float("inf")),
    )
    span = high - low
    return all(isfinite(v) for v in (low, high)) and low > 0 and 10 <= span <= 1000


def prepare(canvas):
    from .widgets.collection_list import CollectionList

    def visit(group):
        children = getattr(group, "children", ())
        if group.kind == "row" and any(
            c.kind == "widget" and isinstance(c.options.get("widget"), CollectionList)
            for c in children
        ):
            for c in children:
                if hasattr(c, "children") and c.kind == "column":
                    c.options["_list_tools"] = True
        for child in children:
            if hasattr(child, "children"):
                visit(child)
            else:
                child.options["_panel_metrics"] = True
                child.options["_list_tool"] = bool(group.options.get("_list_tools"))
                child.options.pop("_slider_stacked", None)
                child.options.pop("_label_span", None)
                if child.options.get("slider_auto"):
                    child.options["slider"] = bool(
                        getattr(canvas, "automatic_sliders", True)
                        and auto_slider(child)
                    )
                if child.kind == "number" and child.options.get("slider"):
                    child.options["_slider_stacked"] = bool(child.label)
                    child.options["_label_band"] = LABEL_BAND
        if group.kind not in {"box", "column"}:
            return
        for i, child in enumerate(children[:-1]):
            if (
                child.kind != "label"
                or not child.label
                or child.options.get("section_heading") is False
            ):
                continue
            if child.options.get("icon") not in {
                None,
                "",
                "NONE",
                0,
            } or child.options.get("icon_value"):
                continue
            first = group.kind == "box" and i == 0
            divided = i > 0 and children[i - 1].kind == "separator"
            following = children[i + 1]
            if (first or divided) and following.kind not in {"label", "separator"}:
                child.options["text_role"] = "title"

    visit(canvas)


def span_labels(group):
    """Grid-like spanning captions, only across otherwise empty label bands."""
    children = getattr(group, "children", ())
    leaves = []
    for child in children:
        leaves.extend(span_labels(child) if hasattr(child, "children") else (child,))
    if group.kind in {"row", "split"}:
        labels = [c for c in leaves if c.options.get("_slider_stacked")]
        if len(labels) == 1:
            label = labels[0]
            x, y, w, h = label.rect
            band = min(20, label.options["_label_band"])
            if all(c is label or c.rect[1] >= y + band for c in leaves):
                label.options["_label_span"] = group.rect[0] + group.rect[2] - x
    return leaves
