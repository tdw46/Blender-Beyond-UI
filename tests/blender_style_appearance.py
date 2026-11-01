"""Real routed CamKeys dialog: preset edits, owner menus, Cancel and teardown."""

import bpy, gpu, importlib.util, os, sys, json, traceback, time
from pathlib import Path

source = Path(os.environ["BEYOND_UI_CAMKEYS_ROOT"])
spec = importlib.util.spec_from_file_location(
    "camkeys_qa", source / "__init__.py", submodule_search_locations=[str(source)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
state = {"step": 0}
checks = []


def current():
    return next(iter(addon.__beyond_ui_integration__.router.dialogs.values()))


def event(kind="MOUSEMOVE", value="NOTHING", point=None):
    x, y = point or (region.width / 2, region.height / 2)
    window.event_simulate(
        type=kind, value=value, x=int(region.x + x), y=int(region.y + y)
    )


def click(control, button="LEFTMOUSE"):
    d = current()
    x, y, _, _ = d.host.canvas.overlay["rect"]
    a, b, w, h = control.rect
    s = d.host.scale
    pt = ((x + a + w / 2) * s, region.height - (y + b + h / 2) * s)
    event(point=pt)
    event(button, "PRESS", pt)
    event(button, "RELEASE", pt)


CAPTURE = os.environ.get("BEYOND_UI_STYLE_CAPTURE")
handle = None
if CAPTURE:
    OUT = Path(CAPTURE)
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from capture_controls import png

    state.update(frames=[], last_capture=0)


def capture():
    if bpy.context.region.as_pointer() != region.as_pointer():
        return
    if time.monotonic() - state["last_capture"] < 0.045:
        return
    try:
        d = current()
        if not d.host.canvas.overlay:
            return
        x, y, w, h = d.host.canvas.overlay["rect"]
        s = d.host.scale
        # Fixed viewport crop keeps style-size changes comparable; real GPU pixels.
        box = state.setdefault(
            "capture_box",
            (
                max(0, int(x * s) - 12),
                max(0, int(region.height - (y + h) * s) - 12),
                min(region.width, int(w * s) + 24),
                min(region.height, int(h * s) + 24),
            ),
        )
        x, y, w, h = box
        w = min(w, region.width - x)
        h = min(h, region.height - y)
        px = gpu.state.active_framebuffer_get().read_color(x, y, w, h, 4, 0, "UBYTE")
        px.dimensions = w * h * 4
        name = f"frame-{len(state['frames']):03d}.png"
        png(OUT / name, w, h, bytes(px))
        state["frames"].append(
            dict(file=name, step=state["step"], time=time.monotonic())
        )
        state["last_capture"] = time.monotonic()
    except StopIteration:
        pass
    except Exception:
        state["capture_error"] = traceback.format_exc()


def finish(error=None):
    if handle:
        bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
    if CAPTURE:
        (OUT / "frames.json").write_text(json.dumps(state.get("frames", []), indent=2))
        error = error or state.get("capture_error")
    try:
        addon.unregister()
    except Exception:
        error = (error or "") + traceback.format_exc()
    Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
        json.dumps(
            dict(
                passed=error is None,
                checks=checks,
                error=error,
                version=bpy.app.version_string,
            ),
            indent=2,
        )
    )
    bpy.ops.wm.quit_blender()


def tick():
    global handle
    try:
        n = state["step"]
        sheet = addon.ui_theme.STUDIO
        if n == 0:
            addon.register()
            state["original"] = sheet.to_dict()
            with bpy.context.temp_override(window=window, area=area, region=region):
                assert bpy.ops.camkeys.ui_appearance("INVOKE_DEFAULT") == {
                    "RUNNING_MODAL"
                }
            if CAPTURE:
                handle = bpy.types.SpaceView3D.draw_handler_add(
                    capture, (), "WINDOW", "POST_PIXEL"
                )
        elif n == 1:
            d = current()
            assert d.canvas.theme.stylesheet is sheet
            record = d.host.records[d.host.key]
            assert record.get("backdrop")
            d.operator.opacity = 0.65
            d.operator.size = 12
            d.operator.motion = False
            d.operator.accent = (0.2, 0.65, 0.9)
            d.changed(None, None)
            event()
        elif n == 2:
            d = current()
            assert d.host.canvas.overlay is not None
            assert abs(sheet.to_dict()["opacity"] - 0.65) < 1e-6
            assert not sheet.animation.enabled and d.canvas.theme.font_size == 12
            primary = sheet.to_dict()["variants"]["primary"]["field"]
            assert all(abs(a-b) < 1e-6 for a, b in zip(primary[:3], (0.2, 0.65, 0.9)))
            variants = sheet.to_dict()["variants"]
            assert all(abs(a-b) < 1e-6 for a, b in zip(
                variants["coral_action"]["field"][:3], d.operator.accent))
            assert all(abs(a-b) < 1e-6 for a, b in zip(
                variants["mint_action"]["selected"][:3], d.operator.mint))
            checks.append("Live accent also updates primary action buttons")
            checks.append("Reset and selected ON/OFF presets follow live coral/mint edits")
            checks.append(
                "Live opacity, type size and disable retain dialog and shared glass"
            )
            c = next(
                c for c in d.canvas.controls.values() if c.label == "Surface Opacity"
            )
            click(c, "RIGHTMOUSE")
        elif n == 3:
            d = current()
            assert (
                d.canvas.context_menu
                and d.canvas.context_menu.target.binding.context.name == "opacity"
            )
            checks.append("Exact-owner Appearance property right-click")
            event("ESC", "PRESS")
            event("ESC", "RELEASE")
        elif n == 4:
            d = current()
            d.operator.blender_colors = True
            d.changed(None, None)
            event()
        elif n == 5:
            assert sheet.to_dict()["colors"] == {} and sheet.to_dict()["surfaces"] == {}
            checks.append("Blender color inheritance restored live")
            click(current().canvas.controls["cancel"])
        elif n == 6:
            assert not addon.__beyond_ui_integration__.router.dialogs
            assert sheet.to_dict() == state["original"], (
                "Cancel must restore entire preset"
            )
            checks.append(
                "Cancel restores colors, metrics, opacity and motion atomically"
            )
            finish()
            return None
        state["step"] += 1
        area.tag_redraw()
        return 0.6
    except Exception:
        finish(traceback.format_exc())
        return None


bpy.app.timers.register(tick, first_interval=1)
