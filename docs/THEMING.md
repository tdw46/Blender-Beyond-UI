# Blender theme colors

Production canvases use Blender's active theme by default. Pass the host's
`context.preferences` to `Canvas.paint(...)`; `PanelHost` already does this.
The original BVT `_shoost_canvas_style.py` is the behavioral source, recorded in
[SOURCE_UI_CONTRACT.md](SOURCE_UI_CONTRACT.md).

One bounded snapshot of eleven public widget colors is read per visible Canvas
paint. Derived palettes are immutable and cached by their color signature (eight
entries); no RNA pointers are retained. Theme changes appear on the next host
redraw without an extension reload, geometry invalidation, backdrop recapture,
or added timer. Hosts that suppress normal Blender redraws must request their
usual redraw after an external theme change.

The palette exposes `source` (`blender`, `mixed`, `fallback`, or `reference`) and
`fallback_roles`. Missing, removed, malformed or nonfinite theme fields use
explicit deterministic fallbacks. A host with no preferences gets `fallback`,
not a claim that the user's theme was read. Colors are already display-space;
there is no scene-linear conversion or preference mutation in library code.

## Semantic mapping

| UI role | Source widget color |
| --- | --- |
| Canvas/input/graph backgrounds | `wcol_regular.inner` |
| Cards, headers, buttons | `wcol_tool.inner` |
| Numeric fields | `wcol_num.inner` |
| Text, titles, icons, unselected points | `wcol_regular.text` |
| Muted text, dividers, grid, scrollbar thumb | Regular text/background mixtures with material alpha |
| Selected text/icons | `wcol_radio.text_sel` |
| Curve and selected points | `wcol_radio.inner_sel` |
| Selected row | Source radio accent/tool background mixture |
| Active tabs | `wcol_tab.inner_sel` |
| Slider/progress track and fill | `wcol_numslider.inner` / `.item` |
| Toggle off/on | `wcol_toggle.inner` / `.inner_sel` |

All eight compound cards use these roles. Their existing translucent surface
alpha hierarchy and gradient deltas stay fixed; theme RGB supplies their color.
Source primitives retain their original source opacity values. Neutral shader
bevel/specular lighting remains a material effect. User-authored palette swatches,
ramp textures, HSV fields and previews bypass the chrome mapping.

The custom graph currently uses the source widget-role family, not the Graph
Editor's editor-specific theme. That mapping is deliberate and centralized;
it does not claim full native Graph Editor appearance or behavior.

## Reproducible reference fixtures

```python
from beyond_ui import Canvas, Theme
from beyond_ui.gpu.style import theme_palette

# Production host: uses the passed context.preferences.
canvas = Canvas()

# Explicit, fixed artwork fixture; never selected implicitly by production.
reference_canvas = Canvas(Theme(palette="REFERENCE"))
reference_palette = theme_palette(reference=True)  # direct widget capture
```

`Theme` is frozen; replace `canvas.theme` with a new `Theme` to change policy and
request the host's ordinary redraw. Palette-only changes need no layout rebuild.
Do not mutate cached palette mappings or use a process-global override: different
canvases can display different policies in the same window.

[Theme QA](design/qa/theme-v1/index.html) includes actual captures, the generated
reference conflict, runtime records and performance limits. Theme wiring is
execution-tested; exact theme-reference fidelity remains open.

## Compatibility evidence

The relevant public API surfaces were checked through exact versioned official
search results: [4.2 widget colors](https://docs.blender.org/api/4.2/bpy.types.ThemeWidgetColors.html),
[4.2 UI theme](https://docs.blender.org/api/4.2/bpy.types.ThemeUserInterface.html),
[5.1 UI theme](https://docs.blender.org/api/5.1/bpy.types.ThemeUserInterface.html),
and [5.2 UI theme](https://docs.blender.org/api/5.2/bpy.types.ThemeUserInterface.html).
The [5.1 Manual](https://docs.blender.org/manual/de/5.1/editors/preferences/themes.html)
describes live theme updates. Exact 4.2/5.1/5.2 English Manual URLs and 5.1/5.2
WidgetColors pages were also attempted, but direct retrieval returned 402/403;
this is not a claim of successful page verification. Installed 5.1.2 and 5.2.2
RNA reads, writes, restoration and actual drawing provide execution evidence.
4.2 runtime execution and Windows/Linux remain unqualified in this checkpoint.
