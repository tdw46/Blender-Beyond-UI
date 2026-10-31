# Automated testing without taking focus

## Standing authorization and known focus limitation — 2026-10-30

Tyler gives standing authorization to use no-focus launched Blender windows
whenever needed, without asking again for each run. This supersedes the previous
one-time exception and blanket suspension. `docs/WINDOWED_TEST_STATUS.json`
admits windowed tests on the basis of this authorization, not a claim that focus
safety has been requalified. Background tests remain the default when possible;
the runner still requires `--no-window-focus` and provides no foreground fallback.

The marking-menu 5.2.2 capture observed owned test PID 35515 become frontmost
despite the advertised flag. Tyler confirmed unsolicited focus theft. Preserve
that evidence: successful GPU assertions do not make it a focus-safe run. Continue
focus audits when workflows change, report unexpected activation and investigate
without activating, raising or restoring focus. Deliberate foreground testing
still requires explicit authorization. Historical records:
`design/qa/marking-menu-v1/focus-windowed.json` and
`design/qa/marking-menu-v1/focus-background.json`.

### Action/component capture follow-up

The action-parity v1 final batch has eight passing background processes, four
passing GPU captures and one passing paired-performance probe. All five windowed
processes activated despite the mandatory flag. The [capture focus audit](design/qa/action-parity-v1/focus.json)
and [performance focus audit](design/qa/action-parity-v1/focus-performance.json)
retain exact PIDs and timestamps. No foreground workaround was used; standing
launch authorization remains separate from the unresolved focus-safety failure.

### Latest pie capture follow-up

The v3 windowed batch passed all four GPU fixtures and both N-panel input fixtures.
Its three 5.2.2 GPU captures had no observed test-process activation, but the 5.1.2
capture and both N-panel fixtures activated their test processes. The initial v3
5.2.2 exploratory capture also activated Blender. All used the mandatory no-focus
flag; no activation/raise/focus-restoration workaround was used. Standing launch
authorization remains in effect, but the workflow is not focus-safe qualified.
See [launch records](design/qa/marking-menu-v3/launches.json),
[batch audit](design/qa/marking-menu-v3/focus-windowed.json) and
[initial audit](design/qa/marking-menu-v3/focus-initial.json).
The archived Cocoa source guards initial application activation but its separate
`GHOST_WindowCocoa::setOrder(Top)` path can activate unconditionally. This is a
possible route to investigate, not an established cause of these observations.

The subsequent [v4 nested-menu batch](design/qa/marking-menu-v4/launches.json)
passed six background fixtures, four GPU fixtures and two native N-panel fixtures.
Its [focus audit](design/qa/marking-menu-v4/focus.json) still recorded test-process
activation despite the mandatory flag. Standing no-focus launch authorization
remains in effect; successful execution does not certify focus safety.

The [v5 standalone/hover QA](design/qa/marking-menu-v5/index.html) again used
mandatory no-focus launches with disposable profiles. Its initial capture,
regression batch and final capture refresh have separate immutable audits linked
from the [combined record](design/qa/marking-menu-v5/focus.json). Activation was
still observed; this is not focus-safe qualification. No foreground input or
focus-restoration workaround was used.

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

Do not treat `open -g` alone, minimizing after launch or restoring focus
afterward as proof that the user was never interrupted. Do not activate
Blender as a workaround. A test that actually requires foreground input stays
unverified until Tyler explicitly authorizes foreground testing. Continue the
remaining safe tests and preserve unrelated Blender sessions.

### Core host matrix follow-up

The final core-host matrix passed four N-panel/Properties processes on 5.1.2/5.2.2
with no observed test-process activation. Earlier fixture attempts did activate
Blender; all audit files are retained in `design/qa/core-hosts-v1/`. This successful
run does not erase earlier focus failures or establish general platform safety.

## macOS LaunchServices capture path (2026-10-30)

Direct subprocess launches again activated Blender in all five initial
`build/macos-controls-v1` runs despite the flag. Tyler confirmed the interruption
and explicitly authorized finding a nonactivating launch or restoring the old
app afterward. Web research used Apple's
[OpenConfiguration](https://developer.apple.com/documentation/appkit/nsworkspace/openconfiguration)
and [NSRunningApplication](https://developer.apple.com/documentation/appkit/nsrunningapplication)
documentation.

`tools/launch_blender_macos.swift` opens a new owned instance with
`NSWorkspace.OpenConfiguration.activates=false`, forwards the checked Blender
flag and disposable environment, and records activation events. Compile it with
`swiftc tools/launch_blender_macos.swift -o build/focus-audit/launch-blender`; pass
`--macos-noactivate` to `tools/run_blender_tests.py`. No desktop input is injected.
The runner uses absolute fixture/result paths because LaunchServices does not
inherit the shell working directory. A first probe exposed that relative-path
error; its owned PID was terminated, and its evidence is retained.

The optional restoration is bounded to eight seconds and three requests, targets
the latest non-owned app, and runs only if the owned Blender is foreground. It
never deliberately activates Blender. Activation still fails the no-interruption
audit even if restoration succeeds. LaunchServices does not supply a child exit
status: the runner requires a fresh successful fixture result and checks logs,
helper errors and timeout. The reported helper exit is not Blender's exit code.

The five-run `build/macos-controls-final` matrix completed with no Blender
activation and zero restoration requests. The new spacing matrix and reference
capture have their own audit records in the new QA report. Earlier failures are
not erased; other builds, additional windows and platforms require revalidation.

### Current helper policy — override/default pass

The latest supplied AGENTS instruction prohibits focus restoration as a workaround.
The LaunchServices helper now only observes activation; the prior optional restore
code is removed. `activates=false`, `--no-window-focus`, fresh-instance launch,
disposable profiles and owned-process cleanup remain. Both final native-adapter
runs on 5.1.2/5.2.2 observed no activation, with only Codex in the foreground.
Evidence: `design/qa/context-overrides-v1/focus.json`. Earlier restoration capability
and launch observations above are historical, not the current helper policy.
