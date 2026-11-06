# Windows Subject Size follow-up — 2026-11-06

Targeted physical NVIDIA execution passed on official Blender 5.2.2 LTS
`d13f752e3b9c`, RTX 4090 Laptop GPU / 591.74, Windows 11 25H2
26220.9836, 144 DPI / 150%, UI scale 1.5. Vulkan and OpenGL were separate
no-focus disposable-profile processes. Neither backend used native UI fallback.

Upstream BUI main `3349364` and CamKeys master `6954a27` were pulled with
backups. CamKeys' runtime pin was `1870ea0`. The only new BUI runtime change is
`8037f3b`: wrapped labels measure the same bold/regular font face and exact
host-scaled size used by painting. The former regular-font approximation could
clip a bold title at a wrap threshold. This runs during retained layout only;
the native adapters, shaders, glass and scheduling policies are unchanged.

The consumer adds four title reset buttons, neutral reset transactions and
new size defaults. Compact stacked labels retain the existing bold subheading
appearance; inline labels and values remain regular. No global font-weight
override was added.

- 494 Python tests pass, including bold-heading width/face regression.
- Both physical backends pass portable native admission/context actions,
  retained shader/icon/glass checks, responsive fitting, consumer subject-size
  controls, transition curves, exact-only wizard checks and front/back live
  curve previews. Consumer callback/reset regressions pass after the final fix.
- Actual native Uraraka-copy mouse input passes all three wizard routes,
  two-axis joystick edits with evaluated geometry changing before release,
  release settling, Escape cancellation, exact owner and title reset hit areas.
- 220/260/380 logical-width captures at 1/2/1.5 scale and Blender/consumer
  themes pass actual glyph-width assertions. No focus activation was recorded.
- Ten warm wide-card CPU-submit samples: median 2.32 ms Vulkan / 1.56 ms
  OpenGL (44 controls). Upstream reference: 5.71 / 1.92 ms (40 controls).
  Small noisy samples, not GPU FPS or evidence of a speedup. Three-second
  settled native samples observed zero BUI canvas paint calls on both backends.

Raw local evidence is in
`C:/Users/tyler/Documents/CamKeys-Windows-Sync-20261106/`.
Representative generic component captures are retained here. The UI integration
fixture uses an unsaved copy of the newer saved Uraraka wizard file. The older
diagnostic file's unversioned graph was retained by conservative migration;
it was not silently replaced to obtain a passing result.

Metal execution for this small heading fix remains unverified here. Mac should
replay the width/scale captures plus native compact title/reset interaction.
No new movie, full viewport-FPS benchmark, long resource soak or shadow
render/playblast requalification is claimed. Stock lens-subtype console warnings
remain in the retained logs; runtime input/draw/fallback error maps are empty.
