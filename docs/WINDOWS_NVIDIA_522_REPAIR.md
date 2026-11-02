# Blender 5.2.2 Windows/NVIDIA qualification — 2026-11-02

Tested official Blender 5.2.2 LTS, build `d13f752e3b9c`, RTX 4090 Laptop GPU,
driver 591.74, Windows 11 Home Insider Preview 10.0.26220, 150% display scaling,
Blender UI preference 1.0 (effective 1.5). Vulkan and OpenGL used separate restarted
processes, profiles, and a copy of Uraraka. Native fallback is not acceptance.

## Repairs

* Admit the official Windows MSI executable's exact SHA-256 in addition to the
  existing ZIP executable. Their pre-certificate PE bytes are identical after
  zeroing the checksum and security directory. Runtime still checks full hashes;
  it never guesses compatibility from a version number or normalized image.
* Preserve `template_popup_confirm` operator properties across draw recording and
  replay, including property assignment and cancellation-only return semantics.
* Refuse native popup fallback in background mode or without an interactive window,
  avoiding Blender's native `wm.call_panel` crash and retaining the failure reason.
* Replace the progress-ring shader's reserved GLSL identifier `active` with
  `filledCoverage`. Shader math, Metal path and retained geometry are unchanged.
* Normalize vendor-record paths to POSIX separators and LF on Windows, retaining
  protection against overwriting edited vendor files.
* Use a normal, nonactivating Windows test window, no console, and isolated recovery
  directories. Blender's maximized Windows launch path did not honor no-focus.

The eight Darwin package binaries, executable fingerprints, symbols and backend
declarations are unchanged. Only their shared Python adapter fingerprint and the
catalog hashes changed. Darwin admission still accepts exactly one executable.
No Mac hardware run was possible here; existing Metal evidence is historical.

## Exact Windows signing qualification

* ZIP executable: `c9f9c33e538dd3e195ccb8dcc5986721f49df795e91288d4f6e82295a028e1c1`
* Installed MSI executable: `f141a3c5754500e6f84361099a4cd53f0bb7662b6a0d2cfaaa8fbb63e92234a0`
* Signing-independent image: `87b6ad531a9062c25a8ec71dd1cdb3a4cf052eed3846a8df2fe7f576f03293ca`
* Official ZIP archive: `3849d17a682cba006075aaa3f3597ecb5c9c30ec31035b2e092c53e40679b535`

The ZIP was checked against the official release SHA-256 list. The installed
executable had a valid Blender Foundation Authenticode signature. Of 113,022,936
bytes, 1,695 differ, exclusively in checksum/signing metadata. The reference and
candidate PDB identity is `0f2479ae-9ada-2f8f-4c4c-44205044422e`, age 1.
`tools/qualify_windows_signing_variant.py` reproduces byte-equivalence admission;
after modifying a package manifest, regenerate its catalog SHA-256 as usual.

## Results

417 unit tests passed. Actual NVIDIA Vulkan and OpenGL each passed native renderer
and framebuffer/glass execution; all six CamKeys panel hosts; 30 authored-panel
state combinations; list identities; all three brush curves; custom dialogs and
menus; Appearance/Billboard/Flattened Falloff; sidebar overlap and viewport-backed
glass; nested menus, exact property-owner actions, search and keyboard/Escape;
scroll/offscreen refresh; light/custom themes; and deterministic rendered motion.
Real-RNA numeric, developer paths/tooltips and keying/driver tests also passed.
Wheel and trackpad direction have synthetic-event unit coverage, not physical
trackpad acceptance. No long-duration GPU memory soak was performed.

Uraraka live-output tests changed the view across 30 samples and verified changing
shape keys plus visible list values. The live linking panel was placed in a
fixture-only category so it remained visible. Rendering used Workbench in that
fixture; the copied scene's optional BVT render engine was unavailable in the
clean profile. Other popup captures retain the copied scene layout.

| Measurement | Vulkan | OpenGL |
|---|---:|---:|
| Warm author callback median / p95 | 4.68 / 9.33 ms | 2.17 / 4.55 ms |
| Warm paint callback median / p95 | 7.30 / 12.54 ms | 3.45 / 5.00 ms |
| 30 s idle process CPU, all 32 logical CPUs | 1.42% | 1.46% |
| BUI idle author / paint calls | 0 / 0 | 0 / 0 |
| Idle CamKeys output solves | 0 | 0 |
| Glass owners after unregister | 0 | 0 |

These are Python callback CPU timings, not GPU frame latency or FPS. Idle private
memory decreased about 0.086 MiB on each backend. A short 5 s CamKeys-disabled
baseline was 1.24% Vulkan / 1.59% OpenGL; most remaining process cost therefore
cannot be attributed to repeated CamKeys solves or BUI painting. Warm-up allocations
are recorded separately from idle stability. No universal performance threshold
is asserted.

## Reproduction

Set `BEYOND_UI_CAMKEYS_ROOT` to the isolated repaired CamKeys checkout and
`BEYOND_UI_CRASH_FILE` to a disposable Windows copy of Uraraka. Use the actual
Blender 5.2.2 executable, and run the following once per backend, never simultaneously:

```powershell
python tools/run_blender_tests.py --blender 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --windowed --gpu-backend vulkan --fixture tests/blender_camkeys_popover_audit.py --output <new-output-directory>
python tools/run_blender_tests.py --blender 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --windowed --gpu-backend opengl --fixture tests/blender_camkeys_hardware.py --output <different-new-output-directory>
```

Repeat **both** fixtures on **both** backends. Also run `blender_camkeys_custom.py`,
`blender_backend_renderer.py`, `blender_panel_scroll.py`, `blender_tooltips_popovers.py`,
`blender_nested_menus_windowed.py`, `blender_search_windowed.py`,
`blender_menu_search_windowed.py`, `blender_search_popover_windowed.py`,
`blender_theme.py`, and `capture_motion.py`. Theme/motion captures require
`BEYOND_UI_THEME_DIR` / `BEYOND_UI_MOTION_DIR` set to disposable output directories.
Run `blender_portable_bridge.py`, `blender_numeric.py`, `blender_action_parity.py`,
`blender_developer_controls.py`, and `blender_keying_actions.py` without `--windowed`.
Use `python -m unittest discover -s tests` for unit regressions.

Each runner invocation creates its own config/scripts/extensions/temp directories,
records the command and result marker, and terminates only its own test process.
The QA harness additionally sampled foreground window ownership at 50 ms intervals;
no repaired-run Blender process was observed in the foreground. No OS input
automation was used. This sampling does not rule out a shorter focus transient.

The external QA artifact retains initial failures as well as passing reruns. Early
unrepaired renderer launches activated Blender and were excluded from no-focus
acceptance. A packaging-help invocation also loaded ordinary add-on preferences;
that owned process was terminated, excluded, and replaced by the standalone package
builder. No scene/preferences save was requested in that invocation. Original
source and the Uraraka scene remain unchanged; no version was changed.
