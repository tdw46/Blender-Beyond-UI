# Consumer artwork and panel headers

Beyond UI retains transparent, display-space RGBA artwork separately from Blender's
native icon atlas. Branding belongs to the consuming addon; native property/search
icons, ownership and interactions remain intact. This does not replace semantic
Blender theme colors. Set `tint: true` on monochrome assets to follow the text role;
colored brand assets retain their authored colors. Surface `opacity` changes chrome, not lettering.

```python
from ._vendor import beyond_ui as bui
from pathlib import Path

art = bui.ArtworkLibrary("my_addon.brand")

def register():
    # After any loader that reloads this module; never inside draw().
    art.load(Path(__file__).parent / "resources/artwork.json")
    # Register your classes / integration as usual.

def unregister():
    # Tear down UI hosts first.
    art.close()

# In an ordinary Panel.draw(self, context):
bui.header(self.layout, "My Addon", subtitle="A short description",
           icon=art["logo"], size=40)
bui.heading(self.layout, "Objects", icon=art["objects"], size=20)
```

`header` builds a fixed icon lane and flexible text column from ordinary layout
controls. All sizes below are host logical units; no artwork pixels enter layout.

```python
bui.header(layout, "CamKeys", subtitle="Camera-driven expressions",
    icon=art["logo"], size=50, gap=9, padding=(6, 4),
    align_items="center", text_gap=0,
    divider=True, divider_height=38,
    title_style={"font_size": 18, "font_weight": "bold", "line_height": 25},
    subtitle_style={"font_size": 12.5, "line_height": 20, "color_role": "muted"},
    icon_style={"icon_size": 50},
    divider_style={"divider_width": 1, "color_role": "edge"})
```

- `size` / `icon_style.icon_size`: visible longest axis; original proportions stay intact.
- `align_items`: `start`, `center` (default), or `end`; aligns complete icon, divider
  and text blocks. This also works on any row through `bui.style(row, scope="group", ...)`.
- `gap`, `padding`, `text_gap`: spacing around lanes, outside the header and between text rows.
- `divider`, `divider_height`: optional vertical rule. `divider_style` controls its
  thickness (`divider_width`), color/theme role, width and margins independently.
- `title_style`, `subtitle_style`, `icon_style`: ordinary per-element `bui.style`
  dictionaries, including size, weight, color, theme role, margin and text effects.
  `color` explicitly overrides `color_role`. Defaults use `title` and `muted`
  semantic theme roles; they continue to follow theme changes.
- `line_height`: baseline-row spacing in logical units. Wrapping adds real layout
  height; use it instead of fixed `height` on titles/subtitles. An explicitly fixed
  height remains an author-imposed constraint.

The returned row also accepts `bui.style(row, scope="group", ...)`. Consumer presets
are plain dictionaries, freely reusable and independently overridable per panel.
`heading` supports `trailing=True` and normal inline style options. Both helpers use
a declared native icon fallback on Blender's native UILayout; decorative custom
header dividers and style-only typography are omitted on that fallback route.
`bui.style(layout, icon_size=20)` is available for ordinary labels. Artwork tokens
can be used as custom `icon` values on Beyond UI controls; keep these native-safe
helpers for shared native draw code.

Prepare transparent PNGs offline. Pack them with:

```sh
python3 tools/pack_artwork.py sources.json my_addon/resources
```

Pillow is only a packaging dependency. Example `sources.json`:

```json
{
  "sources": {"logo": "logo.png", "sheet": "sections.png"},
  "icons": {
    "logo": {"source": "logo", "fallback": "CAMERA_DATA"},
    "objects": {"source": "sheet", "rect": [0, 0, 128, 128],
                "fallback": "OUTLINER_OB_MESH", "tint": true}
  }
}
```

Rectangles use top-left source coordinates. Omit a rectangle to use the whole
source's alpha bounds. Packing preserves pixels; remove unwanted backgrounds
before packing. Ship `artwork.json` and its `.rgba.zlib` files. Loading validates
bounds and exact decompressed byte counts. Namespaces are unique; limits are
16 packs, 8 textures per pack, 128 entries per pack and 4096 pixels per dimension.
Use small shared sheets for production. The CamKeys example uses two textures
for five assets, uploaded once and released on unregister. No IO, texture creation,
shader compilation or new redraw timer is added to steady-state painting.

Current execution evidence: Blender 5.1.2/5.2.2 naming/lifecycle; Metal GPU artwork
and multi-scale Uraraka captures on 5.2.2. Other GPU backends were not visually
qualified in this batch. See the [current header review](design/qa/camkeys-headers-v2/index.html).
