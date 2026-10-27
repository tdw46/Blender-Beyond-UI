"""Generate a complete member-by-member native routing table from official docs."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "docs/api_inventory.json").read_text())
versions = list(data)
lines = [
    "# Blender API coverage",
    "",
    "This native reference table documents **lossless access to Blender's native UI API**. It does not mean every widget is GPU-redrawn in the Effect Layers style. Native controls retain Blender's own keyboard, context menu, undo, tooltip, accessibility, and specialized-editor behavior.",
    "",
    "`NativeLayout` delegates methods, arguments and property assignments unchanged. It wraps only returned UILayout objects (including tuples); operator property objects remain native. Future installed members are reachable without a library update. Missing methods raise the original error; use `supports()` to choose an explicit compatibility path.",
    "",
    "Panel, Menu, Header and UIList remain ordinary host-registered Blender classes. No replacement class, custom registration framework or reduced set of hooks is imposed. Use `NativeLayout(self.layout)` in draw callbacks and `NativeLayout(layout)` in UIList.draw_item.",
    "",
    "## Custom backend",
    "",
    "| Family | Custom support | Full Blender behavior |",
    "| --- | --- | --- |",
    "| Rounded surfaces, vector icons, glass and springs | Extracted GPU primitives | Host controls presentation and lifetime |",
    "| Labels, buttons, booleans, scalar numbers, text, compact enums | Canvas controls | Native Layout for complete keymaps/context menus/accessibility |",
    "| Colors | Custom RGB/HSV/hex math and swatches; host picker action | Native prop/template_color_picker for full picker |",
    "| Images, thumbnails, material previews | Retained GPU textures and bounded caches | Native templates for Blender preview jobs |",
    "| Rows, columns, boxes, search, grouping, clipping | Custom geometry helpers | Native Layout for exact sizing/translation/panel state |",
    "| Large lists | Indexed visible ranges; host builds visible items | template_list/UIList for native selection/filtering |",
    "| Color ramps, curve editors, histograms, scopes, direction spheres | Native route only | All installed native templates exposed |",
    "| Assets, ID/search pickers, file browser, operator popups, pie menus | Native route only | All installed native templates exposed |",
    "| Animatable property decorators, driver clipboard, keymaps | Native route only | No active-native-button impersonation |",
    "",
    "## Version inventory",
    "",
    "Fetched from exact versioned official API pages; see `api_inventory.json` for signatures and URLs. Runtime verification is a separate table in VALIDATION.md. A member present in docs is not an assertion that all its context-dependent combinations were exercised.",
    "",
]
for typename in ("UILayout", "Panel", "Menu", "UIList", "Header"):
    members = sorted(
        set().union(*(set(data[v][typename]["members"]) for v in versions))
    )
    lines += [
        "## " + typename,
        "",
        "| Member | " + " | ".join(versions) + " | Route |",
        "| --- | " + " | ".join("---" for _ in versions) + " | --- |",
    ]
    for name in members:
        flags = [
            "yes" if name in data[v][typename]["members"] else "—" for v in versions
        ]
        route = (
            "NativeLayout → native"
            if typename == "UILayout"
            else "Host-owned native class"
        )
        lines.append("| `" + name + "` | " + " | ".join(flags) + " | " + route + " |")
    lines.append("")
(ROOT / "docs/COVERAGE.md").write_text("\n".join(lines) + "\n")
