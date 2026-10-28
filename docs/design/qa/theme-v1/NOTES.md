# Theme plumbing checkpoint — 2026-10-28

Production now obtains semantic colors from Blender using the original BVT reader.
Eight compound panels, basic controls and existing selection menus share those
roles. Fixed artwork colors require an explicit `REFERENCE` policy.
[Mapping and host integration](../../../THEMING.md).

## Execution and data preservation

- 36 pure Python tests pass, including source RGB/RGBA handling, immutable bounded
  caches, live signature changes, explicit reference policy and unavailable RNA.
- Actual production Canvas painting in isolated Blender 5.1.2 / 5.2.2 macOS Metal
  processes passes for native dark and synthetic light/purple role sets. These are
  synthetic test themes, not Blender's installed Light preset.
- Existing canvas instances change colors without reload. Line batches, ramp
  textures, skin/ring batches and layout counts remain unchanged after warm-up.
- Interior pixels sampled from palette swatches, the ramp and HSV/hue regions
  remain identical across theme changes. Bindings retain their existing color
  handling. This is a sampled data-color check, not proof for every preview type.
- The fixture restores every changed RNA value and never saves preferences.
  No unrelated scene or source BVT file was changed.
- Real embedded-panel tests on both versions pass: actual modal input, retained
  geometry, finite animation timer termination, outside pass-through, rollback,
  host disable and repeated registration.
- All 12 earlier individual resting PNGs remain byte-identical, including contrast
  and alpha captures. All 75 frames plus rest/settled/disabled views of the existing
  eight-panel artwork animation remain byte-identical. The README GIFs remain
  accurate for their explicitly documented reference palette.

## Performance

Blender 5.2.2 / Metal, four 630×472 cards in a 1260×944 target, 10,000-row picker
scrolling 1.25 logical pixels each frame, 20 warm-up + 100 measured samples.
All runs retain 27 line batches and unchanged ramp textures. No other Blender
fixture was launched during these timing runs.

| Run | CPU median | CPU p95 | CPU max | Submission + one-pixel GPU sync median |
| --- | ---: | ---: | ---: | ---: |
| Prior commit a76da88 | 0.514 ms | 0.611 ms | 0.708 ms | 0.938 ms |
| New explicit reference palette | 0.438 ms | 0.493 ms | 0.548 ms | 0.831 ms |
| New Blender theme, 11 color reads per frame | 0.507 ms | 0.566 ms | 0.653 ms | 1.149 ms |

CPU submission shows no regression in these runs. Synchronized GPU timing varies
and is higher in the native-theme run; this needs broader sampling before claiming
performance equivalence. These measurements do not establish source BVT speed,
shared-blur cost, input latency, Windows/Linux behavior or every workload. Timing
and framebuffer readback remain confined to fixtures.

## Reference conflict and visual acceptance

[Comparison](comparison.png): generated sheet left, actual captures right.
[Overlay](overlay.png) and [difference](difference.png) retain the mismatch.
[Generation provenance](../../references/theme-states-v1.json) and
[exact prompt](../../references/theme-states-v1.prompt.txt) are saved; built-in
`image_gen` was used. Supporting inputs are the actual three theme captures,
whose geometry comes from the prior generated controls and source BVT styling.

The generator changed column proportions, row spacing and numeric text, and
cropped/compressed the purple bottom row despite the prompt's invariants. The
original 1130×1392 result is immutable; only the comparison copy is normalized to
the requested 1360×1680 sheet size. This candidate is **not adopted or approved**.
A generated number cannot replace a bound value, and cropped panels cannot define
a complete control. Reference correction and Tyler's visual QA remain open.
No exact-match acceptance is claimed; unchanged prior reference fixtures do not
imply approval for these new themes.

Full right-click menus, the remaining custom API semantics, older runtime series,
DPI matrices and non-macOS hosts remain separate open parity gates.
