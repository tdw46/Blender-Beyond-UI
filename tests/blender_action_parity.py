import bpy, json, os, sys, traceback
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import action_parity_fixture as f
from beyond_ui import Layout


def run():
    checks = []
    try:
        f.register()
        context = bpy.context
        ui = f.build(context)
        canvas = ui.canvas
        clip = (0, 0, 560, 600)
        now = [0.0]
        hold = next(c for c in canvas.controls.values() if c.options.get("hold_menu"))
        hold.motion.clock = lambda: now[0]

        def send(c, kind, value="PRESS"):
            x, y, w, h = c.rect
            return canvas.event(
                NS(type=kind, value=value), x + w / 2, y + h / 2, clip, context=context
            )

        from beyond_ui.context_menu import Entry

        observed = []
        canvas.context_provider = lambda target, ctx: (
            Entry("HOST_ACTION", "Host Action", lambda t, c: observed.append(t.key)),
        )
        assert canvas.open_context(hold, 20, hold.rect[1] + 2, clip, context=context)
        menu = canvas.context_menu
        host_index = next(
            i for i, r in enumerate(menu.page.rows) if r.key == "HOST_ACTION"
        )
        assert sum(r.key == "HOST_ACTION" for r in menu.page.rows) == 1
        menu.choose(host_index, context)
        assert observed == [hold.key]
        canvas.cancel()
        assert canvas.open_context(hold, 20, hold.rect[1] + 2, clip, context=context)
        menu = canvas.context_menu
        host_index = next(
            i for i, r in enumerate(menu.page.rows) if r.key == "HOST_ACTION"
        )
        canvas.controls.pop(hold.key)
        menu.choose(host_index, context)
        assert observed == [hold.key]
        canvas.controls[hold.key] = hold
        canvas.cancel()
        canvas.context_provider = None
        checks.append(
            "Host operator context contributions appear once and reject removed exact owners"
        )
        send(hold, "LEFTMOUSE")
        assert not f.calls
        now[0] = 0.1
        send(hold, "LEFTMOUSE", "RELEASE")
        assert f.calls == [1]
        send(hold, "LEFTMOUSE")
        now[0] += 0.201
        canvas.advance_animations(context=context)
        assert canvas.context_menu
        send(hold, "LEFTMOUSE", "RELEASE")
        assert f.calls == [1]
        canvas.context_menu.choose(0, context)
        assert f.calls == [1, 2]
        canvas.cancel()
        send(hold, "LEFTMOUSE")
        f.allowed = False
        now[0] += 0.3
        canvas.advance_animations(context=context)
        send(hold, "LEFTMOUSE", "RELEASE")
        assert f.calls == [1, 2] and not canvas.context_menu
        f.allowed = True
        checks.append(
            "Quick release dispatch, 200ms hold menu, release suppression and changed-poll rejection"
        )
        opener = next(
            c for c in canvas.controls.values() if c.options.get("panel_model")
        )

        def popup():
            canvas.cancel()
            assert canvas.open_panel(opener, clip, context), canvas.menu_error
            return canvas.overlay["widget"]

        p = popup()
        cancel = next(
            c for c in p.canvas.controls.values() if c.label == "Keep Editing"
        )
        x, y, w, h = cancel.rect
        p.dispatch(NS(type="LEFTMOUSE", value="PRESS"), x + 5, y + 5, context=context)
        assert canvas.overlay
        p.dispatch(NS(type="LEFTMOUSE", value="RELEASE"), x + 5, y + 5, context=context)
        assert not canvas.overlay and f.calls == [1, 2]
        p = popup()
        p.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        assert not canvas.overlay and f.calls == [1, 2, 3]
        f.result = "CANCELLED"
        p = popup()
        p.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        assert canvas.overlay
        f.result = "FINISHED"
        f.cancel_default = True
        p = popup()
        before = list(f.calls)
        p.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        assert not canvas.overlay and f.calls == before
        f.cancel_default = False
        try:
            Layout(context=context).template_popup_confirm("bui.parity_action")
            raise AssertionError("Accepted unowned confirmation")
        except ValueError:
            pass
        checks.append(
            "Owned popup confirm/cancel on matching release, Return default, Cancel-default and CANCELLED retention"
        )
        c = next(c for c in canvas.controls.values() if c.label == "Animated status")
        assert c.options["status"] == "EMPTY"
        context.active_object.keyframe_insert("location", index=0)
        canvas.refresh_status(clip)
        assert c.options["status"] == "KEYED"
        assert next(
            c for c in canvas.controls.values() if c.label == "Alert field"
        ).options["alert"]
        assert (
            next(
                c for c in canvas.controls.values() if c.label == "Unembossed field"
            ).options["emboss"]
            == "NONE"
        )
        checks.append(
            "Normal/none/status/alert flags reach ordinary Canvas controls; keyed status refreshes outside paint"
        )
        c = next(c for c in canvas.controls.values() if c.label == "Shortcut")
        before = f.item.to_string()
        send(c, "LEFTMOUSE")
        assert f.item.to_string() == before and not canvas.context_menu
        assert before and c.options["label_get"]() == "Shortcut  " + before
        canvas.cancel()

        class ClipboardContext:
            window_manager = NS(clipboard="")

            def __getattr__(self, name):
                return getattr(context, name)

        copy_context = ClipboardContext()
        shortcut_calls = []
        canvas.context_provider = lambda target, ctx: (
            Entry(
                "HOST_SHORTCUT",
                "Host shortcut action",
                lambda t, c: shortcut_calls.append(t.key),
            ),
        )
        canvas.context_focus = c
        x, y, w, h = c.rect
        assert canvas.event(
            NS(type="APP", value="PRESS"), x + 2, y + 2, clip, context=copy_context
        )
        menu = canvas.context_menu
        keys = [r.key for r in menu.page.rows]
        assert keys.count("COPY_SHORTCUT") == keys.count("HOST_SHORTCUT") == 1, keys
        assert {"PATH", "FULL_PATH"}.issubset(keys), keys
        menu.choose(keys.index("COPY_SHORTCUT"), copy_context)
        assert copy_context.window_manager.clipboard == before
        canvas.cancel()
        assert canvas.open_context(c, x + 2, y + 2, clip, context=copy_context)
        canvas.context_menu.choose(next(i for i, row in enumerate(canvas.context_menu.page.rows) if row.key == "HOST_SHORTCUT"), copy_context)
        assert shortcut_calls == [c.key]
        canvas.cancel()
        assert canvas.open_context(c, x + 2, y + 2, clip, context=copy_context)
        stale = canvas.context_menu
        f.config.keymaps[0].keymap_items.remove(f.item)
        stale.choose(next(i for i, row in enumerate(stale.page.rows) if row.key == "HOST_SHORTCUT"), copy_context)
        assert shortcut_calls == [c.key]
        canvas.context_provider = None
        canvas.cancel()
        assert not c.enabled
        assert not canvas.advance_animations(context=context)
        checks.append(
            "Shortcut keyboard context, isolated copy, host action and stale keymap rejection"
        )
        opener = next(
            c for c in canvas.controls.values() if c.label == "Transform Components"
        )
        assert canvas.open_panel(opener, clip, context), canvas.menu_error
        p = canvas.overlay["widget"]
        values = [c for c in p.canvas.controls.values() if c.kind == "number"]
        assert len(values) == 3
        c = values[1]
        p.canvas._begin(c)
        p.canvas.editor = __import__("beyond_ui.editing", fromlist=["Text"]).Text(
            "2.5m"
        )
        p.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        assert abs(context.active_object.location.y - 2.5) < 1e-6
        assert canvas.overlay and p.canvas.edit is None
        assert p.canvas.open_context(c, c.rect[0], c.rect[1], p.clip, context=context)
        assert p.canvas.context_menu.target.binding.context.index == 1
        p.canvas.close_context()
        p.canvas._begin(c)
        p.canvas._write(8)
        p.dispatch(
            NS(type="RIGHTMOUSE", value="PRESS"),
            c.rect[0] + 2,
            c.rect[1] + 2,
            context=context,
        )
        assert abs(context.active_object.location.y - 2.5) < 1e-6 and canvas.overlay
        canvas.cancel()
        enum = next(
            c for c in canvas.controls.values() if c.label == "Format Components"
        )
        assert canvas.open_panel(enum, clip, context), canvas.menu_error
        p = canvas.overlay["widget"]
        assert p.canvas.active.options.get("search_bar")
        assert p.canvas.active.label == "", (
            "Search uses an icon/placeholder, not an embedded property label"
        )
        unfiltered_height = p.height
        p.canvas.editor.insert("jpeg")
        p.dispatch(NS(type="RET", value="PRESS"), 0, 0, context=context)
        assert p.height < unfiltered_height
        assert any(
            c.options.get("search_bar") for c in p.canvas.visible_controls(p.clip)
        )
        assert not any(
            c.label.startswith("OpenEXR") for c in p.canvas.visible_controls(p.clip)
        )
        jpeg = next(
            c
            for c in p.canvas.controls.values()
            if c.binding and getattr(c.binding.context, "enum_value", None) == "JPEG"
        )
        p.focus.reveal(jpeg)
        x, y, w, h = jpeg.rect
        p.dispatch(
            NS(type="LEFTMOUSE", value="PRESS"), x + w / 2, y + h / 2, context=context
        )
        assert (
            context.scene.render.image_settings.file_format == "JPEG" and canvas.overlay
        )
        canvas.cancel()
        assert canvas.open_panel(opener, clip, context)
        stale = canvas.overlay["widget"]
        bpy.data.objects.remove(context.active_object, do_unlink=True)
        stale.dispatch(NS(type="LEFTMOUSE", value="PRESS"), 20, 20, context=context)
        assert not canvas.overlay and not opener.enabled
        checks.append(
            "Component popups edit vector and enum values without dismissing; indexed context, right-cancel rollback and deleted owner rejection"
        )
        result = dict(passed=True, version=bpy.app.version_string, checks=checks)
    except Exception:
        result = dict(passed=False, error=traceback.format_exc(), checks=checks)
    finally:
        f.unregister()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


run()
