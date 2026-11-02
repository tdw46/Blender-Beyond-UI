# Blender compatibility

**Blender 4.2 remains the minimum target.** Compatibility covers every release
family through 5.2; no version bump or minimum-version increase was made.
Controls retain the shared glass, motion, theme and owner-aware context actions.
Backends are available only where the selected Blender release and OS provide them.

## Qualified builds and remaining limits

| Stock release | macOS arm64 native actions | Windows x64 native actions |
| --- | --- | --- |
| 4.2.0 | Passed | Passed |
| 4.2.23 LTS | Passed | Passed |
| 4.3.2 | Passed | Passed |
| 4.4.3 | Passed | Passed |
| 4.5.15 LTS | Passed | Passed |
| 5.0.1 | Passed | Passed |
| 5.1.2 | Passed | Passed |
| 5.2.2 LTS | Passed | Passed |

These are exact official builds, not every historical patch or a custom build.
Other patches need their own compiled, tested artifact. The target remains all
release families back to 4.2; unsupported exact builds report their admission
reason rather than loading an unsafe ABI or claiming native fallback is custom parity.

Native-action checks exercise dynamic enum allocation, nested context restoration,
driver copy/paste, property/operator Favorites and custom-property metadata.
Current macOS window tests additionally exercise popover opening, right-click
ownership, numeric editing, nested dismissal and finite animation teardown.
The focus audit records activation/restoration separately from test success.

| GPU execution | Evidence | Remaining acceptance |
| --- | --- | --- |
| Metal / macOS | 4.2.0, 4.4.3, 5.1.2, 5.2.2: real native framebuffer copy, shared blur/refraction, retained resources | User visual/performance review |
| OpenGL / Linux software Mesa | 4.2.0: actual shader, glass and retained-resource checks | Hardware GPU and embedded-host integration |
| Vulkan / Linux software Mesa | 5.2.2: actual shader, glass and retained-resource checks | Windows/NVIDIA GPU and embedded-host integration |

**Windows/NVIDIA 5.2.2 is ready for a hardware QA pass, not certified by Linux
software rendering.** Windows packages pass native-action execution in CI;
window-level callback composition and actual GPU appearance remain unverified there.
Linux's stock binary does not export the symbols this native host adapter needs;
the Linux embedded-panel host remains unavailable. Intel macOS is also unqualified.
Renderer success does not remove those native-host gaps.

See [the execution report](design/qa/compatibility-v1/report.json) for exact builds,
CI provenance and scope. Existing GIFs remain historical styling evidence; no new
cross-platform visual acceptance is implied.

## Packaging and maintenance

The renderer uses Blender's GPU abstraction. The native host bridge uses private
Blender APIs and is compiled against each stock build's exact source headers.
`beyond_ui/_native/catalog.json` pins manifests; manifests pin the compiled library,
executable, C++ and Python adapter sources, platform and available backends.
Windows addresses come from the executable's matching PDB and are checked against
its PE sections. Unknown or changed builds fail closed. Source line endings are
fixed with `.gitattributes` so Windows and macOS vendor fingerprints agree.

There is no runtime compiler, download or code scanning. Version-specific paths
are compiled against actual headers, including older driver clipboard callbacks,
framebuffer copying, allocation signatures, layout and context structures.
Existing exact-build macOS adapters remain available as a compatibility route.

```sh
python tools/build_portable_bridge.py --version 4.2.23 --workspace build/native
python tools/native/run_smoke.py build/native/build-result.json
```

Use `--blender /path/to/blender` for a matching installed runtime. Build and test
on the target OS/architecture. Never broaden a manifest's build hash to admit an
untested patch. Rebuild after changing fingerprinted bridge files.

## Windows/NVIDIA check

Use Blender 5.2.2's official x64 build and the refreshed CamKeys vendor package.
Restart Blender normally after installing; an already running process retains its
loaded native adapter. Test Vulkan, then OpenGL where offered, restarting for each
backend change. In a copy of Uraraka, check sidebar scrolling and changing values,
Falloff and Billboard popovers over the sidebar, nested menus, right-click paths,
hover descriptions, blur over viewport detail, and motion settling without idle
redraw. Report the Blender build hash, backend, GPU/driver, screenshot and any
console error. Do not save over the original scene for compatibility QA.

Official API/Manual entry points: [4.2 GPU API](https://docs.blender.org/api/4.2/gpu.html),
[5.2 GPU API](https://docs.blender.org/api/5.2/gpu.html),
[4.2 System preferences](https://docs.blender.org/manual/en/4.2/editors/preferences/system.html),
[5.2 System preferences](https://docs.blender.org/manual/en/5.2/editors/preferences/system.html).
Exact installed runtime/source checks are the evidence for private ABI behavior.
