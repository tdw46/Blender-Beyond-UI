"""Disposable non-ID pointer owners, membership generations and transactions."""

import bpy, json, os, sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from non_id_fixture import selection_transaction
from beyond_ui import Canvas, Layout, PointerItems, UnsupportedControl
from beyond_ui.widgets.context import target

ctx = bpy.context
arm = bpy.data.armatures.new("PointerFixture")
obj = bpy.data.objects.new("PointerFixture", arm)
ctx.collection.objects.link(obj)
ctx.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name in ("Alpha", "Beta", "Gamma"):
    bone = arm.edit_bones.new(name)
    bone.tail.z = 1
bpy.ops.object.mode_set(mode="OBJECT")
arm.bones.active = arm.bones[0]
tree = bpy.data.node_groups.new("PointerFixture", "ShaderNodeTree")
for name in ("First", "Second", "Third"):
    node = tree.nodes.new("ShaderNodeValue")
    node.name = name
tree.nodes.active = tree.nodes[0]
generation = [0]
commits = []
checks = []


def policy(owner, prop):
    return PointerItems(
        lambda: owner, revision=lambda: generation[0], transaction=selection_transaction
    )


ui = Layout(
    Canvas(menu_commit=commits.append),
    ctx,
    pointer_sources=policy,
    commit=lambda a, b: commits.append((a, b)),
)
bones = ui.prop(arm.bones, "active", text="Bone")
nodes = ui.prop(tree.nodes, "active", text="Node")
search = ui.prop_search(arm.bones, "active", arm, "bones", text="Find Bone")
ui.canvas.arrange(560)
clip = (0, 0, 560, 520)


def open_field(control):
    ui.canvas.cancel()
    a, b, w, h = control.rect
    assert ui.canvas.event(
        NS(type="LEFTMOUSE", value="PRESS"), a + 12, b + 12, clip, context=ctx
    )
    assert ui.canvas.overlay is not None, ui.canvas.menu_error
    return ui.canvas.overlay["widget"]


for control, collection in ((bones, arm.bones), (nodes, tree.nodes)):
    w = open_field(control)
    assert w.select(collection[1].as_pointer()) is True
    assert collection.active == collection[1] and ui.canvas.overlay is None
    assert control.options["pointer_field"].label() == collection[1].name
    paths = control.binding.context.paths()
    assert paths[0] in ("bones.active", "nodes.active"), paths
    assert control.binding.context.editable()
checks.append(
    "Collection-owned Bone and Node pointer selection, labels, RNA paths and exact host commits"
)
assert len(commits) == 2
w = open_field(search)
assert w.select(arm.bones[2].as_pointer()) and arm.bones.active == arm.bones[2]
checks.append(
    "Collection search intersects explicit non-ID policy with the search collection"
)

for control, collection in (
    (bones, arm.bones),
    (search, arm.bones),
    (nodes, tree.nodes),
):
    before = collection.active
    w = open_field(control)
    key = collection[0].as_pointer()
    # Revision-only change rejects even unchanged addresses/labels.
    generation[0] += 1
    assert not w.select(key) and collection.active == before
    assert ui.canvas.overlay is not None
    w = open_field(control)
    # Label/structure changes are also checked even without a revision bump.
    collection[0].name += " renamed"
    assert not w.select(key) and collection.active == before
    # Failed host callback restores original pointer and keeps typed editing.
    w = open_field(control)
    old_commit = control.binding.commit

    def reject(a, b):
        setattr(collection[0], state_name, not selection_before[0])
        raise RuntimeError("Rejected pointer transaction")

    control.binding.commit = reject
    state_name = "select" if hasattr(collection[0], "select") else "use_deform"
    setattr(collection[0], state_name, False)
    selection_before = [getattr(item, state_name) for item in collection]
    from beyond_ui.editing import Text

    w.text_edit = Text(collection[0].name)
    w.query = collection[0].name
    w._filter()
    w.capturing = True
    assert w._accept() is False
    assert collection.active == before and w.text_edit is not None
    assert [getattr(item, state_name) for item in collection] == selection_before
    control.binding.commit = old_commit
