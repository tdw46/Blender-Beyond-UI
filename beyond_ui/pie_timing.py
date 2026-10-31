"""Capability-gated Blender pie preferences, sampled once per menu invocation."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PieSettings:
    animation: float = 0.06
    tap: float = 0.20
    recenter: float = 0.0
    radius: float = 100.0
    threshold: float = 12.0
    confirm: float = 0.0
    reduce_motion: bool = False

    def __post_init__(self):
        for name in ("animation", "tap", "recenter", "radius", "threshold", "confirm"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= (
                10 if name in {"animation", "tap", "recenter"} else 1000
            ):
                raise ValueError("Invalid pie setting: " + name)

    @classmethod
    def from_context(cls, context):
        view = getattr(getattr(context, "preferences", None), "view", None)
        defaults = cls()
        fields = dict(
            animation="pie_animation_timeout",
            tap="pie_tap_timeout",
            recenter="pie_initial_timeout",
            radius="pie_menu_radius",
            threshold="pie_menu_threshold",
            confirm="pie_menu_confirm",
        )
        values = {}
        for name, prop in fields.items():
            value = getattr(view, prop, None)
            values[name] = (
                getattr(defaults, name)
                if value is None
                else float(value)
                / (100 if name in {"animation", "tap", "recenter"} else 1)
            )
        return cls(
            **values, reduce_motion=bool(getattr(view, "use_reduce_motion", False))
        )
