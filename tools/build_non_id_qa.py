"""Package non-ID pointer evidence and compare the unchanged ID control fixture."""

import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/non-id-pointers"
OUT = ROOT / "docs/design/qa/non-id-pointers-v1"
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for prefix, fixture in (
    ("", "capture_non_id_pointers"),
    ("id-", "capture_search_popover"),
):
    for suffix in ("", "-51"):
        run = BUILD / f"{prefix}capture-run{suffix}"
        assert all(
            row["passed"] for row in json.loads((run / "summary.json").read_text())
        )
        record = json.loads(
            (BUILD / f"{prefix}capture{suffix}/capture.json").read_text()
        )
        assert record["passed"] and record["stable_resources"]
        if prefix == "":
            assert record["consumer_fixture_sha256"] == sha(
                ROOT / "tests/non_id_fixture.py"
            )
        assert record["native_text_batching_equal_frames"] == 100
        assert record["fixture_sha256"] == sha(ROOT / f"tests/{fixture}.py")
        for name, digest in record["source_sha256"].items():
            assert sha(ROOT / name) == digest, name
        shutil.copy2(
            BUILD / f"{prefix}capture{suffix}/capture.json",
            OUT / f"{prefix}capture{suffix}.json",
        )
        shutil.copy2(run / "blender-0.log", OUT / f"{prefix}capture{suffix}.log")
comparison = {}
for name in ("rest", "picker", "filtered", "field-context", "disabled"):
    shutil.copy2(BUILD / "capture" / f"{name}.png", OUT / f"{name}.png")
    before = ROOT / "docs/design/qa/search-popover-v1" / f"{name}.png"
    after = BUILD / "id-capture" / f"{name}.png"
    equal = (
        ImageChops.difference(
            Image.open(before).convert("RGB"), Image.open(after).convert("RGB")
        ).getbbox()
        is None
    )
    assert equal, name
    comparison[name] = dict(
        rgb_pixels_equal=equal, before_sha256=sha(before), after_sha256=sha(after)
    )
shutil.copy2(BUILD / "id-capture/rest.png", OUT / "id-rest.png")
(OUT / "id-regression.json").write_text(json.dumps(comparison, indent=2) + "\n")
shutil.copy2(BUILD / "source/audit.json", OUT / "api-source-audit.json")
frames = [
    Image.open(p).convert("RGB")
    for p in sorted((BUILD / "capture").glob("frame-*.png"))
]
assert len(frames) == 100
media = ROOT / "docs/media/panels/non-id-pointers-v1.gif"
frames[0].save(
    media,
    save_all=True,
    append_images=frames[1:],
    duration=33,
    loop=0,
    optimize=False,
    disposal=2,
)
media.with_suffix(".json").write_text(
    json.dumps(
        dict(
            source="Actual Blender production frames; no generated pixels",
            capture="../../design/qa/non-id-pointers-v1/capture.json",
            sha256=sha(media),
        ),
        indent=2,
    )
    + "\n"
)
for folder in (
    "runtime",
    "windowed",
    "pointer-regression",
    "search-regression",
    "popover-regression",
    "regression",
    "menu-windowed",
    "pointer-windowed",
):
    assert all(
        row["passed"]
        for row in json.loads((BUILD / folder / "summary.json").read_text())
    )
    for i, version in enumerate(("52", "51")):
        path = BUILD / folder / f"result-{i}.json"
        assert json.loads(path.read_text())["passed"]
        shutil.copy2(path, OUT / f"{folder}-{version}.json")
        shutil.copy2(
            BUILD / folder / f"blender-{i}.log", OUT / f"{folder}-{version}.log"
        )
(
    OUT / "index.html"
).write_text("""<!doctype html><meta charset="utf-8"><title>Non-ID pointers · QA v1</title>
<style>body{background:#151719;color:#eee;font:15px system-ui;margin:28px}a{color:#8bcafb}img{max-width:100%;height:auto}p{max-width:1050px;line-height:1.6}h2{margin-top:36px}.pair{display:flex;gap:16px;flex-wrap:wrap}.pair figure{margin:0;max-width:640px}figcaption{padding:8px 0}</style>
<h1>Non-ID pointers and collection-owned properties</h1>
<p>Active bones and nodes now use the same custom field, strong-glass picker, source spring and owner-aware menus as ID pointers. Both prop and prop_search support named non-ID targets through an explicit host candidate/poll policy and mandatory revision and transaction callbacks. RNA collection wrappers receive exact owner/path bindings.</p>
<img src="../../../media/panels/non-id-pointers-v1.gif" alt="Actual non-ID node pointer selection, search and candidate menu motion">
<h2>Rest / filtered picker</h2><div class="pair"><figure><img src="rest.png" alt="Non-ID pointer and search fields"><figcaption>Closed fields · no candidate enumeration</figcaption></figure><figure><img src="filtered.png" alt="Filtered node picker"><figcaption>500 nodes · virtualized rows</figcaption></figure></div>
<h2>Exact collection property menu</h2><img src="field-context.png" alt="Context actions for nodes.active">
<p>Execution on Blender 5.1.2 and 5.2.2 covers Bone/Node assignment, rollback, revision changes, renames, removals, stale context actions, clear, copy paths and deletion of the owning ID. Real window input covers immediate typing, selection, candidate menus, compact search, cancellation and quiescent teardown. Rejected pointer commits preserve the editor. Candidate Copy Name now rechecks collection membership too.</p>
<p>Both versions retain one backdrop production, one strong blur, five offscreens and recorded layout/font/shader/batch identities. All 100 sampled frames per runtime match with native text batching enabled and disabled. No per-frame capture, blur or candidate scan is introduced.</p>
<h2>Existing ID controls: before / after</h2><div class="pair"><figure><img src="../search-popover-v1/rest.png" alt="Previous ID/search fixture"><figcaption>Previous published fixture</figcaption></figure><figure><img src="id-rest.png" alt="Current identical ID/search fixture"><figcaption>Current implementation · identical RGB pixels</figcaption></figure></div>
<p>Resting, open, filtered, context-menu and disabled snapshots all retain identical RGB pixels in the unchanged 5.2.2 fixture. Equivalent-workload timing records are retained; separate process runs are a regression check, not a controlled BVT performance comparison.</p>
<p><strong>Parity remains partial.</strong> These are implementation captures using existing control geometry, not approved generated-reference matches. Native button-pointer callbacks for collection owners, unqualified setter side effects, type-specific icons, unnamed/nonassignable targets, unexposed polls without host adapters, eyedroppers/drag-drop, complete keyboard traversal, all theme/DPI states and platform validation remain open. Blender 4.2 was source-reviewed, not executed here.</p>
<p><a href="capture.json">5.2 non-ID capture/timings</a> · <a href="capture-51.json">5.1 non-ID capture/timings</a> · <a href="id-regression.json">ID pixel comparison</a> · <a href="id-capture.json">5.2 ID regression timings</a> · <a href="id-capture-51.json">5.1 ID regression timings</a> · <a href="runtime-52.json">RNA checks</a> · <a href="windowed-52.json">Actual window input</a> · <a href="api-source-audit.json">Official source evidence</a> · <a href="../../../POINTERS_AND_DECORATORS.md">Integration and remaining gaps</a></p>""")
print(OUT)
