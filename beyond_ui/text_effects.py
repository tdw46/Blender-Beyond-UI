"""Native-font text treatment shared by panels, widgets and menus."""
from math import isfinite

DEFAULTS = dict(outline=True, shadow=True, outline_opacity=0.28,
                shadow_opacity=0.20, shadow_offset=(0, -1), shadow_blur=3)


def normalize(values):
    values = dict(values)
    if values.keys() - DEFAULTS.keys():
        raise ValueError('Unknown text effect option')
    for key, value in values.items():
        if key in {'outline', 'shadow'}:
            if not isinstance(value, bool):
                raise ValueError(key + ' must be boolean')
        elif key.endswith('_opacity'):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(key + ' must be finite in [0,1]')
        elif key == 'shadow_blur':
            if type(value) is not int or value not in (0, 3, 5):
                raise ValueError('shadow_blur must be 0, 3 or 5')
        elif key == 'shadow_offset':
            value = tuple(value)
            if len(value) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or abs(v) > 8 for v in value):
                raise ValueError('shadow_offset needs two finite values in [-8,8]')
            values[key] = value
    return values
