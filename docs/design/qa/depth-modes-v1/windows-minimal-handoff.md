# Minimal Windows Volume / Flatten visual check

Completed 2026-11-10 directly through the paired SSH runner: four actual NVIDIA
GPU captures passed and were inspected. See `windows-visual.json` and the four
`windows-*.png` images. Vulkan/OpenGL PNGs match byte-for-byte per state.

The previous assumption that this image-only check required a Windows Codex host
was incorrect. GPUOffScreen captures worked in runner session 0 with isolated
profiles and no-focus launches. Desktop input and foreground-focus qualification
are separate and were not tested. No Windows credentials or settings changed.

Use stock Blender 5.2.2 on the RTX 4090 laptop. Preserve dirty work and live scenes.
Test BUI main `46b9769edf978aa9546638809e2689b2159418bb` and CamKeys master
`e500cdb90c4b204e203ecfe16e0072fb3a4084ca` (or descendants retaining these changes).
Do not rerun geometry/version matrices. No version bumps or renderer changes.

For this noninteractive image check, use BUI's existing
`tests/capture_subject_planes.py` through `tools/run_blender_tests.py` with
`--windowed`, `--gpu-backend vulkan` / `--gpu-backend opengl`, and an isolated
output/profile for each run. The runner requires the advertised
`--no-window-focus`; retain a foreground-PID audit and never activate Blender.
Use Blender-internal input only if needed. Stop only owned test processes.

Set `CAMKEYS_SOURCE` to the tested CamKeys checkout, `BUI_CAPTURE_PICKER=1`,
`BUI_CAPTURE_MODE=LENS`, `BUI_CAPTURE_SCALE=1.5`, and `BUI_CAPTURE_OUTPUT` to a
new test-output directory. For each backend capture:

1. `BUI_CAPTURE_DEPTH_MODE=VOLUME`, `BUI_CAPTURE_WIDTH=380`, unique capture tag.
2. `BUI_CAPTURE_DEPTH_MODE=FLATTEN`, `BUI_CAPTURE_WIDTH=260`, unique capture tag.

Four short processes total. Example command (resolve paths on Windows):

```powershell
& $Python "$Bui\tools\run_blender_tests.py" --blender $Blender --windowed `
  --gpu-backend vulkan --fixture "$Bui\tests\capture_subject_planes.py" `
  --output "$Results\vulkan-volume" --timeout 60
```

Inspect the four actual PNGs: both icons visible and centered, bold readable
labels, correct selected highlight, accent colors, glass, and no wrapping or
clipping at narrow width. Compare with the Mac images in this same QA directory.
Confirm actual backend and NVIDIA renderer with `gpu.platform` in the fixture
result (extend only diagnostic result metadata if needed); never count a backend
request or adapter inventory as proof of the rendering backend.

Retain the PNGs, runtime JSON, exact tested commits, backend/renderer and session
record. Actual desktop tests still require the signed-in session. This checks the new picker appearance only; it does not requalify all
popup interactions, bounce or whole-scene performance. If the images pass, stop.

The runner account blocks `.ps1` execution by policy. The verified run used the
global guide’s literal UTF-16LE `-EncodedCommand` route without changing execution
policy. `build/windows-depth-v1/visual/` retains scripts and SSH logs locally;
`windows-visual.json` records owned PIDs, launch commands and actual GPU metadata.
