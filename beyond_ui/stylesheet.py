"""Composable, JSON-friendly style presets; no Blender or GPU work on import."""

from copy import deepcopy
from dataclasses import replace
from math import isfinite
from types import MappingProxyType
from weakref import WeakSet, WeakKeyDictionary
from .animation import AnimationSettings

_GEOMETRY = {
    "row_height": (16, 64),
    "gap": (0, 24),
    "padding": (0, 40),
    "radius": (0, 32),
    "font_size": (8, 24),
    "icon_size": (10, 24),
    "field_height": (18, 64),
    "button_height": (18, 64),
    "button_padding_x": (0, 32),
    "button_padding_y": (0, 24),
    "icon_button_size": (18, 48),
    "list_tool_size": (18, 48),
    "label_band": (16, 48),
    "list_row_height": (28, 88),
    "heading_height": (16, 48),
    "box_padding": (0, 40),
    "separator_height": (1, 24),
}
_COLORS = {
    "accent",
    "bg",
    "card",
    "bar",
    "field",
    "input",
    "text",
    "title",
    "muted",
    "selected_text",
    "selected",
    "hover",
    "overlay",
    "tab",
    "slider_track",
    "slider_fill",
    "toggle_off",
    "toggle_on",
    "menu_glass",
    "api",
    "edge",
    "selection_rim",
    "curve",
    "point",
    "point_selected",
}


def color(value):
    if isinstance(value, str):
        value = value.removeprefix("#")
        if len(value) not in (6, 8):
            raise ValueError("Colors use #RRGGBB or #RRGGBBAA")
        value = tuple(int(value[i : i + 2], 16) / 255 for i in range(0, len(value), 2))
    value = tuple(float(v) for v in value)
    if len(value) == 3:
        value += (1.0,)
    if len(value) != 4 or any(not isfinite(v) or not 0 <= v <= 1 for v in value):
        raise ValueError("RGBA components must be finite and between 0 and 1")
    return value


