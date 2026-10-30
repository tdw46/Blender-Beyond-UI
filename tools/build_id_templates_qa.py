"""Package source-verified ID-template execution, scale, motion and performance evidence."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/id-templates"
OUT = ROOT / "docs/design/qa/id-templates-v1"
OUT.mkdir(parents=True, exist_ok=True)
STATES = {
    "rest": "Data-block controls beside ordinary fields",
    "narrow": "Narrow host; unchanged logical font scale",
    "picker": "Searchable data-block picker",
    "owner-menu": "Name field owner menu",
    "tab-menu": "Clicked ID tab context menu",
    "disabled": "Motion disabled; shared glass retained",
}


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(data, fixture, source=ROOT):
    assert data["passed"] and data["stable_resources"]
    assert data["fixture_sha256"] == sha(ROOT / "tests" / fixture)
    for path, digest in data["source_sha256"].items():
        assert sha(source / path) == digest, path


def copy(source, name):
    shutil.copy2(source, OUT / name)


comparisons = []
performance = []
for suffix in ("", "-51"):
    for dpi in ("1", "1.5", "2"):
        folder = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        data = read(BUILD / folder / "capture.json")
        verify(data, "capture_id_templates.py")
        assert data["fixture_helper_sha256"] == sha(
            ROOT / "tests/id_templates_fixture.py"
        )
        assert data["paint_candidate_enumerations"] == 0
        assert data["native_text_batching_equal_frames"] == 60
        assert data["retained_resources"]["productions"] == 1
        assert data["retained_resources"]["blur"] == 1
        for name in STATES:
            copy(BUILD / folder / (name + ".png"), name + suffix + "-" + dpi + "x.png")
        copy(BUILD / folder / "frame-022.png", "motion" + suffix + "-" + dpi + "x.png")
        copy(BUILD / folder / "capture.json", folder + ".json")
        copy(BUILD / (folder + "-run") / "blender-0.log", folder + ".log")
    for label in ("runtime", "windowed", "general", "pointer"):
        folder = label + suffix
        assert all(r["passed"] for r in read(BUILD / folder / "summary.json"))
        copy(BUILD / folder / "result-0.json", folder + ".json")
        copy(BUILD / folder / "blender-0.log", folder + ".log")
    for workload, fixture, states in (
        ("benchmark", "benchmark_operator_enums.py", ("rest", "scalar")),
        ("dense", "benchmark_flow_dense.py", ("rest", "scalar", "scrolled")),
    ):
        for revision in ("before", "after"):
            folder = workload + "-" + revision + suffix
            source = BUILD / "baseline" if revision == "before" else ROOT
            data = read(BUILD / folder / "capture.json")
            verify(data, fixture, source)
            assert Path(data["loaded_package"]).parent == source / "beyond_ui"
            copy(BUILD / folder / "capture.json", folder + ".json")
            copy(BUILD / (folder + "-run") / "blender-0.log", folder + ".log")
            for name in states:
                copy(BUILD / folder / (name + ".png"), folder + "-" + name + ".png")
            performance.append(
                dict(
                    runtime=data["version"],
                    workload=workload,
                    revision=revision,
                    timings=data["timings"],
                )
            )
        for name in states:
            a = Image.open(
                OUT / (workload + "-before" + suffix + "-" + name + ".png")
            ).convert("RGB")
            b = Image.open(
                OUT / (workload + "-after" + suffix + "-" + name + ".png")
            ).convert("RGB")
            equal = ImageChops.difference(a, b).getbbox() is None
            assert equal, (workload, suffix, name)
            comparisons.append(
                dict(
                    runtime="5.1.2" if suffix else "5.2.2",
                    workload=workload,
                    state=name,
                    rgb_equal=equal,
                )
            )

frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 60
media = ROOT / "docs/media/panels/id-templates-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=[30, 30, 40] * 20,
    loop=0,
    optimize=False,
    disposal=2,
)
with Image.open(media) as gif:
    duration = 0
    for i in range(gif.n_frames):
        gif.seek(i)
        duration += gif.info["duration"]
    assert duration == 2000
media.with_suffix(".json").write_text(
    json.dumps(
        dict(
            source="Actual production Blender frames; no generated pixels",
            capture="../../design/qa/id-templates-v1/capture.json",
            sha256=sha(media),
            source_frames=60,
            duration_ms=duration,
        ),
        indent=2,
    )
    + "\n"
)

sources = []
for revision in ("v4.2.0", "ec6e62d40fa9", "d13f752e3b9c"):
    relative = "source/blender/editors/interface/" + (
        "interface_templates.cc"
        if revision == "v4.2.0"
        else "templates/interface_template_id.cc"
    )
    path = BUILD / "source" / revision / Path(relative).name
    sources.append(
        dict(
            url=f"https://raw.githubusercontent.com/blender/blender/{revision}/{relative}",
            sha256=sha(path),
        )
    )
(OUT / "source-audit.json").write_text(json.dumps(sources, indent=2) + "\n")
record = dict(
    exact_match=False,
    full_custom_parity=False,
    baseline="8a321cb0e50211ffe3635a1593b996dcfd9f7303",
    acceptance="Existing BVT controls reused. Generated-reference and visual QA remain open. Code and execution checks only.",
    native_text_batching_equal_frames=360,
    existing_workload_pixel_comparisons=comparisons,
    performance=performance,
)
(OUT / "comparison.json").write_text(json.dumps(record, indent=2) + "\n")
(OUT / "manifest.json").write_text(
    json.dumps(
        {
            str(p.relative_to(OUT)): sha(p)
            for p in sorted(OUT.iterdir())
            if p.is_file() and p.name not in {"manifest.json", "index.html"}
        },
        indent=2,
    )
    + "\n"
)
rows = "".join(
    f'<section><h2>{label}</h2><div class="pair"><figure><figcaption>Blender 5.2.2</figcaption><img src="{name}-1x.png"></figure><figure><figcaption>Blender 5.1.2</figcaption><img src="{name}-51-1x.png"></figure></div></section>'
    for name, label in STATES.items()
)
links = " · ".join(
    f'<a href="rest{suffix}-{dpi}x.png">{version} at {dpi}×</a>'
    for suffix, version in (("", "5.2.2"), ("-51", "5.1.2"))
    for dpi in ("1", "1.5", "2")
)
(OUT / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond UI — ID template QA</title><style>body{background:#171b20;color:#e6e8eb;font:16px system-ui;margin:32px auto;max-width:1340px;padding:0 20px}a{color:#91c8ff}h1{font-size:28px}h2{font-size:20px;font-weight:600}.pair{display:flex;gap:20px;flex-wrap:wrap}figure{margin:0;flex:1;min-width:300px}img{max-width:100%;height:auto}figcaption{margin:10px 0;color:#aeb9c4}section{margin:40px 0}p{max-width:950px;line-height:1.6}</style><h1>Data-block selectors and tabs</h1><p>Actual production Blender rendering with active-theme colors, shared BVT glass and motion. These controls remain partial; exact generated-reference acceptance is open. No new generated reference is claimed for this composition. Tyler owns visual QA.</p><p><a href="../../../ID_TEMPLATES.md">Behavior and remaining gaps</a> · <a href="comparison.json">Measured comparisons</a> · <a href="source-audit.json">Source audit</a></p><h2>Animation overview</h2><img src="../../../media/panels/id-templates-v1.gif" alt="Actual ID controls in motion"><p>All 360 sampled frames match with native text batching enabled and disabled. One retained backdrop and one strong blur revision; no candidate enumeration during paint.</p><p>"""
    + links
    + "</p>"
    + rows
    + "</html>"
)
print(json.dumps(record, indent=2))
