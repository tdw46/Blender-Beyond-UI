"""Publish current renderer captures for human QA, without claiming acceptance."""

import hashlib, html, json, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/core-review-v2-final"
OUT = ROOT / "docs/design/qa/core-review-v2"
MEDIA = ROOT / "docs/media/panels"
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
focus = read(ROOT / "build/core-review-v2-final-focus.json")
records = []
states = (
    "rest",
    "hold-menu",
    "hold-context",
    "popover",
    "cancel-context",
    "components",
    "component-enums",
    "component-filtered",
    "narrow",
    "disabled",
)
for label, source in (
    ("1x", "1x"),
    ("15x", "15x"),
    ("2x", "2x"),
    ("51", "51"),
    ("scalar", "scalar"),
):
    record = read(BUILD / ("run-" + source) / "summary.json")[0]
    assert record["passed"] and record["result"]["stable_resources"]
    audit = focus
    record["focus_passed"] = record["pid"] not in audit[
        "sampled_frontmost_pids"
    ] and not any(e.get("pid") == record["pid"] for e in audit["events"])
    assert (
        record["focus_passed"]
        and not record["launch"]["events"]
        and record["launch"]["restore_requests"] == 0
    )
    for name, digest in record["result"]["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    record["fixture_current"] = record["result"]["fixture_sha256"] == sha(
        ROOT
        / "tests"
        / (
            "capture_scalar_layout.py"
            if label == "scalar"
            else "capture_action_parity.py"
        )
    )
    records.append(record)
    capture = BUILD / ("capture-" + source)
    for name in (
        ("rest", "red-reference-theme", "boolean-menu", "number-entry", "disabled")
        if label == "scalar"
        else states
    ):
        shutil.copy2(capture / (name + ".png"), OUT / (label + "-" + name + ".png"))
for name in ("light", "purple", "light-menu", "purple-menu"):
    shutil.copy2(
        BUILD / "capture-1x" / ("theme-" + name + ".png"),
        OUT / ("theme-" + name + ".png"),
    )


for name in (
    "reference-menu",
    "reference-in-context",
    "normalized-picker",
    "external-color-fields",
    "external-curve-fields",
    "external-ramp-fields",
):
    shutil.copy2(BUILD / "capture-1x" / (name + ".png"), OUT / (name + ".png"))


def gif(source, pattern, name, retain=False):
    files = sorted(source.glob(pattern))
    assert files
    frames = [Image.open(p).convert("RGB") for p in files]
    frames[0].save(
        MEDIA / (name + ".gif"),
        save_all=True,
        append_images=frames[1:],
        duration=1000 / 30,
        loop=0,
        optimize=False,
    )
    metadata = dict(
        source="Actual current-library Blender GPU frames",
        frames=len(files),
        frame_sha256={p.name: sha(p) for p in files},
        sha256=sha(MEDIA / (name + ".gif")),
        exact_match=False,
    )
    (MEDIA / (name + ".json")).write_text(json.dumps(metadata, indent=2) + "\n")
    if retain:
        (OUT / "frames").mkdir(exist_ok=True)
        for p in files:
            shutil.copy2(p, OUT / "frames" / p.name)
    return metadata


