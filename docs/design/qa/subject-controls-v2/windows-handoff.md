# View-plane controls: Windows handoff

Use the published CamKeys master commit and its complete pinned `_vendor/beyond_ui`.
Do not mix individual files from a previous install. Blender 4.2 onward remains
the target; no version numbers or native admission certificates were changed.

The shared inset shader uses the existing GPUShaderCreateInfo path and unchanged
push-constant layout. Duotone icons use the existing retained RGBA8 atlas renderer.
There are no platform-specific joystick, responsive-layout or curve-owner paths.
The native bridge sources, binaries, exact-build fingerprints, Windows signing
admission, LF rules, Vulkan/OpenGL routing and no-focus runner are unchanged.

Automated dispatch in the private CamKeys repo: **Subject controls Windows
compatibility** takes an exact public BUI test-harness commit and checks the
current CamKeys commit with its own repository token. It runs packaged native admission/context actions, transition curves,
responsive widths, subject geometry and asset loading on Windows Blender
4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2 and 5.2.2. Separate Linux software-GPU
jobs execute the actual inset/icon/glass shaders on OpenGL and Vulkan. These
jobs do not establish Windows/NVIDIA hardware appearance or performance.

For the hardware pass, use the existing [Windows checklist](../../../WINDOWS_QA.md)
and add:

- Lens / Subject Size and Exact / Artistic tabs: accent overrides vs native theme,
  narrow/wide width, centered contained shutter, selected state and right-click.
- Front/Subject/Back pads: 4x speed, Shift precision, reset, cancel, independent
  values, no idle redraw, and compact layout before X/Y fields wrap.
- Both transition curve popovers: drag a point with the view stationary; the
  mesh must update before release and presets must update without closing.
  The endpoint remains at zero. Change active item and verify the popup still
  edits its original owner; test undo and stale-owner cancellation.
- Repeat with Vulkan and OpenGL after separate Blender restarts. Preserve the
  existing liquid glass, shadow-capture and exact-owner context-menu behavior.
- Record exact commits, Blender hash/backend/GPU/driver, console output and
  performance observations. Use copied scenes and disposable profiles.

Local Metal execution passed with native framebuffer copying, shared retained
glass, both inset modes and recolored two-layer icons. 493 pure Python tests pass
(one skipped). No extra per-frame shader/texture creation was introduced.
Official versioned GPU/API pages could not be retrieved during this audit
(HTTP 402/403); exact installed-runtime execution is the evidence used here.

The initial public-repository consumer dispatch stopped at checkout because its
scoped token cannot read private CamKeys. Consumer CI now lives in CamKeys; no
new cross-repository secret or credential grant is required. The first GPU run
passed both software backends: BUI Actions run 42256503879.

## Completed automated qualification

- [Windows consumer run 42256908454](https://github.com/tdw46/CamShapeMatic/actions/runs/42256908454): **42/42 passed**, six fixtures on each of seven Blender versions.
- [Shared renderer run 42256503879](https://github.com/tdw46/Blender-Beyond-UI/actions/runs/42256503879): OpenGL 4.2.0 and Vulkan 5.2.2 software GPU jobs **passed**; the initial private checkout jobs failed before execution and were replaced by the consumer run above.
- [Cross-platform pure Python run 42256397064](https://github.com/tdw46/Blender-Beyond-UI/actions/runs/42256397064): Mac/Windows/Linux **passed** (493 tests, one skip).
- Local Metal 5.2.2: native framebuffer copy, retained glass, both inset modes, duotone colors and retained textures **passed**. No focus activation in the audit.

Production versions tested: BUI `1870ea0a9e81f191ab9623cf267978afe7ad96c1`,
CamKeys `75a4997f59def987fcf58ef991329ec7943b615a` (Windows CI checkout
`f75651d` adds only its workflow). Later publication commits update QA records.
No package version bumps, native certificate relaxation or changes to BVT.
Physical NVIDIA appearance, host composition and viewport performance are still
manual acceptance items; the software renderer is not that hardware evidence.
