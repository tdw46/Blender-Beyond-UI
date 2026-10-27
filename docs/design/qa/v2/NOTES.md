# Reference fidelity revision 2

Generated reference v1 is unchanged. These captures are real Blender 5.2.2 Metal
renders of the library's production full-card painters at 630 × 472 pixels.
The capture script no longer adds its own title/frame around a widget.

Changed: measured shared paint/hit rectangles, transparent card/field surfaces,
explicit blue selected/tab roles, label/value contrast, curve/grid/point colors,
outline icons and chevrons, alpha slider, ramp swatch color conversion, and
bundled Inter Regular/SemiBold. General Canvas titles and Layout panel/heading
labels use the same semibold face. Widgets preserve their aspect ratio at smaller
host widths. Input tests exercise the new geometry and curve numeric fields.

`*-comparison.png` has reference left and implementation right. `*-overlay.png`
and `*-difference.png` are diagnostics; no reference pixels enter runtime code.
`comparison.json` retains the strict exact-match result: **false for all four**.
RGB error has decreased substantially but is not an acceptance threshold.

## Still open

- Background illumination, material highlights, microgeometry, font rasterization
  and several icon/edge details remain visibly different. The generated artwork
  does not define an exact source backdrop or a reproducible lighting process.
- The color reference's RGB 0.20/0.70/0.90 corresponds to HSV approximately
  0.548/0.778/0.900. Its drawn marker is nearer value 0.79, and its hue marker is
  near 0.52. The implementation displays the bound color correctly. Matching both
  the pictured values and pictured positions would require lying about the
  selection. This specification conflict needs an explicit reference revision;
  it has not been silently resolved by changing the image or numeric values.
- The ramp's middle pictured stop is left of the geometric midpoint despite a
  displayed Position 0.50. The implementation positions the bound stop at 0.50.
- Specialized controls remain partial implementations. Header disclosure/menu,
  curve handle-mode menu and ramp interpolation menu are not complete. Picker
  toolbar actions and eyedropper/color actions require consuming-host callbacks.
  These captures establish rendering, not full API semantics or acceptance.

## Transparency evidence

`transparency.png` uses the same production controls over a high-contrast checker
background. `*-alpha.png` captures the actual alpha channel. The cards and fields
transmit the background; color surfaces remain opaque where they depict colors.
These offscreens exercise the tint-only path. The existing host's shared glass
backdrop is forwarded to specialized painters, but this fixture does not prove
native backdrop capture, blur or refraction. No blur pass or readback was added
to the widget production paint path.

## Performance evidence

See `performance.json` and `tests/benchmark_controls.py`. Four visible cards,
including a picker backed by 10,000 rows, are measured after 20 warmup frames for
100 frames in a 1260 × 944 offscreen. Warm line batches and ramp textures keep
identical identities. Icon paths and line geometry are retained independently of
host position; graph grids and multi-stroke icons share batches. One triangle
shader is reused. Fonts load at host setup; final owner teardown releases shared
paint caches.

The revised rendering adds actual title faces, controls, borders and antialiased
geometry that the previous prototype omitted. Its CPU submission p50 is about
0.45 ms (p95 0.51 ms), versus 0.32 ms (p95 0.37 ms) for the previous prototype.
This is a measured increase of about 0.14 ms, not a speedup. The source extension
itself has not been benchmarked with an equivalent workload. Full source-speed
parity, shared-blur cost, dense layouts, idle behavior and live input latency
remain qualification work. A one-pixel synchronization readback is benchmark
instrumentation only; the measured total including that readback is separate.

## API compatibility evidence

Font loading, drawing and unloading were checked against the exact official
[4.2 BLF API](https://docs.blender.org/api/4.2/blf.html),
[5.1 BLF API](https://docs.blender.org/api/5.1/blf.html) and
[5.2 BLF API](https://docs.blender.org/api/5.2/blf.html), and the versioned Manual's
panel pages for 4.2, 5.1 and 5.2. The implementation loads an actual semibold font
file rather than assuming an undocumented BLF weight-setting function. Installed
5.1.2 and 5.2.2 runtimes executed the revised painters; 4.2 was not runtime-tested.
