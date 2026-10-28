# Data Picker interaction progress

The README now embeds eight individual panel GIFs cropped from actual Blender
Canvas captures. A reproducible builder validates frame timing, dimensions and
animation, and records hashes. These are implementation previews, not generated
concepts or a full-parity claim.

The picker now implements draggable scrollbar thumbs (including a usable minimum
size for long lists), page clicks, arrow/Home/End/Page navigation, automatic cursor
reveal and Enter confirmation. Search Enter confirms a result; Home/End inside
search still move the text caret. Selection is revalidated immediately before
commit. Keyboard focus persists when the pointer leaves, then clears on outside
click, hiding, invalidation or cancellation. Escape during a scrollbar drag
restores the starting offset.

Partially visible rows render inside the owning clip instead of disappearing.
Icons use four retained geometry slots and translation uniforms while scrolling.
The 10,000-row benchmark confirms warm geometry remains unchanged. The recorded
four-card median was 0.63ms during fractional scrolling, p95 0.76ms. The separate
rest run was 0.46ms median; timing variability and additional clipping work are
not evidence of source-extension speed equivalence. No measurement/readback
enters production painting.

Real windowed tests on Blender 5.1.2 and 5.2.2 verify mouse scrollbar dragging,
keyboard selection after pointer exit, stale confirmation rejection and outside
click focus release. All 12 prior resting captures remain byte-identical. Scrolled
capture pixels outside the list and scrollbar remain exactly unchanged.

The generated scroll reference is immutable and uses the approved resting picker
as its input. It introduced a different scrollbar position/size than requested;
this conflict is recorded rather than silently changing the input geometry to fit
it. Exact image comparison remains false. The current viewport is clipped at
logical x=25..585, y=147..353 with a 24-pixel scroll offset. Visual acceptance is
still Tyler's QA decision.

Full data-block parity remains open: hidden-data filtering/preferences, rename,
user count/fake user, linked/library/asset status, drag-and-drop and the new hard
requirements for BVT right-click menus and active Blender theme adaptation.
See the [original BVT source contract](../../../SOURCE_UI_CONTRACT.md).

Official API and Manual pages were checked for Blender 4.2, 5.1 and 5.2; native
runtime execution was tested on installed 5.1.2/5.2.2 only:
[4.2 data-block menu](https://docs.blender.org/manual/en/4.2/interface/controls/templates/data_block.html),
[5.1 data-block menu](https://docs.blender.org/manual/en/5.1/interface/controls/templates/data_block.html),
[5.2 data-block menu](https://docs.blender.org/manual/en/5.2/interface/controls/templates/data_block.html),
[4.2 GPU state](https://docs.blender.org/api/4.2/gpu.state.html),
[5.1 GPU state](https://docs.blender.org/api/5.1/gpu.state.html),
[5.2 GPU state](https://docs.blender.org/api/5.2/gpu.state.html).