checks.append(
    "Host revision, structural rename and rejected-commit guards preserve pointer, host snapshot and pending editor"
)

# Full field menu works on collection owners, including copy paths.
ui.canvas.cancel()
assert ui.canvas.open_context(bones, 20, 20, clip, context=ctx), ui.canvas.menu_error
assert (
    ui.canvas.context_menu.target.binding.context.owner().bl_rna.identifier
    == "ArmatureBones"
)
clipboard = NS(window_manager=NS(clipboard=""))
bones.binding.context.execute("PATH", None, clipboard)
assert clipboard.window_manager.clipboard == "bones.active"
ui.canvas.cancel()

# Context copy must revalidate membership, not merely a still-live wrapper.
w = open_field(nodes)
key = tree.nodes[1].as_pointer()
index = next(i for i, item in enumerate(w.items) if item[0] == key)
hit = target(w, nodes.key, 40, 147 + index * 70 + 10)
rows = hit.payload(hit, ctx)
clipboard = NS(window_manager=NS(clipboard="Original"))
assert rows[1].action(hit, clipboard) is True
assert clipboard.window_manager.clipboard == tree.nodes[1].name
tree.nodes.remove(tree.nodes[0])
assert rows[1].action(hit, clipboard) is False
assert clipboard.window_manager.clipboard == "Second"
assert w.select(key) is False
checks.append(
    "Candidate right-click Copy Name and Select reject stale structural snapshots"
)

# Clear rejects stale generations too, then supports one fresh transactional clear.
model = bones.options["pointer_field"]
entry = model.clear_entry()
generation[0] += 1
try:
    entry.action(None, ctx)
except ReferenceError:
    pass
else:
    raise AssertionError("Stale clear accepted")
model.clear_entry().action(None, ctx)
assert arm.bones.active is None
checks.append(
    "Clear respects nullability, host generation and transactional property owner"
)

# No implicit candidate policy for a non-ID field.
for sources in (
    None,
    lambda o, p: PointerItems(lambda: o),
    lambda o, p: PointerItems(lambda: o, revision=lambda: 0),
):
    try:
        Layout(context=ctx, pointer_sources=sources).prop(arm.bones, "active")
    except UnsupportedControl:
        pass
    else:
        raise AssertionError("Non-ID policy without generation admitted")
# Draw-facing reads never enumerate a candidate collection.
w = open_field(nodes)
model = nodes.options["pointer_field"]
from dataclasses import replace

original = model.policy
model.policy = replace(
    original, items=lambda: (_ for _ in ()).throw(AssertionError("Paint scan"))
)
for _ in range(100):
    model.label()
    w.selected()
    assert w.valid(tree.nodes[0].as_pointer())
model.policy = original
ui.canvas.cancel()
ui.canvas.animation.enabled = False
ui.canvas.invalidate()
assert ui.canvas.overlay is None and not ui.canvas.advance_animations()
checks.append(
    "Explicit revision policy admission, zero candidate scans in paint-facing reads and quiescent teardown"
)
# Public temp_override converts collection wrappers to lists. Do not claim
# native button-pointer callback parity for these owners; host providers retain
# the exact binding owner and can supply custom actions directly.
from beyond_ui.context_extensions import collect

observed = []


def extension_callback(self, context):
    observed.append(isinstance(context.button_pointer, list))


assert collect(ctx, bones.binding.context, [extension_callback]) == []
assert observed == [True]
checks.append(
    "Native collection button-pointer override becomes a list; callback parity remains explicitly unsupported"
)
bpy.data.node_groups.remove(tree)
assert not nodes.binding.valid() and not nodes.binding.context.valid()
checks.append("Deleted containing ID invalidates collection-owned bindings")
result = dict(passed=True, version=bpy.app.version_string, checks=checks)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print("NON_ID_POINTERS", result)
