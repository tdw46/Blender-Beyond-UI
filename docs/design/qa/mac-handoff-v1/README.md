# Mac performance handoff — 2026-11-03

Pulled Beyond UI `3b6b864`, CamKeys `5bd2f28`, BVT `9da830b`.
Both development and installed CamKeys have the complete published vendor.
Backup branches preserve the previous source heads. The interrupted overview
changes were backed up before updating.

431 BUI unit tests and three BVT module-cache tests pass. Actual Blender 5.2.2
Metal checks passed for a copied Uraraka scene: unchanged-panel reuse with live
values; invalidation on help/mode/selection changes; same-size reorder/deletion;
registered-list interactions; scroll/offscreen behavior; and shared glass with
retained resources. All windowed focus audits recorded no activation/restoration.
The original scene hash is unchanged. See [report.json](report.json).

No new visual acceptance or Mac speedup is claimed. Windows measurements remain
Windows evidence. Running Uraraka/Midoriya sessions were left alone; restart
normally after saving your work to load the complete installed packages.

BVT source preflight currently rejects the existing native certificate because
`VRM_Compositor.py` and `src/beyond_npr/shadow_scene.py` differ from its proof.
Both the compositor file and renderer submodule pin are unchanged by this pull;
the mismatch predates this sync. No certificate was rewritten and no native
package was replaced. This remains a separate native-optimization validation gap.
