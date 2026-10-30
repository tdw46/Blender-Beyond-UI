# Automated testing without taking focus

Tyler's requirement is to preserve the app they are using. A test may create a
Blender window when necessary, but must not activate it, raise it over their work
or redirect their desktop input.

`tools/run_blender_tests.py` uses `--background` by default. For tests requiring a
graphics window, `--windowed` now adds Blender's **`--no-window-focus`** before the
Python script argument. The runner checks the executable's `--help` first and
refuses a windowed launch if the flag is unavailable. There is no foreground
fallback. Disposable config/scripts/extensions directories protect live state.
Timeout cleanup kills only the child started by that invocation. Old success
markers are removed before each run; success still requires a fresh result,
zero process exit and no traceback.

```sh
# RNA and nonvisual execution tests: no window.
uv run python tools/run_blender_tests.py \
  --blender '/Applications/Blender 5.2.2.app/Contents/MacOS/Blender' \
  --fixture tests/blender_sizing.py

# GPU or actual N-panel tests: a window, without activating Blender.
uv run python tools/run_blender_tests.py --windowed \
  --blender '/Applications/Blender 5.2.2.app/Contents/MacOS/Blender' \
  --fixture tests/blender_sizing_windowed.py
```

The capture fixtures read actual GPU offscreen framebuffers and save PNGs/GIF
frames. They do not require a desktop screenshot or foreground Blender window.
Panel fixtures use Blender's `--enable-event-simulate` and internal test events;
they do not move the user's pointer or type into their current application.

## Verification on this Mac — 2026-10-30

Six production GPU captures (1×, 1.5× and 2× on each installed version) and two
N-panel mouse/keyboard fixtures passed on Blender **5.1.2 and 5.2.2**. A separate
AppKit monitor watched application-activation notifications and sampled the
foreground PID every 10 ms for the entire 51.5-second batch. It observed no
activation events and the same non-Blender foreground app throughout. Test PIDs
were absent from every foreground observation. This verifies these launch,
capture and panel paths; it is not a guarantee about arbitrary future scripts.

A subsequent complete layout-sizing batch passed all **42 test processes** over
129 seconds with the same result: no activation events, no observed foreground
test PID and the same unrelated app in focus. Its
[launch-by-launch record](design/qa/layout-sizing-v1/focus.json) includes headless
tests, GPU benchmarks, captures and the existing interaction regression suite.

The [audit record](design/qa/background-testing-v1/audit.json) contains owned PIDs,
commands, return codes and observations. The reproducible monitor is
[`tools/monitor_focus_macos.swift`](../tools/monitor_focus_macos.swift). It only
observes focus; it never activates apps or restores a previously focused app.

```sh
mkdir -p build/focus-audit
xcrun swiftc tools/monitor_focus_macos.swift -o build/focus-audit/monitor
BEYOND_UI_QA_ONLY=capture,windowed build/focus-audit/monitor \
  build/focus-audit/focus.json /usr/bin/env uv run python tools/run_sizing_qa.py
```

Compare each runner summary's `pid` with both the monitor's activation-event PIDs
and `sampled_frontmost_pids`; any test-process activation fails the focus audit.
User-initiated switching between unrelated apps is allowed. Recheck when changing
Blender builds, platforms or window workflows, including creation of additional
windows. This monitor is a development tool, never a production UI polling loop.

## Evidence and limits

Both installed executables advertise “Open behind other windows and without
taking focus.” Official source confirms the option sets the initial window-focus
policy and guards macOS application activation: [argument handler](https://raw.githubusercontent.com/blender/blender/d13f752e3b9c/source/creator/creator_args.cc)
and [Cocoa launch handler](https://raw.githubusercontent.com/blender/blender/d13f752e3b9c/intern/ghost/intern/GHOST_SystemCocoa.mm).
The option also exists in the [Blender 4.2 source](https://raw.githubusercontent.com/blender/blender/v4.2.0/source/creator/creator_args.cc);
4.2 runtime behavior and other platforms were not exercised here. Exact 4.2,
5.1 and 5.2 Manual argument pages were requested but unavailable from the web
fetcher, so they are not counted as validation.

Do not substitute `open -g` alone, minimizing after launch or restoring focus
afterward: none establishes that the user was never interrupted. Do not activate
Blender as a workaround. A test that actually requires foreground input stays
unverified until Tyler explicitly authorizes foreground testing. Continue the
remaining safe tests and preserve unrelated Blender sessions.
