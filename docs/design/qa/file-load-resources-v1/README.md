# File-switch rendering resources

Opening All Might in an existing session left CamKeys BUI text invisible. The retained labels and numeric values were present, no draw/input exception was recorded, and BLF could still measure its font IDs. Releasing/recreating owned fonts and render caches restored the live text.

BUI now retires complete panel hosts before loading a file, including fonts, cached measurement/render resources, callbacks and old-region records. The existing finite startup task creates fresh hosts after loading (or a failed load when that handler is available). Theme/motion configuration stays intact; ordinary undo/value refreshes retain warm resources. No new paint-time probes, polling or repeated resource loads.

Actual no-focus Metal tests on 4.2.23, 4.3.2, 4.4.3, 4.5.15, 5.0.1, 5.1.2 and 5.2.2 each open files three times. Body/bold text pixels stay identical, previous resources close, ordinary refresh retains fonts and failed-load callback recovery works. Unit suite: 472 tests, one skipped, zero failures. No owned test process took focus. Physical Windows replay remains pending.

Source and installed CamKeys vendored packages match their 248-file SHA-256 manifests. Live All Might definitions reloaded; scene/view snapshot unchanged during installation; no save. Screenshots show the missing/restored text but are not a geometry comparison: the user continued navigation between captures.