movies = {
    "components": gif(
        BUILD / "capture-1x", "core-*.png", "core-review-components-v2", True
    ),
    "actions": gif(BUILD / "capture-1x", "frame-*.png", "core-review-actions-v2"),
    "scalars": gif(BUILD / "capture-scalar", "frame-*.png", "core-review-scalars-v2"),
}
# A slideshow of current GPU theme captures, not simulated live switching.
theme_paths = [
    OUT / n
    for n in (
        "1x-rest.png",
        "theme-light.png",
        "theme-purple.png",
        "1x-hold-context.png",
        "theme-light-menu.png",
        "theme-purple-menu.png",
    )
]
theme_frames = [Image.open(p).convert("RGB") for p in theme_paths]
theme_file = MEDIA / "theme-support-v2.gif"
theme_frames[0].save(
    theme_file,
    save_all=True,
    append_images=theme_frames[1:],
    duration=1500,
    loop=0,
    optimize=False,
)
movies["themes"] = dict(
    source="Slideshow of fresh Blender GPU captures; synthetic light/purple inputs",
    frames=len(theme_frames),
    frame_sha256={p.name: sha(p) for p in theme_paths},
    sha256=sha(theme_file),
    exact_match=False,
)
theme_file.with_suffix(".json").write_text(
    json.dumps(movies["themes"], indent=2) + "\n"
)
current = [
    dict(
        title=title,
        path="docs/media/panels/" + name,
        report="docs/design/qa/core-review-v2/report.json",
    )
    for title, name in (
        ("Updated sliders, switches and numeric entry", "core-review-scalars-v2.gif"),
        (
            "Updated context menus, component fields and searchable enums",
            "core-review-components-v2.gif",
        ),
        ("Updated held menus and confirmation popovers", "core-review-actions-v2.gif"),
        (
            "Updated theme support: dark and synthetic light/purple",
            "theme-support-v2.gif",
        ),
    )
]
(OUT / "current-media.json").write_text(json.dumps(current, indent=2) + "\n")
report = dict(
    visual_acceptance=False,
    exact_match=False,
    full_custom_parity=False,
    current_library_sha256=records[0]["result"]["source_sha256"],
    gpu_runs=records,
    latest_context_evidence="../custom-contributions-v1/runtime.json",
    capture_regression=dict(
        initial_attempt="build/core-review-v2/run-1x/summary.json",
        issue="RegisteredMenu omitted the context argument added to contribution overrides.",
        fix="Pass the owning layout context; constructor regression test added.",
        pure_tests=254,
    ),
    browser_validation="Static local links and GIF decoding verified. Browser automation blocked file URLs; persistent open was queued, not confirmed. Interactive controls await user review.",
    focus=focus,
    native_batch_equal_frames=sum(
        r["result"]["native_text_batching_equal_frames"] for r in records
    ),
    movies=movies,
    limitations=[
        "Historical family pages remain historical, not recaptured by this pass.",
        "Light/purple are synthetic theme inputs over the same contrasting backdrop; no preferences saved.",
        "Theme inputs are synthetic; human contrast review remains pending.",
        "Exact generated-reference matching remains unaccepted; source scalar screenshot scale/background are unknown.",
        "No 4.2 or cross-platform runtime qualification.",
        "Other feature recordings remain in the historical archive; these five runs refresh the core review surfaces.",
    ],
)
(OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
checks = [
    (
        "scalar",
        "Sliders and switches",
        "Label, thin track, bubble handle, separate number entry; switches on every boolean. Check compact and disabled controls.",
    ),
    (
        "glass",
        "Glass",
        "Underlying text should soften; rims and refraction should remain visible through nested surfaces.",
    ),
    (
        "motion",
        "Bounce and menu text",
        "Every option and hint should move together. Check reveal, settle, disabled motion and the reduced wide-field amplitude.",
    ),
    (
        "scale",
        "Scale and typography",
        "Compare body/title/icon sizes across fields, component editors and narrow popovers at all captured scales.",
    ),
    (
        "theme",
        "Theme contrast",
        "Check dark, synthetic light and purple. Includes current shared light-menu contrast treatment.",
    ),
    (
        "context",
        "Right-click controls",
        "Inspect exact-owner component menus and contributed actions. Missing action families are listed in the context audit; this is not full parity acceptance.",
    ),
]
review = "".join(
    f'<section class="check"><h3>{title}</h3><p>{hint}</p><select data-key="{key}"><option value="pending">Not reviewed</option><option value="pass">Looks good</option><option value="fix">Needs work</option></select><textarea data-note="{key}" placeholder="What needs changing?"></textarea></section>'
    for key, title, hint in checks
)
gallery = "".join(
    f'<figure><figcaption>{html.escape(name)}</figcaption><img loading="lazy" data-state="{name}" src="1x-{name}.png"></figure>'
    for name in states
)
links = [
    ("pointer-decorators-v1", "Pointers and decorators"),
    ("collection-search-v1", "Collection search"),
    ("enum-properties-v2", "Enums and dropdowns"),
    ("registered-lists-v1", "Editable lists"),
    ("marking-menu-v5", "Pies and compound layouts"),
    ("context-menu-v6", "Full-menu text batching and motion"),
]
for path, _ in links:
    assert (OUT.parent / path / "index.html").exists(), path
families = " · ".join(
    f'<a href="../{path}/index.html">{title}</a>' for path, title in links
)
page = (
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Beyond UI · Core visual review</title>
<style>body{background:#191b20;color:#ecedf1;font:16px system-ui;margin:30px}a{color:#afd0ff}p{max-width:1100px;line-height:1.5}h1{font-size:28px}h2{margin-top:36px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,640px));gap:20px}figure{margin:0}figcaption{padding:10px 0}img{max-width:100%;height:auto}.note,.check{background:#262b34;padding:18px;border-radius:12px;margin:12px 0}select,button,textarea{font:inherit;padding:8px;background:#303847;color:#fff;border:1px solid #6c7a90;border-radius:6px}textarea{display:block;width:90%;margin-top:12px;min-height:55px}.check{max-width:1000px}input[type=range]{width:min(600px,90%)}small{color:#bdc4cf}</style>
<h1>Core visual QA · ready for your review</h1><p><a href="../overview/index.html">Feature overview and estimate</a> · <a href="report.json">Capture provenance and execution results</a> · <a href="../../../CORE_CONTEXT_AUDIT.md">Remaining right-click actions</a></p>
<div class="note"><strong>Fresh styling captures · 2026-10-30 · awaiting your acceptance.</strong><p>Blender 5.2.2 at 1×, 1.5× and 2×; Blender 5.1.2 at 1×. Shared BVT glass, theme roles and source motion. Five final GPU runs pass; BATCH_COUNT native-batched/unbatched frame pairs match. No test-process activation or focus restoration was observed in the capture audit. These are controlled offscreen GPU scenes, with earlier real host integration documented separately.</p><p>No full-parity or exact-reference claim. Historical family evidence is labelled below. The recordings include the current light-menu contrast treatment. No new image generations were needed; existing source/reference targets remain unchanged.</p></div>
<h2>1 · Sliders and switches</h2><div class="grid"><figure><figcaption>Your original BVT screenshots (unknown capture scale/background)</figcaption><img src="../../references/bvt-scalars-v1/slider.png"><img src="../../references/bvt-scalars-v1/switches.png"></figure><figure><figcaption>Fresh actual implementation · explicit red comparison palette</figcaption><img src="scalar-red-reference-theme.png"></figure></div><p>This side-by-side is a geometry/style review, not an equal-dimension pixel match.</p><img loading="lazy" src="../../../media/panels/core-review-scalars-v2.gif" alt="Actual slider, switch, entry and menu motion">
<h2>2 · Context menus, component fields and searchable enums</h2><img src="../../../media/panels/core-review-components-v2.gif" alt="Actual component and context-menu animations"><p>Frame-by-frame inspection: <output id="frameLabel">0</output></p><input id="frame" type="range" min="0" max="99" value="0"><div><img id="scrub" src="frames/core-000.png"></div>
<h2>3 · Held menus and confirmation popovers</h2><img loading="lazy" src="../../../media/panels/core-review-actions-v2.gif" alt="Actual hold and confirmation animation">
<h2>4 · Size, disabled motion and resting states</h2><label>Capture <select id="scale"><option value="1x">5.2.2 · 1×</option><option value="15x">5.2.2 · 1.5×</option><option value="2x">5.2.2 · 2×</option><option value="51">5.1.2 · 1×</option></select></label><p>Images fit this page for comparison; open the image to inspect original pixels.</p><div class="grid">GALLERY</div>
<h2>5 · Theme inputs over contrasting glass backdrops</h2><img loading="lazy" src="../../../media/panels/theme-support-v2.gif" alt="Fresh theme capture slideshow"><p>Factory active-theme capture plus synthetic light/purple inputs to the same renderer. Synthetic inputs do not represent installed presets. Glass stays enabled. Please flag text/highlight contrast; including the light-menu state.</p><div class="grid"><figure><figcaption>Active Blender theme</figcaption><img loading="lazy" src="1x-hold-context.png"></figure><figure><figcaption>Synthetic light · menu</figcaption><img loading="lazy" src="theme-light-menu.png"></figure><figure><figcaption>Synthetic purple · menu</figcaption><img loading="lazy" src="theme-purple-menu.png"></figure></div>
<h2>6 · Current field and picker styling</h2><p>Fresh Blender captures: external labels, inset fields, search padding, selected-row sizing and color-picker Alpha alignment.</p><div class="grid"><figure><figcaption>Searchable format menu</figcaption><img src="reference-menu.png"></figure><figure><figcaption>Color picker and Alpha</figcaption><img src="external-color-fields.png"></figure><figure><figcaption>Curve fields</figcaption><img src="external-curve-fields.png"></figure><figure><figcaption>Ramp fields</figcaption><img src="external-ramp-fields.png"></figure><figure><figcaption>Data picker in context</figcaption><img src="normalized-picker.png"></figure></div><h2>7 · Other core families (historical evidence)</h2><p>FAMILIES</p><p>These pages retain their original dates/source hashes and reference limitations. They are not presented as freshly recaptured. The earlier rejected context-menu generation is not an acceptance target.</p>
<h2>Your QA notes</h2><p>These notes stay in this browser when local storage is available. Export a JSON copy to preserve or share them; nothing is sent automatically.</p>CHECKS<button id="export">Export QA notes</button><p id="storage"></p>
<script>
const key='beyond-ui-core-review-v2';let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){document.querySelector('#storage').textContent='Local storage unavailable; export notes before leaving.'}
function collect(){const result={};document.querySelectorAll('[data-key]').forEach(e=>result[e.dataset.key]={status:e.value,note:document.querySelector('[data-note="'+e.dataset.key+'"]').value});return result}
document.querySelectorAll('[data-key]').forEach(e=>{e.value=saved[e.dataset.key]?.status||'pending';const note=document.querySelector('[data-note="'+e.dataset.key+'"]');note.value=saved[e.dataset.key]?.note||'';for(const control of [e,note])control.addEventListener('input',()=>{try{localStorage.setItem(key,JSON.stringify(collect()))}catch(err){document.querySelector('#storage').textContent='Use Export QA notes to preserve changes.'}})});
document.querySelector('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({page:key,review:collect()},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='beyond-ui-core-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
document.querySelector('#scale').onchange=e=>document.querySelectorAll('[data-state]').forEach(i=>i.src=e.target.value+'-'+i.dataset.state+'.png');document.querySelector('#frame').oninput=e=>{document.querySelector('#frameLabel').textContent=e.target.value;document.querySelector('#scrub').src='frames/core-'+String(e.target.value).padStart(3,'0')+'.png'};
</script></html>""".replace("GALLERY", gallery)
    .replace("FAMILIES", families)
    .replace("CHECKS", review)
)
page = page.replace("BATCH_COUNT", str(report["native_batch_equal_frames"]))
(OUT / "index.html").write_text(page)
print("Core visual review published; acceptance pending")
