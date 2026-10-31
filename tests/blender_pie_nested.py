"""Background RNA checks for nested navigation and compound layout arguments."""

import bpy, json, os, sys, traceback, hashlib
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import pie_nested_fixture as fixture
import pie_fixture
from beyond_ui.pie_menu import PieMenu


def run():
    checks = []
    try:
        assert bpy.app.background
        fixture.register()
        ctx = bpy.context
        canvas, opener = fixture.build(ctx)
        clip = (0, 0, 1200, 900)

        def open():
            canvas.cancel()
            assert canvas.open_operator_menu(opener, clip, ctx, anchor=(600, 450)), (
                canvas.menu_error
            )
            return canvas.context_menu

        def click(label, kind="LEFTMOUSE"):
            menu = canvas.context_menu
            _, (x, y, w, h), _ = next(
                v for v in menu.visible_rows() if v[2].label == label
            )
            canvas.event(
                NS(type=kind, value="PRESS"), x + w / 2, y + h / 2, clip, context=ctx
            )
            if kind == "LEFTMOUSE":
                canvas.event(
                    NS(type=kind, value="RELEASE"),
                    x + w / 2,
                    y + h / 2,
                    clip,
                    context=ctx,
                )

        def key(kind):
            canvas.event(NS(type=kind, value="PRESS"), 0, 0, clip, context=ctx)

        parent = open()
        click("Transform…")
        child = canvas.context_menu
        assert (
            isinstance(child, PieMenu)
            and child.navigation_parent is parent
            and child.layout_mode == "PIE"
        )
        assert len(child.slots.roots) == 3
        click("Resolution", "RIGHTMOUSE")
        assert any(r.key == "FULL_PATH" for r in child.page.rows)
        key("LEFT_ARROW")
        assert child.radial()
        click("Resolution")
        child.editor.text.text = "73"
        key("RET")
        assert ctx.scene.render.resolution_percentage == 73
        before = ctx.scene.render.film_transparent
        click("Transparent")
        assert ctx.scene.render.film_transparent != before
        parent = open()
        click("Transform…")
        child = canvas.context_menu
        click("More Actions")
        assert child.page.search is not None
        key("LEFT_ARROW")
        assert child.radial()
        key("LEFT_ARROW")
        assert canvas.context_menu is parent and not parent.closed
        checks.append(
            "Nested pie, exact property context/edit/toggle, searchable child list and Back retain the correct owners"
        )
        click("Transform…")
        click("Rotate")
        assert (
            pie_fixture.calls[-1] == 202
            and canvas.context_menu is None
            and parent.closed
        )
        checks.append(
            "Release dispatch targets the exact split child and tears down all retained parent menus"
        )
        open()
        click("Transform…")
        fixture.allowed = False
        click("Apply")
        assert canvas.context_menu is None and pie_fixture.calls[-1] == 202
        fixture.allowed = True
        checks.append(
            "Changed registered child poll blocks execution and cancels the chain"
        )
        canvas, opener = fixture.build(ctx, "BUI_MT_nested_list")
        open()
        click("Nested Transform")
        assert isinstance(canvas.context_menu, PieMenu)
        canvas.animation.enabled = False
        assert canvas.context_menu.motion.strength == 0
        key("LEFT_ARROW")
        assert not isinstance(canvas.context_menu, PieMenu)
        canvas.cancel()
        assert not canvas.advance_animations(context=ctx)
        checks.append(
            "Ordinary list to pie navigation inherits live host motion policy and settles without idle work"
        )
        signatures = {}
        for name in (
            "split",
            "column_flow",
            "grid_flow",
            "separator_spacer",
            "separator",
        ):
            signatures[name] = [
                p.identifier
                for p in bpy.types.UILayout.bl_rna.functions[name].parameters
            ]
        result = dict(
            passed=True,
            version=bpy.app.version_string,
            checks=checks,
            signatures=signatures,
            source_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "beyond_ui").rglob("*.py"))
            },
        )
    except Exception:
        result = dict(passed=False, error=traceback.format_exc())
    finally:
        fixture.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("NESTED_PIE", result.get("passed"), result.get("error", ""), flush=True)


if __name__ == "__main__":
    run()
