"""Conditional file, asset, ID navigation and existing-editor route checks."""

import bpy, json, os, sys, traceback, tempfile
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Target, Menu
from beyond_ui import context_files, context_assets, context_jump, context_editor


def run():
    ctx = bpy.context
    commits, opened = [], []
    target = Target("data", commit=commits.append)

    def menu(rows, t=target):
        return Menu(t, rows, (0, 0), (0, 0, 800, 1000), context=ctx)

    def execute(rows, key, t=target):
        m = menu(rows, t)
        i = next(i for i, row in enumerate(m.page.rows) if row.key == key)
        m.refresh(ctx, all_rows=True)
        assert m.page.available[i], (key, m.error)
        m.choose(i, ctx)
        assert m.closed and m.error is None, m.error

    # Stub only external OS opening: path resolution and menu lifecycle are real.
    context_files.open_path = opened.append
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "source image.png"
        path.write_bytes(b"fixture")
        image = bpy.data.images.new("file fixture", width=1, height=1)
        image.filepath = str(path)
        source = rna_binding(lambda: image, "filepath").context
        rows = context_files.entries(source)
        execute(rows, "OPEN_FILE")
        execute(rows, "OPEN_LOCATION")
        assert opened == [str(path), folder]
        image.filepath = folder
        directory_rows = context_files.entries(source)
        assert [r.key for r in directory_rows] == ["OPEN_LOCATION"]
        execute(directory_rows, "OPEN_LOCATION")
        assert opened.pop() == folder
        image.filepath = str(Path(folder) / "missing")
        assert context_files.entries(source) == ()
        pending = menu(rows)
        pending.choose(0, ctx)
        assert len(opened) == 2, "Stale property must not open its old or new value"
        image.filepath = "//source image.png"
        assert not bpy.data.filepath and context_files.entries(source) == ()
        library = Path(folder) / "fixture.blend"
        bpy.data.libraries.write(str(library), {image})
        with bpy.data.libraries.load(str(library), link=True) as (available, loaded):
            loaded.images = [image.name]
        linked = loaded.images[0]
        linked_source = rna_binding(lambda: linked, "filepath").context
        execute(context_files.entries(linked_source), "OPEN_FILE")
        assert opened[-1] == str(path), "Resolve // against owner library, not cwd"
        path.unlink()
        assert context_files.entries(linked_source) == ()

    # Mark/Clear operate on exactly one ID even when another object is active.
    item = bpy.data.objects.new("asset target", None)
    ctx.collection.objects.link(item)
    active = ctx.active_object
    rows = context_assets.entries(lambda: item, ctx)
    execute(rows, "ASSET_MARK")
    assert item.asset_data and active.asset_data is None
    item.asset_data.description = "kept description"
    item.asset_data.author = "fixture"
    item.asset_data.catalog_id = "11111111-2222-3333-4444-555555555555"
    item.asset_data.tags.new("tag one")
    item.asset_data["custom"] = 19
    before_count = len(bpy.data.objects)

    def reject(action):
        item.location.x = 17
        raise RuntimeError("reject")

    denied = replace(target, commit=reject)
    m = menu(rows, denied)
    m.choose(next(i for i, r in enumerate(m.page.rows) if r.key == "ASSET_CLEAR"), ctx)
    assert m.error == "reject", m.error
    assert item.asset_data.description == "kept description"
    assert item.asset_data.author == "fixture"
    assert item.asset_data.catalog_id == "11111111-2222-3333-4444-555555555555"
    assert item.asset_data.tags[0].name == "tag one" and item.asset_data["custom"] == 19
    assert item.location.x == 17 and len(bpy.data.objects) == before_count
    execute(rows, "ASSET_CLEAR")
    assert item.asset_data is None
    m = menu(rows, denied)
    m.choose(0, ctx)
    assert m.error == "reject" and item.asset_data is None
    no_undo = menu(rows, Target("no undo"))
    assert not any(no_undo.page.available)
    selected = [item]
    stale = menu(context_assets.entries(lambda: selected[0], ctx))
    selected[0] = active
    stale.choose(0, ctx)
    assert active.asset_data is None

    # Jump uses this view layer and rolls back selection on rejected host commit.
    active_before = ctx.view_layer.objects.active
    selection_before = {o.as_pointer(): o.select_get() for o in ctx.view_layer.objects}
    jumps = context_jump.entries(lambda: item)
    m = menu(jumps, denied)
    m.choose(0, ctx)
    assert m.error == "reject" and ctx.view_layer.objects.active == active_before
    assert {
        o.as_pointer(): o.select_get() for o in ctx.view_layer.objects
    } == selection_before
    execute(jumps, "JUMP_TARGET")
    assert ctx.active_object == item and item.select_get()
    item.hide_set(True)
    assert not menu(jumps).page.available[0]
    item.hide_set(False)

    # Root pointer and both collection-search field/row menus expose exact IDs.
    pointer = rna_binding(lambda: ctx.scene, "camera").context
    pointer_rows = pointer.entries(target, ctx)
    assert {"ASSET_MARK", "ASSET_CLEAR", "JUMP_TARGET"}.issubset(
        {r.key for r in pointer_rows}
    )
    from beyond_ui import Canvas
    from beyond_ui.search import CollectionSearch

    bpy.types.Scene.bui_route_name = bpy.props.StringProperty()
    try:
        ctx.scene.bui_route_name = item.name
        binding = rna_binding(lambda: ctx.scene, "bui_route_name")
        search = CollectionSearch(binding, lambda: ctx.scene, "objects")
        search.canvas = Canvas(menu_commit=commits.append)
        root = replace(target, binding=binding)
        assert {"ASSET_MARK", "JUMP_TARGET"}.issubset(
            {r.key for r in search.entries(root, ctx)}
        )
        row = search.context_target(replace(target, part=("row", item.as_pointer())))
        assert {"ASSET_MARK", "JUMP_TARGET"}.issubset(
            {r.key for r in row.payload(row, ctx)}
        )
        pending = menu(search.entries(root, ctx), root)
        ctx.scene.bui_route_name = active.name
        pending.choose(
            next(i for i, r in enumerate(pending.page.rows) if r.key == "ASSET_MARK"),
            ctx,
        )
        assert item.asset_data is None and active.asset_data is None
    finally:
        del bpy.types.Scene.bui_route_name

    # Bone navigation stays on the explicitly active pose rig, with API fallback.
    arm = bpy.data.armatures.new("jump rig data")
    rig = bpy.data.objects.new("jump rig", arm)
    ctx.collection.objects.link(rig)
    for other in ctx.selected_objects:
        other.select_set(False)
    rig.select_set(True)
    ctx.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name in ("First", "Second"):
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode="POSE")
    pose = rig.pose.bones["Second"]
    execute(context_jump.entries(lambda: pose), "JUMP_TARGET")
    assert rig.data.bones.active == pose.bone
    assert pose.select if hasattr(pose, "select") else pose.bone.select
    execute(context_jump.entries(lambda: rig.data.bones["First"]), "JUMP_TARGET")
    assert rig.data.bones.active.name == "First"
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    item.select_set(True)
    ctx.view_layer.objects.active = item

    # Public native editor path; no active native UI button and no new window.
    item.location.y = 3
    item.keyframe_insert(data_path="location", index=1, frame=1)
    item.location.y = 5
    item.keyframe_insert(data_path="location", index=1, frame=8)
    source = rna_binding(lambda: item, "location", index=1).context
    assert context_editor.route(source, ctx, False) is None
    area = next(a for a in ctx.screen.areas if a.type == "DOPESHEET_EDITOR")
    area.type = "GRAPH_EDITOR"
    area.spaces.active.mode = "FCURVES"
    area.spaces.active.dopesheet.show_only_selected = False
    resolved = context_editor.route(source, ctx, False)
    assert resolved is not None, "Existing Graph Editor must expose the exact channel"
    execute(context_editor.entries(source), "VIEW_CURVE_ALL")
    assert all(f.select for f in resolved[-1])
    driver = item.driver_add("location", 2)
    driver.driver.expression = "2"
    area.spaces.active.mode = "DRIVERS"
    driven = source.component(2)
    assert context_editor.route(driven, ctx, True) is not None
    execute(context_editor.entries(driven), "VIEW_DRIVER_ALL")
    assert driver.select
    item.driver_remove("location", 2)
    assert context_editor.route(driven, ctx, True) is None
    return dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "File/location actions resolve owner-library relative paths; no OS opener executed in tests",
            "Missing/unsaved paths and stale values reject external opening",
            "Asset actions touch only the captured ID and require host undo",
            "Rejected clear restores complete metadata, tags, custom fields and catalog UUID",
            "Rejected mark removes metadata; temporary backup IDs are released",
            "Pointer replacement rejects stale asset actions",
            "Root pointer/search and candidate-row menus include exact-ID actions",
            "Object jump selects exact view-layer target; rejected commit restores selection",
            "Pose and data-bone jump uses the active rig and version-gated selection API",
            "Existing Graph/Drivers Editor routes exact channels without native buttons or new windows",
        ],
    )


try:
    result = run()
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
