"""Blender-independent inline text/numeric editing; no eval or side effects."""

import ast
import math
import operator
import colorsys


def display_number(value):
    """Two significant digits for display only, including trailing zeroes."""
    return format(value, "#.2g").removesuffix(".")


def drag_step(kind, step, minimum, maximum, *, precision=False):
    """Normal motion is 4x the previous slow rate; Shift retains that rate."""
    span = maximum - minimum
    slow = (
        0.1
        if kind == "INT"
        else min(max(0.00001, step / 1000.0), span / 400.0)
        if 0 < span < 1e6
        else max(0.00001, step / 1000.0)
    )
    return slow if precision else slow * 4.0


def transform_range(field, angular=False):
    """Useful track extents, not hard limits; stored angles remain radians."""
    if angular:
        return (-math.pi, math.pi)
    if field in {"position", "position_2d"}:
        return (-1.0, 1.0)
    if field == "location":
        return (-5.0, 5.0)
    if field in {"scale", "scale_2d", "gradient_size", "gradient_aspect"}:
        return (0.001, 4.0)
    return None


def transform_step(field, angular=False, precision=False):
    """Unit-aware numeric scrubbing; Shift keeps quarter-rate precision."""
    extent = transform_range(field, angular)
    if extent is None:
        return None
    span = extent[1] - extent[0]
    distance = (
        240.0
        if angular
        else 100.0
        if field in {"position", "position_2d"}
        else 160.0
        if field == "location"
        else 120.0
    )
    step = (math.degrees(span) if angular else span) / distance
    return step * (0.25 if precision else 1.0)


def to_display(value):
    return (
        12.92 * value
        if value <= 0.0031308
        else 1.055 * max(0.0, value) ** (1 / 2.4) - 0.055
    )


def to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def color_hsv(rgb, linear=True, hue=0.0):
    display = tuple(to_display(v) for v in rgb[:3]) if linear else rgb[:3]
    h, s, v = colorsys.rgb_to_hsv(*display)
    return (h if s > 1e-6 else hue, s, v)


def color_rgb(hsv, linear=True):
    rgb = colorsys.hsv_to_rgb(*hsv)
    return tuple(to_linear(v) for v in rgb) if linear else rgb


def color_hex(value, linear=True):
    rgb = (to_display(v) for v in value[:3]) if linear else value[:3]
    return "#" + "".join(f"{round(max(0.0, min(1.0, v)) * 255):02X}" for v in rgb)


def parse_color_hex(text, current, linear=True):
    code = text.strip().removeprefix("#")
    if len(code) not in {3, 4, 6, 8} or any(
        c not in "0123456789abcdefABCDEF" for c in code
    ):
        raise ValueError("Invalid hex color")
    if len(code) in {3, 4}:
        code = "".join(c * 2 for c in code)
    channels = [int(code[i : i + 2], 16) / 255 for i in range(0, len(code), 2)]
    rgb = tuple(to_linear(v) for v in channels[:3]) if linear else tuple(channels[:3])
    return rgb + (
        (channels[3] if len(channels) == 4 else current[3],)
        if len(current) == 4
        else ()
    )


def number(text):
    text = text.strip().removesuffix("°").strip()
    if not text or len(text) > 256:
        raise ValueError("Invalid number")
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def visit(node, depth=0):
        if depth > 12:
            raise ValueError("Expression too deep")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand, depth + 1) * (
                -1 if isinstance(node.op, ast.USub) else 1
            )
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](
                visit(node.left, depth + 1), visit(node.right, depth + 1)
            )
        raise ValueError("Only numeric arithmetic is supported")

    try:
        value = visit(ast.parse(text, mode="eval").body)
    except (SyntaxError, ZeroDivisionError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid number") from error
    if not math.isfinite(value):
        raise ValueError("Non-finite number")
    return value


class Text:
    def __init__(self, value):
        self.text = str(value)
        self.cursor = len(self.text)
        self.anchor = 0

    def insert(self, text):
        start, end = sorted((self.cursor, self.anchor))
        text = text.replace("\n", "").replace("\r", "")[:4096]
        self.text = self.text[:start] + text + self.text[end:]
        self.cursor = self.anchor = start + len(text)

    def move(self, position, select=False):
        self.cursor = max(0, min(len(self.text), position))
        if not select:
            self.anchor = self.cursor

    def erase(self, backwards=True):
        if self.cursor == self.anchor:
            self.anchor = (
                max(0, self.cursor - 1)
                if backwards
                else min(len(self.text), self.cursor + 1)
            )
        self.insert("")
