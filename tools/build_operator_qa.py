"""Package production operator captures and checked evidence."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/operator-enums"
OUT = ROOT / "docs/design/qa/operator-enums-v1"
OUT.mkdir(parents=True, exist_ok=True)
STATES = {
    "rest": "Dropdowns and expanded operator actions",
    "actions": "Grouped operator choices",
    "long": "200 searchable actions",
    "filtered": "Search result retains exact operator arguments",
    "empty": "No matches",
    "choice-context": "Right-click the selected operator choice",
    "popup-context": "Right-click the custom popup button",
    "disabled": "Motion disabled; glass retained",
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(record, fixture, source=ROOT):
    assert record["passed"] and record["stable_resources"]
    assert record["fixture_sha256"] == sha(ROOT / "tests" / fixture)
    for name, digest in record["source_sha256"].items():
        assert sha(source / name) == digest, name


for suffix in ("", "-51"):
    for dpi in ("1", "1.5", "2"):
        folder = "capture" + suffix + ("" if dpi == "1" else "-" + dpi + "x")
        data = read(BUILD / folder / "capture.json")
        verify(data, "capture_operator_enums.py")
        assert data["fixture_helper_sha256"] == sha(
            ROOT / "tests/operator_choices_fixture.py"
        )
        assert data["native_text_batching_equal_frames"] == 100
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
        for name in STATES:
            shutil.copy2(
                BUILD / folder / (name + ".png"),
                OUT / (name + suffix + "-" + dpi + "x.png"),
            )
    for label in (
        "runtime",
        "windowed",
        "enum-regression",
        "search-regression",
        "menu-regression",
        "context-regression",
        "general",
    ):
        index = 1 if suffix else 0
        assert all(r["passed"] for r in read(BUILD / label / "summary.json"))
        for source, extension in (
            (f"result-{index}.json", ".json"),
            (f"blender-{index}.log", ".log"),
        ):
            shutil.copy2(
                BUILD / label / source,
                OUT / (label + ("-51" if suffix else "-52") + extension),
            )
    for revision in ("before", "after"):
        folder = "benchmark-" + revision + suffix
        data = read(BUILD / folder / "capture.json")
        source = ROOT if revision == "after" else BUILD / "baseline"
        verify(data, "benchmark_operator_enums.py", source)
        assert Path(data["loaded_package"]).parent == source / "beyond_ui"
        shutil.copy2(BUILD / folder / "capture.json", OUT / (folder + ".json"))
        shutil.copy2(
            BUILD / (folder + "-run") / "blender-0.log", OUT / (folder + ".log")
        )
        for name in ("rest", "scalar"):
            shutil.copy2(
                BUILD / folder / (name + ".png"), OUT / (folder + "-" + name + ".png")
            )

frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 100
media = ROOT / "docs/media/panels/operator-enums-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=[30, 30, 40] * 33 + [30],
    loop=0,
    optimize=False,
    disposal=2,
)
with Image.open(media) as preview:
    duration_ms = 0
    for frame in range(preview.n_frames):
        preview.seek(frame)
        duration_ms += preview.info["duration"]
    assert duration_ms == 3330
    encoded_frames = preview.n_frames
media.with_suffix(".json").write_text(
    json.dumps(
        {
            "source": "Actual production Blender frames; no generated pixels",
            "capture": "../../design/qa/operator-enums-v1/capture.json",
            "sha256": sha(media),
            "source_frames": 100,
            "encoded_frames": encoded_frames,
            "duration_ms": duration_ms,
            "encoding": "Duplicate static frames share a longer duration; 30 fps source timing preserved at GIF centisecond resolution",
        },
        indent=2,
    )
    + "\n"
)
from PIL import ImageChops

comparison = {
    "exact_match": False,
    "baseline_commit": "adbe5d62d3d8162fd5d85ba8627ae60483551919",
    "acceptance": "Shared BVT button/menu surfaces reused; new operator semantics are execution-tested. Exact reference and motion acceptance remain with Tyler.",
    "pairs": {},
}
for suffix in ("", "-51"):
    for name in ("rest", "scalar"):
        paths = [
            BUILD / ("benchmark-" + revision + suffix) / (name + ".png")
            for revision in ("before", "after")
        ]
        equal = (
            ImageChops.difference(
                *[Image.open(p).convert("RGB") for p in paths]
            ).getbbox()
            is None
        )
        assert equal
        comparison["pairs"][name + suffix] = {
            "rgb_pixels_equal": equal,
            "before_sha256": sha(paths[0]),
            "after_sha256": sha(paths[1]),
        }
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
shutil.copy2(BUILD / "source/audit.json", OUT / "source-audit.json")
rows = "".join(
    f'<figure><figcaption>{title}</figcaption><a class="capture" data-name="{name}" href="{name}-1x.png"><img src="{name}-1x.png" alt="{title}"></a></figure>'
    for name, title in STATES.items()
)
(OUT / "index.html").write_text(
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Operator choices · QA</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}p{max-width:1050px;line-height:1.6}img{max-width:100%;height:auto;display:block}figure{margin:0}figcaption{padding:10px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,640px));gap:16px}select{font:inherit;padding:6px;background:#292c30;color:white;border:1px solid #777;border-radius:6px}h2{margin-top:36px}</style>
<h1>Operator choices</h1>
<p><code>operator_enum</code> creates expanded action buttons. <code>operator_menu_enum</code> opens the same searchable liquid-glass menu with operator choices. Browsing does not execute the operator; selecting supplies the exact enum identifier and configured arguments. Flags pass singleton sets.</p>
<h2>Actual Blender motion</h2><img src="../../../media/panels/operator-enums-v1.gif" alt="Real Blender operator menu reveal, choice execution, search, expanded button motion and right-click actions">
<p>Existing BVT buttons, arrows, fonts, theme roles, strong menu blur and shared squash/stretch are reused. No new concept artwork is substituted for implementation evidence. These recordings are ready for Tyler’s visual QA; exact reference matching is not claimed.</p>
<h2>Runtime and scale captures</h2><label for="dpi">Capture scale </label><select id="dpi"><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>
<label for="runtime"> Blender </label><select id="runtime"><option value="">5.2.2</option><option value="-51">5.1.2</option></select><div class="grid">"""
    + rows
    + """</div>
<p>600 motion frames match with native text batching enabled/disabled. One backdrop production, one strong blur and five offscreens remain retained alongside font, shader, batch and layout identities. Warm paint performs no dynamic enum evaluation or temporary keyconfig creation. Long menus draw only visible rows.</p>
<p>Real window input searches for action 199, executes once with configured arguments, cancels without execution, activates expanded choices and opens exact operator context menus. Runtime tests cover enum flags, context pointers, dynamic numeric remaps, poll failures, removal, argument changes, invocation, static fallback and a registered host shortcut that opens the custom popup.</p>
<h2>Shared painter regression / before and after</h2><div class="grid"><figure><figcaption>Published adbe5d6 · 48-action menu</figcaption><img src="benchmark-before-scalar.png" alt="Previous shared button and menu renderer"></figure><figure><figcaption>Current renderer · same workload</figcaption><img src="benchmark-after-scalar.png" alt="Current shared button and menu renderer"></figure></div>
<p>The same six buttons and searchable 48-action menu are rendered on both revisions. Resting and open-menu RGB pixels are unchanged on both runtimes. This is a shared-painter regression comparison; the previous revision did not implement these operator authoring methods. <a href="comparison.json">Pixel comparison</a> · <a href="benchmark-before.json">Before timing</a> · <a href="benchmark-after.json">After timing</a>.</p>
<p>130 unit tests plus Blender runtime and window tests pass. Exact reference/motion approval, icon-only buttons and arbitrary custom icons, full native OperatorProperties introspection, broader themes/platforms and Blender 4.2 execution remain open. No native widget fallback is used.</p>
<p><a href="capture.json">Capture record</a> · <a href="runtime-52.json">Runtime checks</a> · <a href="windowed-52.json">Real input</a> · <a href="../../../OPERATOR_CHOICES.md">Integration and limits</a> · <a href="../../../VALIDATION.md">Performance and validation</a> · <a href="source-audit.json">Official source audit</a></p>
<script>function updateCaptures(){const dpi=document.getElementById('dpi').value;const runtime=document.getElementById('runtime').value;for(const link of document.querySelectorAll('a.capture')){const path=`${link.dataset.name}${runtime}-${dpi}x.png`;link.href=path;link.querySelector('img').src=path;}}for(const id of ['dpi','runtime'])document.getElementById(id).addEventListener('change',updateCaptures);</script></html>"""
)
print(OUT)
