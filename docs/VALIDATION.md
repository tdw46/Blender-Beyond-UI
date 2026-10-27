# Validation record — 2026-10-27

## Current status

The modular extraction and initial custom implementation are execution-tested.
Full custom Blender UI parity is **not complete**. No generated-reference match
has been accepted. Tyler owns visual QA; do not infer approval from screenshots,
unit tests, native forwarding or ordinary CI.

## Evidence

- 16 pure Python tests pass: transactions/rollback, stale-owner rejection,
  retained geometry, clipped input, million-row virtualization, text/arithmetic,
  independent vendor namespaces, and custom color/curve/ramp/picker interactions.
- Ruff parser/name-error checks pass. No claim of full static type validation.
- Exact official documentation inventories: Blender 4.2, 4.3, 4.4, 4.5, 5.0,
  5.1 and 5.2; UILayout, Panel, Menu, UIList and Header. The union includes
  137 UILayout members. Versioned Manual button pages were also checked.
- Blender 5.1.2 `ec6e62d40fa9` and 5.2.2 `d13f752e3b9c`, macOS arm64:
  documented RNA availability, edit rollback, two vendor namespaces,
  registration cycles, custom RNA authoring, ramp/curve rollback and explicit
  unsupported-template behavior pass in disposable background profiles.
- Real windowed tests on both installed versions pass: native reference API
  access, custom anchor/GPU drawing, actual modal toggle input, retained warm
  geometry, outside-region pass-through, invalidation rollback, and disable /
  re-enable callback ownership.
- All four specialized widget painters execute in Blender 5.2.2 / Metal and
  produce actual GPU framebuffer captures. [QA board](design/qa/v1/index.html),
  [full image](design/qa/v1/all-controls-comparison.png),
  [capture provenance](design/qa/v1/capture.json).

No live Blender MCP listener was available. Tests used isolated processes and
profiles; the source BVT extension and unrelated user scenes were not changed.
No visual approval or native Windows/Linux qualification is implied.

## Gates still open

- Full custom control semantics and all documented API methods.
- Exact generated-reference matching, including additional states/sizes/themes.
- Full keyboard/context-menu/tooltip/accessibility parity.
- All older runtime series. 4.2's inherited native ABI allowlist is not a fresh
  qualification of this library; unknown builds are rejected.
- Windows and Linux custom embedded hosts; source is not binary qualification.
- Complete GPU/CPU performance, multi-window, DPI and stress/idle matrices.

The strict `tools/check_custom_parity.py --require-complete` gate intentionally
fails. Ordinary CI validates the current implementation and honest ledger; it
must never be described as evidence of full custom parity.
