# Macro child registration safety

The 2026-10-31 launch crash was a Beyond UI adoption defect, reproduced without
loading a scene. The reported Camera Effect Locks scene was not the cause.

CamKeys registers navigation macros that reference its begin/finish operators.
Beyond UI then unregistered and re-registered those operators to wrap callbacks.
Blender's macro definitions retain pointers to their child OperatorProperties RNA
types. Re-registration frees those types without rebuilding the macro definition.
After an event-loop update, writing nested keymap properties crashed in
`WM_operator_properties_create_ptr`, through `Operator_properties_get` and
`path_resolve`. Immediate, same-callback checks missed this deferred failure.

The registration-only audit in `macro_safety.py` preserves children referenced by
registered Python macros, including macros owned by other packages, and protects
their registered bases. Macro registration is detected by its own `bl_rna`:
Macro does not expose Operator's `is_registered` attribute. An unreadable macro
audit fails closed by preserving operator registrations. No scanning is added to
painting, input or idle callbacks.

Preserved dependencies appear in `status.popups.preserved_macro_dependencies`.
Their own popup callbacks retain native routing, explicitly recorded in
`status.popups.native_fallbacks`; this is not custom popup parity. CamKeys' two
navigation steps have no popup UI. Its panels, dialogs, lists, glass, motion,
theme and right-click controls remain on the existing custom routes.

## Evidence

- Before repair: minimal deferred macro property write crashed without any scene.
- After repair: deferred write and teardown passed on 5.1.2 and 5.2.2.
- Full CamKeys consumer regressions passed on both versions; 296 unit tests pass.
- The original scene loaded on 5.2.2, with 63 objects, five forced keymap refreshes
  and 15 nested macro-property writes. Its SHA-256 remained unchanged.
- The installed CamKeys vendor matches the repaired source; the previous vendor
  is backed up in ignored `build/launch-crash/installed-vendor-before`.
- Use a fresh Blender process: hot-reloading cannot repair already dangling RNA.

[Runtime and focus evidence](design/qa/macro-lifecycle-v1/runtime.json).
Tests used isolated preferences and CamKeys; other user add-ons were not enabled.
No visual approval is implied. Blender 4.2 was not runtime-tested in this pass.

Exact versioned 4.2/5.1/5.2 API and Manual requests were unavailable through the
documentation fetcher. The installed runtime and official 5.2.2 source establish
this diagnosis: [macro definition and operator removal](https://github.com/blender/blender/blob/v5.2.2/source/blender/windowmanager/intern/wm_operator_type.cc)
and [operator property access](https://github.com/blender/blender/blob/v5.2.2/source/blender/makesrna/intern/rna_wm.cc).
