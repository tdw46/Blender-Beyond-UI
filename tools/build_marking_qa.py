"""Package observed marking-menu results without converting diagnostics to acceptance."""

import hashlib
import ast
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/marking-menu"
OUT = ROOT / "docs/design/qa/marking-menu-v1"
OUT.mkdir(parents=True, exist_ok=True)
CAPTURE = BUILD / "capture-1x"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


capture = read(CAPTURE / "capture.json")
assert capture["passed"] and capture["stable_resources"]
post_capture = []
for path, digest in capture["source_sha256"].items():
    if sha(ROOT / path) != digest:
        # The later directional hit correction changes input only; retain the
        # exact captured source and expose the difference, never relabel frames.
        assert path == "beyond_ui/pie_menu.py", path
        snapshot = OUT / "captured-pie-menu.py.txt"
        assert sha(snapshot) == digest

        def without_event(source):
            tree = ast.parse(source)
            for cls in tree.body:
                if isinstance(cls, ast.ClassDef) and cls.name == "PieMenu":
                    cls.body = [
                        n
                        for n in cls.body
                        if not isinstance(n, ast.FunctionDef) or n.name != "event"
                    ]
            return ast.dump(tree)

        assert without_event(snapshot.read_text()) == without_event(
            (ROOT / path).read_text()
        )
        post_capture.append(
            dict(
                path=path,
                current_sha256=sha(ROOT / path),
                note="Event-only visible-petal priority correction after capture; background/unit tested. No new GPU capture.",
            )
        )
assert capture["fixture_sha256"] == sha(ROOT / "tests/capture_pie.py")
assert capture["fixture_helper_sha256"] == sha(ROOT / "tests/pie_fixture.py")
assert capture["native_text_batching_equal_frames"] == 60
assert capture["retained_resources"]["productions"] == 1
assert capture["retained_resources"]["blur"] == 1
states = (
    "rest",
    "pie",
    "nested-search",
    "row-context",
    "numeric-edit",
    "narrow",
    "disabled",
    "list-before",
    "list-after",
)
for name in states:
    shutil.copy2(CAPTURE / (name + ".png"), OUT / (name + ".png"))
shutil.copy2(CAPTURE / "capture.json", OUT / "capture.json")
shutil.copy2(BUILD / "capture-1x-run/summary.json", OUT / "capture-launch.json")
shutil.copy2(BUILD / "focus-first.json", OUT / "focus-windowed.json")
shutil.copy2(BUILD / "focus-background.json", OUT / "focus-background.json")
for name in ("runtime", "runtime-51", "general", "general-51"):
    results = read(BUILD / name / "summary.json")
    assert all(r["passed"] for r in results)
    shutil.copy2(BUILD / name / "result-0.json", OUT / (name + ".json"))

frames = [Image.open(p).convert("RGB") for p in sorted(CAPTURE.glob("frame-*.png"))]
assert len(frames) == 60
gif = ROOT / "docs/media/panels/marking-menu-v1.gif"
frames[0].save(
    gif,
    save_all=True,
    append_images=frames[1:],
    duration=[30, 30, 40] * 20,
    loop=0,
    optimize=False,
    disposal=2,
)
gif.with_suffix(".json").write_text(
    json.dumps(
        dict(
            source="Actual Blender GPU frames, no generated pixels",
            source_frames=60,
            sha256=sha(gif),
            capture="../../design/qa/marking-menu-v1/capture.json",
        ),
        indent=2,
    )
    + "\n"
)
comparison = dict(
    exact_match=False,
    full_custom_parity=False,
    native_text_batching_equal_frames=60,
    ordinary_list_before_after_equal=sha(OUT / "list-before.png")
    == sha(OUT / "list-after.png"),
    timings=capture["timings"],
    focus_acceptance=False,
    post_capture_changes=post_capture,
    focus_note="Tyler confirmed the owned test Blender process stole focus. Shared runner blocks all windowed tests pending safe requalification. Subsequent headless audit passed.",
    unverified=[
        "Generated-reference and visual acceptance",
        "Compound pie slots",
        "Nested radial definitions",
        "Native preference/timing/edge equivalence",
        "Additional scales, themes and runtime GPU coverage",
        "Blender 4.2 runtime",
    ],
)
(OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
cards = "".join(
    f'<figure><img src="{name}.png" alt="{name}"><figcaption>{name.replace("-", " ")}</figcaption></figure>'
    for name in states
)
(OUT / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>Beyond UI · Marking menus</title>
<style>body{background:#17191c;color:#e6e7e9;font:15px system-ui;margin:32px;max-width:1500px}h1{font-size:26px}p{max-width:1000px;line-height:1.6}a{color:#9cd4ee}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:20px}figure{margin:0;background:#22262a;padding:12px;border-radius:12px}img{display:block;width:100%;height:auto}figcaption{padding:8px}.notice{border-left:3px solid #e0ae64;padding:12px;background:#29251e}</style>
<h1>Marking menus · implementation QA</h1>
<p>Eight directional slots, release-owned clicks, exact-property right-click menus, searchable children and the shared BVT glass/theme/spring painter. These are actual Blender 5.2.2 Metal frames at 1×. Visual acceptance and generated-reference matching remain open.</p>
<p class="notice">Focus gate not accepted: the test process became active despite the no-focus launch flag. Tyler confirmed an unsolicited focus steal; the shared runner now blocks all windowed tests pending safe requalification. Background execution passed on 5.1.2 and 5.2.2 with no activation observed. This diagnostic capture is retained for transparent review.</p>
<p><a href="../../../MARKING_MENUS.md">Integration and remaining gaps</a> · <a href="comparison.json">Comparison and timings</a> · <a href="focus-windowed.json">Window focus audit</a> · <a href="focus-background.json">Background focus audit</a></p>
<figure style="max-width:720px"><img src="../../../media/panels/marking-menu-v1.gif" alt="Actual marking menu animation"><figcaption>Opening, hover, exact-row context menu, and back navigation. All text follows the shared transform.</figcaption></figure>
<h2>States</h2><div class="grid">"""
    + cards
    + """</div><p>The ordinary list before/after images are byte-identical. Seven pie petals share one retained backdrop revision and one strong-blur production. Timing samples measure warm CPU paint submission only, excluding readback.</p>"""
)
print(OUT)
