"""Exact selected-owner domains and animation applicability; disposable background."""

import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target


def run():
    ctx = bpy.context
    commits = []

    def subject(owner, name, index=None, commit=None):
        binding = rna_binding(
            lambda: owner,
            name,
            index=index,
            commit=commit or (lambda before, after: commits.append((before, after))),
        )
        return binding.context, Target(
            name, binding=binding, valid=binding.context.valid, commit=commits.append
        )

    owner = ctx.active_object
    owner.animation_data_clear()
    y, target = subject(owner, "location", 1)

    def menu():
        return Menu(
            target, y.entries(target, ctx), (0, 0), (0, 0, 800, 1200), context=ctx
        )

    def available(m, key):
        m.refresh(ctx, all_rows=True)
        return m.page.available[
            next(i for i, row in enumerate(m.page.rows) if row.key == key)
        ]

    def label(key):
        return next(r.label for r in y.entries(target, ctx) if r.key == key)

    assert label("KEY") == "Insert Keyframe"
    ctx.scene.frame_set(8, subframe=0.25)
    owner.keyframe_insert(data_path="location", index=1, frame=8.25)
    assert label("KEY") == "Replace Keyframe"
    assert label("KEY_ALL") == "Replace All Keyframes"
    assert not available(menu(), "DRIVER")
    assert not y.animation_applicable("PASTE_DRIVER")
    before = len(commits)
    y.execute("DRIVER", target, ctx)
    assert not owner.animation_data.drivers and len(commits) == before
    ctx.scene.frame_set(9)
    assert label("KEY") == "Insert Keyframe"
    assert not available(menu(), "DRIVER"), "Other-frame animation blocks Add Driver"
    owner.animation_data_clear()
    stale = menu()
    owner.driver_add("location", 1)
    assert not available(stale, "KEY") and not available(stale, "DRIVER")
    assert not available(stale, "KEY_ALL")
    y.execute("KEY", target, ctx)
    assert owner.animation_data.action is None and len(commits) == before
    owner.driver_remove("location", 1)
    owner.driver_add("location", 0)
    assert available(menu(), "KEY"), "Sibling X driver must not block Y"
    assert not available(menu(), "KEY_ALL"), "All-channel action includes driven X"

    # Shared light data is copied exactly once, incompatible camera data is ignored.
    a = bpy.data.lights.new("source", "POINT")
    b = bpy.data.lights.new("receiver", "POINT")
    wrong = bpy.data.cameras.new("wrong domain")
    objects = [
        bpy.data.objects.new(n, data)
        for n, data in (("A", a), ("B", b), ("B user 2", b), ("camera", wrong))
    ]
    selection = NS(selected_objects=objects)
    source, dest = subject(a, "energy")
    a.energy, b.energy = 12, 3
    assert source.selected(selection) == (b,)
    before = len(commits)
    source.execute("SELECTED", dest, selection)
    assert b.energy == 12 and len(commits) == before + 1
    source.execute("SELECTED", dest, selection)
    assert len(commits) == before + 1, "No-op copies must not commit"

    # Nodes use the selected node domain, not an active object or a name match.
    tree = bpy.data.node_groups.new("selection fixture", "ShaderNodeTree")
    n1, n2 = (tree.nodes.new("ShaderNodeValue") for _ in range(2))
    n3 = tree.nodes.new("ShaderNodeRGB")
    n1.location, n2.location = (4, 5), (8, 9)
    source, dest = subject(n1, "location", 0)
    nodes = NS(selected_nodes=[n1, n2, n3])
    assert source.selected(nodes) == (n2,)
    source.execute("SELECTED", dest, nodes)
    assert tuple(n2.location) == (4, 9)
    nodes.selected_nodes = []
    n1.location.x = 20
    source.execute("SELECTED", dest, nodes)
    assert tuple(n2.location) == (4, 9), "Selection is re-read at execution"

    # Real pose bones, with explicit fixture selection independent of a UI editor.
    arm = bpy.data.armatures.new("armature")
    rig = bpy.data.objects.new("rig", arm)
    ctx.collection.objects.link(rig)
    for obj in ctx.selected_objects:
        obj.select_set(False)
    rig.select_set(True)
    ctx.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name in ("A", "B"):
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode="POSE")
    p1, p2 = rig.pose.bones["A"], rig.pose.bones["B"]
    bones = NS(selected_pose_bones=[p1, p2])
    p1.location, p2.location = (2, 3, 4), (7, 8, 9)
    source, dest = subject(p1, "location", 1)
    source.execute("SELECTED", dest, bones)
    assert tuple(p2.location) == (7, 3, 9)

    def reject(before, after):
        p2.location.z = 33
        raise RuntimeError("reject commit")

    source.commit = reject
    p1.location.y = 15
    try:
        source.execute("SELECTED", dest, bones)
    except RuntimeError as error:
        assert str(error) == "reject commit"
    else:
        raise AssertionError("Rejected commit must propagate")
    assert tuple(p2.location) == (7, 3, 33), "Restore clicked component only"
    data_source, _ = subject(p1.bone, "use_deform")
    assert data_source.selected(bones) == (p2.bone,)
    bpy.ops.object.mode_set(mode="OBJECT")
    return dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Replace wording follows current subframe, insertion remains available elsewhere",
            "Animated channels reject Add/Paste Driver; driven channels reject key insertion",
            "Open menus and direct actions revalidate conflicts; sibling component stays independent",
            "Selected object data is type checked and shared datablocks deduplicated",
            "Selected nodes, pose bones and data bones resolve exact owners",
            "Selection changes, no-op suppression and rejected component commits are respected",
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