def merged(base, changes):
    result = deepcopy(base)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merged(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class StyleSheet:
    """Explicit addon branding layered over Blender theme roles.

    Presets are data, never executable CSS. extend() returns an independent copy;
    update() validates atomically, updates existing canvases and wakes owners once.
    Unspecified colors continue to follow Blender's current theme.
    """

    def __init__(
        self,
        *,
        name="Custom",
        colors=None,
        geometry=None,
        geometry_variants=None,
        surfaces=None,
        opacity=1.0,
        cards=False,
        variants=None,
        operators=None,
        motion=None,
        text_effects=None,
        wide_numeric_motion_scale=0.15,
    ):
        self._owners = WeakSet()
        self._canvases = WeakSet()
        self._original_geometry = WeakKeyDictionary()
        self._applied_revision = WeakKeyDictionary()
        self._canvas_variants = WeakKeyDictionary()
        self._cache = None
        self._variant_cache = {}
        self.revision = 0
        self.animation = AnimationSettings()
        self._data = deepcopy(
            dict(
                name=name,
                colors=colors or {},
                geometry=geometry or {},
                geometry_variants=geometry_variants or {},
                surfaces=surfaces or {},
                opacity=opacity,
                cards=bool(cards),
                variants=variants or {},
                operators=operators or {},
                motion=motion or {},
                text_effects=text_effects or {},
                wide_numeric_motion_scale=wide_numeric_motion_scale,
            )
        )
        self._validate(self._data)
        self._sync_motion()

    @staticmethod
    def _validate(data):
        from .text_effects import normalize

        normalize(data["text_effects"])
        if not isinstance(data["name"], str):
            raise ValueError("Style name must be text")
        if "" in data["geometry_variants"]:
            raise ValueError("Geometry variants require a nonempty name")
        if set(data["colors"]) - _COLORS:
            raise ValueError("Unknown semantic color role")
        for value in data["colors"].values():
            color(value)
        for name, geometry in {
            "": data["geometry"],
            **data["geometry_variants"],
        }.items():
            if not isinstance(name, str) or set(geometry) - set(_GEOMETRY):
                raise ValueError("Unknown geometry token or variant name")
            for key, value in geometry.items():
                low, high = _GEOMETRY[key]
                if (
                    isinstance(value, bool)
                    or not isfinite(value)
                    or not low <= value <= high
                ):
                    raise ValueError(f"{key} must be finite in [{low}, {high}]")
        for role, values in data["variants"].items():
            if not isinstance(role, str) or set(values) - _COLORS:
                raise ValueError("Variants map class names to semantic colors")
            for value in values.values():
                color(value)
        if any(v not in data["variants"] for v in data["operators"].values()):
            raise ValueError("Operator rule references an unknown variant")
        from .gpu.skin import ROLES

        if set(data["surfaces"]) - set(ROLES):
            raise ValueError("Unknown surface role")
        for pair in data["surfaces"].values():
            if len(pair) != 2:
                raise ValueError("Surface needs lower and upper RGBA colors")
            for value in pair:
                color(value)
        for key in ("opacity", "wide_numeric_motion_scale"):
            value = data[key]
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(key + " must be in [0,1]")
        if set(data["motion"]) - {"enabled", "strength", "speed"}:
            raise ValueError("Unknown motion token")
        AnimationSettings(**data["motion"])

    def _sync_motion(self):
        m = self._data["motion"]
        self.animation.enabled = m.get("enabled", True)
        self.animation.strength = m.get("strength", 1.0)
        self.animation.speed = m.get("speed", 1.0)

    def to_dict(self):
        return deepcopy(self._data)

    @classmethod
    def from_dict(cls, data):
        return cls(**deepcopy(data))

    def extend(self, **overrides):
        return type(self).from_dict(merged(self._data, overrides))

    def replace(self, **sections):
        candidate = self.to_dict()
        candidate.update(deepcopy(sections))
        self._commit(candidate)

    def update(self, **overrides):
        self._commit(merged(self._data, overrides))

    def _commit(self, candidate):
        if set(candidate) != set(self._data):
            raise ValueError("Unknown style section")
        self._validate(candidate)
        if candidate == self._data:
            return
        self._data = candidate
        self.revision += 1
        self._cache = None
        self._variant_cache.clear()
        self._sync_motion()
        for canvas in tuple(self._canvases):
            self.apply(canvas)
        for owner in tuple(self._owners):
            owner.refresh()

    def apply(self, canvas, *, variant=None):
        if variant is not None:
            if variant and variant not in self._data["geometry_variants"]:
                raise ValueError("Unknown geometry variant: " + str(variant))
            self._canvas_variants[canvas] = variant
        self._canvases.add(canvas)
        original = self._original_geometry.setdefault(
            canvas, {key: getattr(canvas.theme, key) for key in _GEOMETRY}
        )
        geometry = dict(original, **self._data["geometry"])
        geometry.update(
            self._data["geometry_variants"].get(self._canvas_variants.get(canvas), {})
        )
        next_theme = replace(canvas.theme, **geometry, stylesheet=self)
        changed = (
            next_theme != canvas.theme
            or self._applied_revision.get(canvas) != self.revision
        )
        canvas.theme = next_theme
        canvas.wide_numeric_motion_scale = self._data["wide_numeric_motion_scale"]
        canvas.animation = self.animation
        canvas.bind_animation(canvas._animation_parents, canvas._animation_wake)
        self._applied_revision[canvas] = self.revision
        if changed:
            # Style changes do not cancel the editor/dialog that is changing them.
            # Owners schedule one redraw; geometry is recomputed at the next layout.
            canvas._dirty = True
            if canvas._animation_wake:
                canvas._animation_wake()

    @property
    def cards(self):
        return self._data["cards"]

    def control_palette(self, base, control):
        name = control.options.get("style_class") or self._data["operators"].get(
            control.options.get("operator_id")
        )
        values = self._data["variants"].get(name)
        if not values:
            return base
        key = (id(base), name)
        if key not in self._variant_cache:
            if len(self._variant_cache) >= 64:
                self._variant_cache.clear()
            self._variant_cache[key] = MappingProxyType(
                dict(
                    base,
                    **{
                        k: (
                            color(v)[:3] + (color(v)[3] * self._data["opacity"],)
                            if k
                            in {
                                "field",
                                "input",
                                "hover",
                                "selected",
                                "card",
                                "bg",
                                "bar",
                            }
                            else color(v)
                        )
                        for k, v in values.items()
                    },
                )
            )
        return self._variant_cache[key]

    def palette(self, base):
        if self._cache is not None and self._cache[0] is base:
            return self._cache[1]
        from .gpu.skin import themed_roles

        p = dict(base)
        p["text_effects"] = MappingProxyType({**base.get("text_effects", {}), **self._data["text_effects"]})
        overrides = {key: color(value) for key, value in self._data["colors"].items()}
        p.update(overrides)
        if "accent" in overrides:
            for key in ("slider_fill", "toggle_on", "tab", "api"):
                if key not in overrides:
                    p[key] = overrides["accent"][:3] + (base[key][3],)
            if "selected" not in overrides:
                p["selected"] = overrides["accent"][:3] + (0.28,)
        surfaces, inks = themed_roles(p)
        p.update(inks)
        p.update(overrides)
        for role, pair in self._data["surfaces"].items():
            surfaces[role] = tuple(color(c) for c in pair)
        opacity = self._data["opacity"]
        # Text/data colors remain fully legible; only chrome opacity changes.
        for key in (
            "bg",
            "card",
            "bar",
            "field",
            "input",
            "selected",
            "hover",
            "overlay",
            "tab",
            "menu_glass",
            "toggle_off",
            "toggle_on",
        ):
            p[key] = p[key][:3] + (p[key][3] * opacity,)
        p["surfaces"] = MappingProxyType(
            {
                key: tuple(c[:3] + (c[3] * opacity,) for c in pair)
                for key, pair in surfaces.items()
            }
        )
        roles = (
            "bg",
            "card",
            "bar",
            "accent",
            "field",
            "text",
            "muted",
            "api",
            "selected",
        )
        tokens = dict(base["tokens"])
        for token, role in zip(tuple(tokens)[:9], roles):
            tokens[token] = p[role]
        p["tokens"] = MappingProxyType(tokens)
        p["source"] = base["source"] + "+preset:" + self._data["name"]
        result = MappingProxyType(p)
        self._cache = (base, result)
        return result
