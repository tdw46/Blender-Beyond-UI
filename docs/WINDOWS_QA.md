# Windows / NVIDIA compatibility QA

Use the exact CamKeys commit supplied with the checkpoint. CamKeys already
contains its pinned Beyond UI package; do not replace it with another branch.
Use a separate worktree if the local checkout contains changes. Verify the
installed add-on path and Git HEAD before testing. Preserve repository line
endings: the vendored `.gitattributes` protects native-adapter fingerprints.

## Test environment

- Official Windows x64 Blender 5.2.2, build `d13f752e3b9c`.
- Record Windows version, NVIDIA GPU and driver, Blender build, active backend,
  display scaling and UI scale.
- Run Vulkan and OpenGL separately, restarting Blender after switching backend.
- Use a disposable profile and a copy of Uraraka. Locate the Windows scene path;
  do not reuse the Mac path, overwrite the original, or save user preferences.
- Confirm the exact-build native adapter is admitted and panels/popovers use BUI.
  A native fallback or a flat alpha overlay is a defect, not a passing result.
- Automated window launches must use the no-focus test runner and verify focus
  behavior. Do not inject desktop input or deliberately activate Blender without
  permission. Keep unrelated Blender sessions untouched.

## Exercise both backends

1. Open all CamKeys panels, lists and brush curves. Check text, icons, labels,
   accents, disabled states, dividers and scaling at narrow/wide panel widths.
2. Open Appearance, Billboard settings, Flattened Falloff and other panel,
   property and operator popovers. Check overlap over the sidebar, viewport-backed
   liquid glass, blur/refraction/rims, nested menus, clipping and hit alignment.
3. Exercise hover descriptions with developer tooltips enabled; right-click
   properties and list subcontrols. Check copy paths, numeric editing, applicable
   animation/keying actions and driver clipboard. Execute against disposable data
   and verify the exact owner changed; disabled or unavailable actions must be honest.
4. Move the viewport while CamKey values update. Verify actual shape-key values,
   UI feedback, no scroll jump, offscreen culling and recovery on scrolling back.
5. Test dropdown searching, wheel/trackpad scroll, keyboard navigation, nested
   Escape, cancellation and reopening. Exercise repeated popup open/close and
   add-on disable/re-enable in the disposable session.
6. Compare Blender-theme mode with explicit CamKeys orange/green overrides.
   Check motion at default, disabled, and changed speed/strength settings.
7. Record warm interaction frame timings and idle CPU/redraw behavior. Capture
   screenshots/short clips and console errors; distinguish measured performance
   from visual impressions. Check for stale callbacks or increasing resources.

## Report

Provide a Vulkan/OpenGL pass/fail/unverified table, exact commits and environment,
native-adapter status, reproduction steps, logs, screenshots/clips, timing method
and measurements. Keep software-Mesa evidence separate from NVIDIA hardware
results. Do not claim other Blender patches or operating systems are qualified.
Do not modify code, versions, manifests or fingerprints merely to make admission
pass; report failures and proposed fixes first.
