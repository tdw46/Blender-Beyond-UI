"""Consumer-owned, retained RGBA artwork and native-safe panel header helpers.

Loading is explicit (register/startup), never hidden in a draw callback. Packs
contain display-space RGBA bytes; assets do not create Blender image datablocks.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import zlib


@dataclass(frozen=True)
class Artwork:
    token: str
    fallback: str = 'IMAGE_DATA'


class ArtworkLibrary:
    def __init__(self, namespace):
        if not isinstance(namespace, str) or not namespace or ':' in namespace:
            raise ValueError('Use a nonempty, extension-qualified artwork namespace')
        self.namespace = namespace
        self.assets = {}
        self.loaded = False

    def load(self, path):
        """Load a trusted addon-local pack once; call close() during unregister."""
        if self.loaded:
            return
        from .gpu import icons
        path = Path(path).resolve()
        spec = json.loads(path.read_text())
        sources = {}
        for key, data in spec['sources'].items():
            width, height = data['size']
            if not all(isinstance(n, int) and 0 < n <= 4096 for n in (width, height)):
                raise ValueError('Artwork dimensions must be in 1..4096')
            source = (path.parent / data['file']).resolve()
            if path.parent not in source.parents:
                raise ValueError('Artwork source must stay inside its pack directory')
            decoder = zlib.decompressobj()
            raw = decoder.decompress(source.read_bytes(), width * height * 4 + 1)
            if len(raw) != width * height * 4 or not decoder.eof:
                raise ValueError('Artwork RGBA byte count mismatch')
            sources[key] = (width, height, raw)
        entries, assets = {}, {}
        for name, data in spec['icons'].items():
            if not name or ':' in name or data['source'] not in sources:
                raise ValueError('Invalid artwork name or source')
            token = self.namespace + ':' + name
            width, height, _ = sources[data['source']]
            x, y, w, h = data['rect']
            if not all(isinstance(n, int) for n in (x,y,w,h)) or min(x,y) < 0 or min(w,h) <= 0 or x+w > width or y+h > height:
                raise ValueError('Artwork bounds exceed source')
            entries[token] = (data['source'], (x,y,w,h), bool(data.get('tint', False)))
            assets[name] = Artwork(token, data.get('fallback', 'IMAGE_DATA'))
        icons.register_artwork(self.namespace, sources, entries)
        self.assets = assets
        self.loaded = True

    def __getitem__(self, name):
        return self.assets[name]

    def close(self):
        from .gpu import icons
        icons.unregister_artwork(self.namespace)
        self.assets.clear()
        self.loaded = False


def _custom(layout):
    from .layout import Layout
    from .layout_recording import Node
    return isinstance(layout, (Layout, Node))


def heading(layout, text, *, icon=None, size=20, trailing=False, **style_options):
    """Normal label with optional themed/colored artwork; native icon fallback."""
    from .style_api import style
    glyph = icon.token if isinstance(icon, Artwork) and _custom(layout) else icon.fallback if isinstance(icon, Artwork) else icon or 'NONE'
    if trailing and _custom(layout):
        row = layout.row(align=True)
        label = row.column(align=True)
        style(label, scope='group', flex_grow=1)
        label.label(text=text)
        style(label, font_weight='bold', **style_options)
        art = row.column(align=True)
        style(art, scope='group', width=size+4)
        art.label(text='', icon=glyph)
        style(art, height=max(24,size), icon_size=size, text_align='center')
    else:
        layout.label(text=text, icon=glyph)
        style(layout, font_weight='bold', icon_size=size, **style_options)
    return layout


def header(layout, title, *, subtitle='', icon=None, size=40, gap=10, padding=4,
           text_gap=0, align_items='center', divider=False, divider_height=None,
           icon_style=None, title_style=None, subtitle_style=None, divider_style=None):
    """Native-safe media header; every element accepts ordinary bui.style options.

    size controls the icon's visible longest axis. Row align_items aligns the full
    icon and text block, including wrapped subtitles. Divider has independent
    height, thickness, color and spacing. No custom widget or draw callback.
    """
    from .style_api import style, normalize
    # Validate all user overrides before recording any partial layout.
    icon_options = normalize(dict(height=size+4, icon_size=size, text_align='center'), **(icon_style or {}))
    title_options = normalize(dict(font_size=16, font_weight='bold', color_role='title', line_height=24, wrap=True), **(title_style or {}))
    subtitle_options = normalize(dict(font_size=11, font_weight='normal', color_role='muted', line_height=18, wrap=True), **(subtitle_style or {}))
    divider_options = normalize(dict(width=1, height=36 if divider_height is None else divider_height, divider_width=1, color_role='edge'), **(divider_style or {}))
    row_options = normalize(gap=gap, padding=padding, align_items=align_items)
    if type(divider) is not bool:
        raise ValueError('divider must be Boolean')
    row = layout.row(align=True)
    style(row, scope='group', **row_options)
    if icon is not None:
        art = row.column(align=True)
        lane = max(size+4, icon_options.get('icon_size',size)+4)
        style(art, scope='group', width=lane, min_width=lane, max_width=lane, align='CENTER')
        glyph = icon.token if isinstance(icon, Artwork) and _custom(layout) else icon.fallback if isinstance(icon, Artwork) else icon
        art.label(text='', icon=glyph)
        style(art, **icon_options)
        if divider and _custom(layout):
            row.separator(type='LINE')
            style(row, **divider_options)
    content = row.column(align=True)
    style(content, scope='group', gap=text_gap, flex_grow=1)
    content.label(text=title)
    style(content, **title_options)
    if subtitle:
        content.label(text=subtitle)
        style(content, **subtitle_options)
    return row
