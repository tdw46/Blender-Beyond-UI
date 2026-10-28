"""RNA numeric presentation. Stored values and context-menu targets stay native.

No registration, polling or GPU resources. Unit formatting uses a bounded cache;
parsing happens only on input and permits arithmetic and known unit tokens only.
"""

from functools import lru_cache
import math
import re
from .editing import number, display_number, drag_step

_LENGTH = {
    "KILOMETERS": "km",
    "METERS": "m",
    "CENTIMETERS": "cm",
    "MILLIMETERS": "mm",
    "MICROMETERS": "um",
    "MILES": "mi",
    "FEET": "ft",
    "INCHES": "in",
    "THOU": "thou",
}
_WORDS = set(
    "km m cm mm um micrometer micrometers kilometer kilometers meter meters centimeter centimeters millimeter millimeters mi mile miles ft foot feet in inch inches yd yard yards thou rad radians degree degrees".split()
)
_TOKEN = re.compile(
    r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z]+|[+*/(),\-°²³'\"]|\s+"
)


def checked_units(text):
    if not text.strip() or len(text) > 256:
        raise ValueError("Invalid unit expression")
    if "**" in text or "//" in text:
        raise ValueError("Only basic unit arithmetic is supported")
    depth = 0
    for char in text:
        depth += (char == "(") - (char == ")")
        if depth < 0 or depth > 12:
            raise ValueError("Invalid unit expression nesting")
    if depth:
        raise ValueError("Unbalanced unit expression")
    offset = 0
    for token in _TOKEN.finditer(text):
        value = token.group()
        if token.start() != offset or (value.isalpha() and value not in _WORDS):
            raise ValueError("Use numeric arithmetic and supported length/angle units")
        offset = token.end()
    if offset != len(text):
        raise ValueError("Unsupported unit expression")
    return text


@lru_cache(maxsize=512)
def _unit_text(system, category, value, precision, separate):
    from bpy.utils import units

    return units.to_string(
        system, category, value, precision=precision, split_unit=separate
    ).strip()


class Numeric:
    """A lightweight codec per RNA property; snapshots are immutable scene settings."""

    def __init__(self, meta, context=None):
        self.context = context
        self.integer = meta.type == "INT"
        self.unit = getattr(meta, "unit", "NONE")
        # Unit-only AREA/VOLUME metadata has no named subtype in tested RNA.
        self.subtype = (
            "NONE"
            if self.unit in {"AREA", "VOLUME"}
            else getattr(meta, "subtype", "NONE")
        )
        if self.subtype in {"ANGLE", "EULER"}:
            self.unit = "ROTATION"
        self.precision = min(6, max(0, getattr(meta, "precision", 3)))
        self.step = getattr(meta, "step", 1 if self.integer else 3)
        self.minimum, self.maximum = meta.soft_min, meta.soft_max

    def snapshot(self):
        settings = getattr(getattr(self.context, "scene", None), "unit_settings", None)
        view = getattr(getattr(self.context, "preferences", None), "view", None)
        return (
            getattr(settings, "system", "NONE"),
            getattr(settings, "scale_length", 1.0),
            getattr(settings, "system_rotation", "DEGREES"),
            getattr(settings, "length_unit", "ADAPTIVE"),
            getattr(settings, "use_separate", False),
            getattr(view, "factor_display_type", "FACTOR"),
        )

    def scale(self, state):
        if self.unit == "ROTATION":
            return 1 if state[2] == "RADIANS" else 180 / math.pi
        if self.subtype == "FACTOR" and state[5] == "PERCENTAGE":
            return 100
        if self.unit in {"LENGTH", "AREA", "VOLUME"} and state[0] != "NONE":
            return state[1] ** {"LENGTH": 1, "AREA": 2, "VOLUME": 3}[self.unit]
        return 1

    def format(self, value, state=None):
        state = state or self.snapshot()
        if self.integer:
            return str(int(value)) + ("%" if self.subtype == "PERCENTAGE" else "")
        if self.unit == "ROTATION":
            suffix = " rad" if state[2] == "RADIANS" else "°"
            return _decimal_text(value * self.scale(state), self.precision, suffix)
        if self.subtype == "PERCENTAGE" or (
            self.subtype == "FACTOR" and state[5] == "PERCENTAGE"
        ):
            return display_number(value * self.scale(state)) + "%"
        if self.unit in {"LENGTH", "AREA", "VOLUME"} and state[0] != "NONE":
            # The public formatter selects an appropriate unit; explicit preferred
            # length units are applied below without changing the bound value.
            if self.unit == "LENGTH" and state[3] in _LENGTH:
                suffix = _LENGTH[state[3]]
                factor = _unit_factor(state[0], suffix)
                return _decimal_text(
                    value * self.scale(state) / factor, self.precision, " " + suffix
                )
            return _unit_text(
                state[0], self.unit, value * self.scale(state), self.precision, state[4]
            )
        return display_number(value)

    def parse(self, text, original, state=None):
        state = state or self.snapshot()
        if text == self.format(original, state):
            return original  # Merely focusing a rounded field must be lossless.
        if self.unit == "ROTATION":
            raw = text.strip()
            if not re.search(r"[A-Za-z°'\"]", re.sub(r"\d[eE][+-]?\d+", "0", raw)):
                return number(raw) / self.scale(state)
            from bpy.utils import units

            result = units.to_value("NONE", "ROTATION", checked_units(raw))
        elif self.unit in {"LENGTH", "AREA", "VOLUME"} and state[0] != "NONE":
            from bpy.utils import units

            result = units.to_value(
                state[0],
                self.unit,
                checked_units(text),
                str_ref_unit=self.format(original, state),
            ) / self.scale(state)
        else:
            raw = (
                text.strip().removesuffix("%")
                if self.subtype in {"PERCENTAGE", "FACTOR"}
                else text
            )
            factor = (
                100
                if self.subtype == "FACTOR" and text.strip().endswith("%")
                else self.scale(state)
            )
            result = number(raw) / factor
        if not math.isfinite(result):
            raise ValueError("Non-finite number")
        return result

    def display_scale(self, state):
        scale = self.scale(state)
        if self.unit == "LENGTH" and state[0] != "NONE" and state[3] in _LENGTH:
            scale /= _unit_factor(state[0], _LENGTH[state[3]])
        return scale

    def drag(self, state, *, precision=False):
        scale = self.display_scale(state)
        # Preserve BVT's step/precision behavior; rotations drag in displayed units.
        return (
            drag_step(
                "INT" if self.integer else "FLOAT",
                self.step,
                self.minimum * scale,
                self.maximum * scale,
                precision=precision,
            )
            / scale
        )


@lru_cache(maxsize=32)
def _unit_factor(system, suffix):
    from bpy.utils import units

    return units.to_value(system, "LENGTH", "1" + suffix)


@lru_cache(maxsize=512)
def _decimal_text(value, precision, suffix):
    text = f"{value:.{precision}f}"
    if precision:
        text = text.rstrip("0").rstrip(".")
    return text + suffix
