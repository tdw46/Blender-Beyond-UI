"""Generate a complete member-by-member native routing table from official docs."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "docs/api_inventory.json").read_text(encoding="utf-8"))
versions = list(data)
ledger = json.loads((ROOT / "docs/CUSTOM_PARITY.json").read_text(encoding="utf-8"))["members"]
custom_summary = "The member-by-member [custom parity ledger](CUSTOM_PARITY.json) is authoritative:\n**{unimplemented} unimplemented / {partial} partial / {matched} reference-matched** members. Native delegation\ndoes not count toward these totals. The table below groups current partial work.\n\n| Family | Custom support | Remaining examples |\n| --- | --- | --- |\n| Surfaces, vector icons, glass and springs | Retained BVT primitives and host-owned lifetime | Exact reference/theme/platform and source-equivalent performance qualification |\n| Labels, buttons, booleans, numbers, text and enums | Shared Canvas fields, source switches/sliders, searchable menus | Full property combinations, focus/accessibility and exact acceptance |\n| Color editing | Custom SV/hue/RGB/HSV/alpha/hex controls | Host eyedropper, locking/cubic modes and full native semantics |\n| Layout | Retained rows, columns, flows, grids, boxes, sizing policies and panel popovers | Remaining UILayout settings and complete sizing/alignment semantics |\n| Popup keyboard | Initial text/numeric activation and guarded default operator actions | Other control kinds, operator variants, full native acceptance/Tab navigation and exact acceptance; see [keyboard contract](POPUP_KEYBOARD.md) |\n| Large lists | Default lists and registered Python row/filter callbacks on retained visible canvases | Bounded callback settings/layouts, native-only callbacks, drag/drop and full native semantics; see [registered lists](REGISTERED_LISTS.md) |\n| Color ramps and curves | Custom stop/point editing and channel controls | Remaining interpolation, handles, bounds and specialized modes |\n| Data selectors | Searchable ID and supported non-ID pointers, collection searches, ID tabs and ID actions | Unsupported pointer categories and preview/template families |\n| Property decorators and menus | Custom keyframe/driver states, property actions, registered menus and scoped shortcuts | Full context coverage, platform admission and native semantics |\n| Scopes, specialized previews, asset/file browsers and pie menus | Unimplemented members remain explicitly tracked | Custom implementations and interaction/reference evidence |".format(
    unimplemented=sum(row["status"] == "unimplemented" for row in ledger.values()),
    partial=sum(row["status"] == "partial" for row in ledger.values()),
    matched=sum(row["status"] == "reference-matched" for row in ledger.values()),
)
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
    *custom_summary.splitlines(),
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
(ROOT / "docs/COVERAGE.md").write_text(
    "\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n"
)
