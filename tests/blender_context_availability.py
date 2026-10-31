"""Exact-channel animation removal and stale-menu checks; background only."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Menu, Target


def run():
    ctx = bpy.context
    owner = ctx.active_object
    owner.animation_data_clear()
    commits = []

    def subject(index):
        binding = rna_binding(lambda: owner, "location", index=index)
        return binding.context, Target(
            "location",
            binding=binding,
            valid=binding.context.valid,
            commit=commits.append,
        )

    y, target = subject(1)
    whole, whole_target = subject(None)

    def menu(source=y, target=target):
        return Menu(
            target, source.entries(target, ctx), (0, 0), (0, 0, 640, 900), context=ctx
        )

    def available(m, key):
        m.refresh(ctx)
        return m.page.available[
            next(i for i, row in enumerate(m.page.rows) if row.key == key)
        ]

    def choose(m, key):
        m.choose(next(i for i, row in enumerate(m.page.rows) if row.key == key), ctx)
        assert m.error is None, m.error

    empty = menu()
    assert not available(empty, "DELETE_KEY")
    assert not available(empty, "REMOVE_DRIVER")
    ctx.scene.frame_set(10, subframe=0.5)
    owner.keyframe_insert(data_path="location", index=0, frame=10.5)
    assert not available(empty, "DELETE_KEY"), "Sibling key must not enable Y"
    assert available(menu(whole, whole_target), "DELETE_KEY")
    choose(menu(), "KEY")
    assert available(menu(), "DELETE_KEY")
    assert commits == ["KEY"]
    ctx.scene.frame_set(11)
    assert not available(menu(), "DELETE_KEY"), "Other frame must not enable removal"
    ctx.scene.frame_set(10, subframe=0.5)
    choose(menu(), "DELETE_KEY")
    assert commits == ["KEY", "DELETE_KEY"]
    assert not available(menu(), "DELETE_KEY")
    assert available(menu(whole, whole_target), "DELETE_KEY"), "Sibling X survives"

    owner.keyframe_insert(data_path="location", index=1, frame=10.5)
    stale = menu()
    owner.keyframe_delete(data_path="location", index=1, frame=10.5)
    choose(stale, "DELETE_KEY")
    assert not stale.closed and commits == ["KEY", "DELETE_KEY"]
    y.execute("DELETE_KEY", target, ctx)
    assert commits == ["KEY", "DELETE_KEY"], "Direct stale delete is a no-op"

    # Empty FCurves are still animation channels: clear Y before adding a driver.
    choose(menu(), "CLEAR_KEYS")
    owner.driver_add("location", 0)
    assert not available(menu(), "REMOVE_DRIVER"), "Sibling driver must not enable Y"
    assert available(menu(whole, whole_target), "REMOVE_DRIVER")
    choose(menu(), "DRIVER")
    assert available(menu(), "REMOVE_DRIVER")
    stale = menu()
    owner.driver_remove("location", 1)
    before = list(commits)
    choose(stale, "REMOVE_DRIVER")
    y.execute("REMOVE_DRIVER", target, ctx)
    assert not stale.closed and commits == before
    owner.driver_add("location", 1)
    choose(menu(), "REMOVE_DRIVER")
    assert owner.animation_data.drivers.find("location", index=0) is not None
    assert owner.animation_data.drivers.find("location", index=1) is None

    no_undo = Target("no undo", binding=target.binding, valid=y.valid)
    locked = Target(
        "locked",
        binding=target.binding,
        valid=y.valid,
        commit=commits.append,
        editable=lambda: False,
    )
    for restricted in (no_undo, locked):
        m = menu(y, restricted)
        assert all(
            not available(m, key)
            for key in ("KEY", "DELETE_KEY", "DRIVER", "REMOVE_DRIVER")
        )
    return dict(
        passed=True,
        version=bpy.app.version_string,
        build=bpy.app.build_hash.decode(),
        checks=[
            "Empty/sibling channels disable destructive animation actions",
            "Whole-array menus include applicable sibling channels",
            "Insert/delete use exact subframe; other frames stay disabled",
            "Open menus revalidate removed channels and skip host commits",
            "Direct stale removal is a no-op; sibling animation survives",
            "Missing host undo and locked controls disable animation actions",
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
