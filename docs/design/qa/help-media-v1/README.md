# CamKeys help media replacements

Distance Only now uses the supplied `Camkeys - CamProps Outline Width Demo - Sm_opt_opt_opt.mp4`, bundled as `distance`. CamKeys header / View source help uses the existing Sonic clip (`apparent_fov`, also used in Choose Your Subject). Other workflow and help mappings remain unchanged.

The new clip keeps the complete 2.34-second duration at the existing 10 FPS preview cadence, 320 × 162 pixels; 23 compressed RGBA frames use 1,030,465 bytes. It retains the shared silent looping playback, rounded media surface and visible-only scheduler. No decoder dependency or source-machine path is required at runtime.

Source and installed CamKeys files match. Live Blender 5.2.2 successfully builds both help layouts and decodes every frame of both clips. No scene save, release version change or platform-specific API change. No new visual/GIF capture or physical Windows execution was performed for this media-only change.

## Billboard alignment and remaining help mappings

The billboard accessory lane now has explicit BUI widths and gutters: toggle, 28-unit cog, then 24-unit help button at the panel right edge. Both icon buttons share their vertical center. The help button stays to the right of the cog as requested and plays Stepped Turn Around. Retained-layout checks pass at 280, 360 and 520 logical units; no additional visual capture was performed.

Falloff help uses Sonic. CamProps help uses the Mr. Incredible clip, with Another example opening the new cube outline-width clip; the cube example links back to Mr. Incredible. The CamProps comparison help also resolves to the cube clip. Lens Tricks retains its explicitly requested AutoFOV comparison clip. Live help draw and frame decoding checks pass for every changed mapping. Source and installed checkout agree; live definitions reloaded and adopted panels refreshed without saving Uraraka.
