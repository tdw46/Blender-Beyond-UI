"""Compare cold invalidated and retained layout costs in disposable Blender."""

import bpy, sys, os, json, time, statistics, hashlib, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("BEYOND_UI_LIBRARY_ROOT", str(ROOT)))
sys.path.insert(0, str(SOURCE))
from beyond_ui import Layout

try:
    ui = Layout(context=bpy.context)
    for i in range(24):
        row = ui.row()
        for j in range(6):
            row.group.button(f"{i}:{j}", f"Action {i}:{j}", lambda: None)
    canvas = ui.canvas
    canvas.arrange(560)

    def sample(invalidate):
        values = []
        for i in range(220):
            if invalidate:
                canvas._dirty = True
            start = time.perf_counter_ns()
            canvas.arrange(560)
            elapsed = (time.perf_counter_ns() - start) / 1e6
            if i >= 20:
                values.append(elapsed)
        return dict(
            median_ms=statistics.median(values),
            p95_ms=sorted(values)[189],
            max_ms=max(values),
        )

    timings = dict(invalidated=sample(True), retained=sample(False))
    if ui.supports("scale_y"):
        ui.scale_y = 1.25
        timings.update(
            configured_invalidated=sample(True), configured_retained=sample(False)
        )
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        timings=timings,
        workload="144 buttons in 24 rows, 560 logical width, 20 warmups and 200 samples per case; no GPU or bindings",
        source_sha256={
            str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (SOURCE / "beyond_ui").rglob("*.py")
        },
        fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(
    "LAYOUT_BENCHMARK", result.get("passed"), result.get("timings", result.get("error"))
)
