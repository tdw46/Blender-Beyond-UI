"""Package host-scale evidence; preserve all earlier references and galleries."""

import hashlib
import html
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/ui-scale"
OUT = ROOT / "docs/design/qa/ui-scale-v1"
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def capture(folder, run, fixture, *, overview=False):
    assert all(row["passed"] for row in read(BUILD / run / "summary.json"))
    record = read(BUILD / folder / "capture.json")
    assert record["passed"]
    assert record["fixture_sha256"] == sha(ROOT / f"tests/{fixture}.py")
    for name, digest in record["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    if overview:
        assert record["native_text_batching_equal"] == len(record["rows"]) == 39
        assert all(row["stable_resources"] for row in record["rows"])
    else:
        assert record["stable_resources"]
        assert record["native_text_batching_equal_frames"] == 100
        if "consumer_fixture_sha256" in record:
            assert record["consumer_fixture_sha256"] == sha(ROOT / "tests/non_id_fixture.py")
    shutil.copy2(BUILD / folder / "capture.json", OUT / f"{folder}.json")
    shutil.copy2(BUILD / run / "blender-0.log", OUT / f"{folder}.log")
    return record


for suffix in ("", "-51"):
    capture(f"capture{suffix}", f"capture-run{suffix}", "capture_ui_scale", overview=True)
    capture(f"popover{suffix}", f"popover-run{suffix}", "capture_non_id_pointers")
capture("target", "target-run", "capture_search_popover")
record = read(BUILD / "capture/capture.json")
for row in record["rows"]:
    shutil.copy2(BUILD / "capture" / row["image"], OUT / row["image"])
for folder in ("popover", "target"):
    for name in ("rest", "picker", "filtered", "field-context", "disabled"):
        shutil.copy2(BUILD / folder / f"{name}.png", OUT / f"{folder}-{name}.png")

for folder in ("non-id", "pointer", "search", "popover", "runtime", "scaling",
               "non-id-windowed", "picker-windowed", "pointer-windowed", "menu-windowed"):
    assert all(row["passed"] for row in read(BUILD / folder / "summary.json"))
    for i, version in enumerate(("52", "51")):
        for source, dest in ((f"result-{i}.json", f"checks-{folder}-{version}.json"),
                             (f"blender-{i}.log", f"checks-{folder}-{version}.log")):
            shutil.copy2(BUILD / folder / source, OUT / dest)

frames = [Image.open(p).convert("RGB") for p in sorted((BUILD / "popover").glob("frame-*.png"))]
assert len(frames) == 100
media = ROOT / "docs/media/panels/ui-scale-v1.gif"
frames[0].save(media, save_all=True, append_images=frames[1:], duration=33,
               loop=0, optimize=False, disposal=2)
media.with_suffix(".json").write_text(json.dumps({
    "source": "Actual Blender production frames; no generated pixels",
    "capture": "../../design/qa/ui-scale-v1/popover.json", "sha256": sha(media)
}, indent=2) + "\n")

comparison = {"exact_match": False, "change": "User-requested host-relative scale correction; prior oversized presentation superseded",
              "pairs": []}
for folder, before in (("popover", "non-id-pointers-v1"), ("target", "search-popover-v1")):
    comparison["pairs"].append({
        "before": f"../{before}/picker.png", "after": f"{folder}-picker.png",
        "before_sha256": sha(OUT.parent / before / "picker.png"),
        "after_sha256": sha(OUT / f"{folder}-picker.png"),
        "dimensions": [640, 560], "fixture_unchanged": True,
    })
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")

cards = "\n".join(
    f'<figure><figcaption>{html.escape(row["title"])}</figcaption>'
    f'<a class="capture" data-slug="{row["slug"]}" href="{row["image"]}">'
    f'<img loading="lazy" src="{row["image"]}" alt="{html.escape(row["title"])} at host scale"></a></figure>'
    for row in record["rows"] if row["dpi"] == 1
)
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Consistent UI scale · QA v1</title>
<style>
body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}p{max-width:1050px;line-height:1.6}
h2{margin-top:36px}img{max-width:100%;height:auto;display:block}figure{margin:0}figcaption{padding:10px 0}
.pair{display:grid;grid-template-columns:repeat(2,minmax(0,640px));gap:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,380px));gap:20px}
.grid img{width:380px}select{font:inherit;padding:6px;background:#292c30;color:white;border:1px solid #73777d;border-radius:6px}
@media(max-width:760px){.pair{grid-template-columns:1fr}body{margin:16px}}
</style>
<h1>Consistent control and popover scale</h1>
<p>Active Node, collection search, Target and color popovers now follow the surrounding panel's text scale. Wider panels no longer enlarge them. Standard body text is 11 logical units and section titles are 12; compound cards normally render at 315 logical units wide. Original BVT glass, theme roles, spring motion and exact-owner context menus remain shared.</p>
<h2>Active Node · before / corrected</h2>
<div class="pair"><figure><img src="../non-id-pointers-v1/picker.png" alt="Oversized Active Node popover before correction"><figcaption>Before · width-driven scale</figcaption></figure><figure><img src="popover-picker.png" alt="Active Node scaled consistently with its panel"><figcaption>Corrected · host-relative scale</figcaption></figure></div>
<h2>Target / collection search · before / corrected</h2>
<div class="pair"><figure><img src="../search-popover-v1/picker.png" alt="Oversized Target and collection search picker"><figcaption>Before · same 640 × 560 fixture</figcaption></figure><figure><img src="target-picker.png" alt="Corrected Target and collection search picker"><figcaption>Corrected · same geometry and input transform</figcaption></figure></div>
<h2>Opening, filtering and context menu motion</h2>
<img src="../../../media/panels/ui-scale-v1.gif" alt="Actual corrected Blender picker animation and candidate context menu">
<p>All 100 animation frames match with native text batching enabled and disabled on each tested runtime. One shared backdrop production, one blur and five offscreens remain retained. These are Blender captures, not browser recreations.</p>
<h2>Every implemented control family</h2>
<p>Each capture includes surrounding standard fields for scale comparison. Choose the physical rendering scale; images stay at the same logical display width below. Click an image for its full-resolution file. This audits rendered scale, not every OS display configuration.</p>
<label for="dpi">Capture scale </label><select id="dpi"><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>
<div class="grid">CARDS</div>
<h2>Evidence and limits</h2>
<p>39 captures per Blender version cover 13 families at three scales, with byte-identical native/standalone text output and stable warm rendering resources. RNA and window-input checks cover pointer/search selection, color edits and cancellation, exact palette ownership, resized clips, context actions and teardown. Large progress percentages intentionally remain larger data readouts.</p>
<p>Blender 5.1.2 and 5.2.2 / macOS arm64 / Metal / factory active theme. Existing generated references and older galleries remain immutable; Tyler's scale correction supersedes their oversized presentation. <strong>Exact generated-reference acceptance and full API parity remain open.</strong> Blender 4.2 execution, other platforms and arbitrary tiny viewport readability are not established here.</p>
<p><a href="capture.json">5.2 all-family capture/timings</a> · <a href="capture-51.json">5.1 all-family capture/timings</a> · <a href="popover.json">5.2 Active Node motion/timings</a> · <a href="popover-51.json">5.1 Active Node motion/timings</a> · <a href="target.json">Target/search capture</a> · <a href="comparison.json">Before/after provenance</a> · <a href="checks-scaling-52.json">Scale/input checks</a> · <a href="../../../UI_SCALING.md">Sizing contract</a></p>
<script>document.getElementById('dpi').addEventListener('change',event=>{for(const link of document.querySelectorAll('a.capture')){const file=`${link.dataset.slug}-${event.target.value}x.png`;link.href=file;link.querySelector('img').src=file;}});</script></html>'''
(OUT / "index.html").write_text(page.replace("CARDS", cards))
print(OUT)
