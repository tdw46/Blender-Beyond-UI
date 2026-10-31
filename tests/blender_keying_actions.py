"""Scene keying sets and exact animation-channel context actions."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target
from beyond_ui.decorator import channel_collections


def run():
    ctx, commits = bpy.context, []
    obj, scene = ctx.object, ctx.scene
    binding = rna_binding(lambda: obj, "location", index=1)
    source = binding.context
    target = Target("Y", binding=binding, valid=source.valid, commit=commits.append)

    def menu(t=target):
        return Menu(t, source.entries(t, ctx), (0, 0), (0, 0, 640, 700), context=ctx)

    def choose(key, m=None):
        m = m or menu()
        index = next(i for i, row in enumerate(m.page.rows) if row.key == key)
        assert m.page.available[index], (key, m.error)
        m.choose(index, ctx)
        assert m.error is None, m.error
        return m

    def reject(key):
        raise RuntimeError("rejected")

    rejected = Target("Y", binding=binding, valid=source.valid, commit=reject)
    m = menu(rejected)
    m.choose(next(i for i, r in enumerate(m.page.rows) if r.key == "KEYING_ADD"), ctx)
    assert m.error == "rejected" and len(scene.keying_sets) == 0
    choose("KEYING_ADD")
    ks = scene.keying_sets.active
    assert len(ks.paths) == 1 and ks.paths[0].array_index == 1
    assert ks.paths[0].id == obj and ks.paths[0].data_path == "location"
    before = len(commits)
    choose("KEYING_ADD")
    assert len(ks.paths) == 1 and len(commits) == before
    m = menu(rejected)
    m.choose(
        next(i for i, r in enumerate(m.page.rows) if r.key == "KEYING_REMOVE"), ctx
    )
    assert m.error == "rejected" and len(ks.paths) == 1 and ks.paths[0].array_index == 1
    choose("KEYING_REMOVE")
    assert not ks.paths
    choose("KEYING_ADD_ALL")
    assert len(ks.paths) == 1 and ks.paths[0].use_entire_array
    choose("KEYING_REMOVE")
    assert not ks.paths
    old = menu()
    other = scene.keying_sets.new(idname="Other", name="Other")
    scene.keying_sets.active = other
    old.choose(
        next(i for i, r in enumerate(old.page.rows) if r.key == "KEYING_ADD"), ctx
    )
    assert not ks.paths and not other.paths

    obj.location = (3, 4, 5)
    choose("KEY_ALL")
    collections, _ = channel_collections(obj)
    assert sum(len(c) for c in collections) == 3
    scene.frame_set(20)
    obj.keyframe_insert("location", index=1)
    choose("CLEAR_KEYS")
    collections, _ = channel_collections(obj)
    assert {f.array_index for c in collections for f in c} == {0, 2}
    choose("CLEAR_KEYS_ALL")
    assert not any(channel_collections(obj)[0])
    choose("RESET_ALL")
    assert tuple(obj.location) == (0, 0, 0)
    no_undo = Target("Y", binding=binding, valid=source.valid)
    m = menu(no_undo)
    assert not any(
        enabled
        for row, enabled in zip(m.page.rows, m.page.available)
        if row.key.startswith("KEYING_") or row.key == "CLEAR_KEYS_ALL"
    )
    return dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Create keying set on first add; rejected creation removes only the owned set",
            "Exact component and whole-array paths; repeat add skips commit",
            "Rejected remove restores path; changing active set revokes stale menu",
            "Insert all and clear single/all channels preserve sibling animation",
            "All-component reset and host-undo availability",
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
