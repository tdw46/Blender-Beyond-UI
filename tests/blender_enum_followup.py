"""RNA enum groups, modifier distinction and metadata compatibility."""

import bpy, os, sys, json
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import Canvas, Layout
from beyond_ui.hosts import menu_native
from beyond_ui.context_enums import items as enum_items

rows = [
    ("", "Main", "Heading"),
    ("A", "Alpha", "Alpha description", "MESH_CUBE", 1),
    None,
    ("", "Extras", "Other heading"),
    ("B", "Beta", "Beta description", "LIGHT", 2),
    ("C", "Gamma", "Gamma description", "CAMERA_DATA", 4),
]
bpy.types.Scene.enum_followup = bpy.props.EnumProperty(
    items=rows, options={"ENUM_FLAG"}, default={"A"}
)


def dynamic(owner, context):
    return rows


bpy.types.Scene.enum_followup_dynamic = bpy.props.EnumProperty(items=dynamic)
try:
    ctx = bpy.context
    ctx.scene.enum_followup_dynamic = "A"
    assert menu_native.api() is not None, menu_native.reason()
    for prop in ("enum_followup", "enum_followup_dynamic"):
        full = enum_items(ctx.scene, prop, ctx, include_separators=True)
        assert [i.name for i in full if i.identifier == ""] == ["Main", "", "Extras"], [
            (i.identifier, i.name) for i in full
        ]
        assert len(enum_items(ctx.scene, prop, ctx)) == 3
        for identifier in ("A", "B", "C", "UNKNOWN"):
            for name in ("enum_item_name", "enum_item_description", "enum_item_icon"):
                actual = getattr(Layout, name)(ctx.scene, prop, identifier)
                expected = getattr(bpy.types.UILayout, name)(
                    ctx.scene, prop, identifier
                )
                assert actual == expected, (name, identifier, actual, expected)
    # Public RNA omits structural rows; retain useful choices on unqualified builds.
    fallback = enum_items(ctx.scene, "enum_followup", None, include_separators=True)
    assert [i.identifier for i in fallback] == ["A", "B", "C"]
    from unittest.mock import patch

    expected = [
        getattr(bpy.types.UILayout, name)(ctx.scene, "enum_followup", "A")
        for name in ("enum_item_name", "enum_item_description", "enum_item_icon")
    ]
    with patch.object(menu_native, "enum_items", return_value=None):
        actual = [
            getattr(Layout, name)(ctx.scene, "enum_followup", "A")
            for name in ("enum_item_name", "enum_item_description", "enum_item_icon")
        ]
    assert actual == expected, (actual, expected)
    commits = []
    canvas = Canvas()
    ui = Layout(canvas, context=ctx, commit=lambda a, b: commits.append((a, b)))
    ui.prop(ctx.scene, "enum_followup", text="Flags")
    expanded = list(canvas.controls.values())
    a = next(c for c in expanded if c.label == "Alpha")
    b = next(c for c in expanded if c.label == "Beta")
    single = ui.prop_enum(ctx.scene, "enum_followup", "C")
    menu_control = ui.prop_menu_enum(ctx.scene, "enum_followup", text="Flag menu")
    ui.props_enum(ctx.scene, "enum_followup")
    canvas.arrange(560)
    clip = (0, 0, 560, 800)

    def click(c, shift=False):
        x, y, w, h = c.rect
        canvas.event(
            NS(type="LEFTMOUSE", value="PRESS", shift=shift),
            x + w / 2,
            y + h / 2,
            clip,
            context=ctx,
        )

    click(b)
    assert ctx.scene.enum_followup == {"B"}
    click(a, True)
    assert ctx.scene.enum_followup == {"A", "B"}
    click(b, True)
    assert ctx.scene.enum_followup == {"A"}
    click(a, True)
    assert ctx.scene.enum_followup == set()
    click(a)
    assert ctx.scene.enum_followup == {"A"}
    click(a)
    assert ctx.scene.enum_followup == {
        "A"
    }  # exclusive selected flag cannot clear itself
    click(single)
    assert ctx.scene.enum_followup == {"A", "C"}
    click(menu_control)
    menu = canvas.context_menu
    assert [r.label for r in menu.page.rows if r.heading] == ["Main", "Extras"]
    assert menu.page.rows[2].heading and menu.page.rows[2].divider
    assert menu.page.highlight == 1
    menu.event(NS(type="DOWN_ARROW", value="PRESS"), 10, 10, ctx)
    assert menu.page.highlight == 3
    menu.choose(2, ctx)
    assert not menu.closed and ctx.scene.enum_followup == {"A", "C"}
    menu.choose(3, ctx)
    assert ctx.scene.enum_followup == {"A", "B", "C"}
    canvas.cancel()
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Static and dynamic RNA headings/separators survive opt-in copy; old callers still receive choices only",
            "Expanded flag strips: exclusive plain clicks, Shift toggles including empty; individual prop_enum still toggles",
            "Headings use nonselectable rows, separators stay attached, arrows skip headings",
            "Name, description and icon metadata equal native class methods for static/dynamic/missing choices",
            "Public-RNA fallback preserves static choices and metadata; grouping remains unavailable",
            "Exact-build native adapter admitted after reviewed Python-only item-copy change",
        ],
    )
finally:
    del bpy.types.Scene.enum_followup
    del bpy.types.Scene.enum_followup_dynamic
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(result)
