"""Assemble unchanged Blender capture frames and a reference/implementation review."""

from pathlib import Path
import html, json, shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/design/qa/camkeys-studio-v6"
MEDIA = ROOT / "docs/media/panels"
MEDIA.mkdir(parents=True, exist_ok=True)
report = json.loads((OUT / "implementation/report.json").read_text())
revised = {
    "camkeys_main",
    "camkeys_linking",
    "flatten_falloff_popover",
    "lattice_auto_fov_modifier",
    "dolly_expressions",
}
audit = json.loads((OUT / "layout-audit.json").read_text())

def registered_image(url, size, bounds, extra=""):
    x, y, w, h = bounds
    return f'<div class="registered {extra}" style="aspect-ratio:{w}/{h}"><img loading="lazy" src="{url}" style="width:{size[0]/w*100:.8f}%;left:{-x/w*100:.8f}%;top:{-y/h*100:.8f}%"></div>'

current = []
cards = []
manifest = []
for row in report["records"]:
    slug = row["slug"]
    title = row["controls"][0]["label"]
    active = len(row["controls"]) > 1
    frames = sorted((ROOT / "build/studio-v6-motion" / slug).glob("*.png"))
    gif = MEDIA / f"camkeys-studio-v6-{slug}.gif"
    if frames and active:
        ims = [Image.open(p).convert("RGB") for p in frames]
        ims[0].save(
            gif,
            save_all=True,
            append_images=ims[1:],
            duration=[33] * (len(ims) - 1) + [1100],
            loop=0,
            optimize=True,
        )
        for im in ims:
            im.close()
        current.append(
            dict(title="CamKeys Studio · " + title, path=str(gif.relative_to(ROOT)))
        )
    version = "camkeys-studio-v2" if slug in revised else "camkeys-studio-v1"
    ref = f"../../references/{version}/{slug}.png"
    impl = f"implementation/{slug}.png"
    notes = "Actual scene data; real Blender GPU render over a diagnostic backdrop. Coral value fills, left-side Enum Bins switches, inset numeric cells, fixed-decimal unit labels and caret/info help actions are implemented through shared presentation hints. Generated glyphs and optical glass remain an explicit reference boundary."
    if slug == "lattice_auto_fov_modifier":
        notes = "Conditional fixture: a temporary lattice controller targets the existing Uraraka head mesh. Created only in the disposable test process; source scene unchanged."
    if slug == "dolly_expressions":
        notes = "Shape Keys mode in a disposable copy. The empty expression target list reflects the scene data; the prior VRM dependency notice is archived separately."
    if slug == "distance_falloff_popover":
        notes = "Seven real options retained. The incorrect shortened v2 generated variant is rejected; v1 is the comparison target."
    ref_size = Image.open(OUT / ref).size
    impl_size = Image.open(OUT / impl).size
    review = audit[slug]
    ref_bounds = review["reference_bounds_px"]
    impl_bounds = (32, 32, impl_size[0]-64, impl_size[1]-64)
    ref_view = registered_image(ref, ref_size, ref_bounds)
    impl_view = registered_image(impl, impl_size, impl_bounds)
    ratio = max(ref_bounds[3] / ref_bounds[2], impl_bounds[3] / impl_bounds[2])
    before = f"../camkeys-studio-v5/implementation/{slug}.png"
    before_size = Image.open(OUT / before).size
    before_view = registered_image(before, before_size, (32,32,before_size[0]-64,before_size[1]-64))
    changes = '<ul>' + ''.join('<li>'+html.escape(x)+'</li>' for x in review['fixes']) + '</ul>'
    limitations = '<ul>' + ''.join('<li>'+html.escape(x)+'</li>' for x in review['remaining']) + '</ul>'
    notes = "Fresh Blender capture using bui.style presets. Outer panel rims aligned at equal logical width; no image stretching or replacement pixels."
    embedded = "".join(
        f'<a href="embedded/{slug}-{part}.png">Embedded {part}</a> '
        for part in ("top", "lower")
        if (OUT / f"embedded/{slug}-{part}.png").exists()
    )
    scales = " · ".join(
        f'<a href="narrow/{slug}-{scale}x.png">260 px / {scale}×</a>'
        for scale in ("1", "1.5", "2")
        if (OUT / f"narrow/{slug}-{scale}x.png").exists()
        and slug != "lattice_auto_fov_modifier"
    )
    motion = (
        f'<details><summary>Actual Blender change-animation GIF</summary><img loading="lazy" src="../../../../media/panels/{gif.name}"></details>'
        if frames and active
        else ""
    )
    # Correct QA-relative media path below, without changing image contents.
    motion = motion.replace("../../../../media/", "../../../media/")
    cards.append(f'''<section id="{slug}"><h2>{html.escape(title)}</h2><p>{notes}</p>{changes}{embedded}<p>{scales}</p>
<div class="pair"><figure><figcaption>Generated reference · {version}</figcaption>{ref_view}</figure><figure><figcaption>Updated Blender implementation · 360 logical px / 2×</figcaption>{impl_view}</figure></div>
<details><summary>Registered overlay · reference opacity</summary><p>Outer panel bounds aligned; aspect ratios preserved. Registration uncertainty is about two source pixels. Different backdrops and artwork prevent a meaningful full-image pixel score.</p><input aria-label="Reference opacity" type="range" min="0" max="1" step=".01" value=".5" oninput="this.nextElementSibling.querySelector('.reference-layer').style.opacity=this.value"><div class="overlay" style="aspect-ratio:1/{ratio}"><div class="base-layer">{impl_view}</div><div class="reference-layer">{ref_view}</div></div></details>
<details><summary>Before this pass · v5</summary>{before_view}</details><details><summary>Remaining reference differences / later user corrections</summary>{limitations}</details>{motion}</section>''')
    manifest.append(
        dict(
            panel=row["panel"],
            slug=slug,
            reference_version=version,
            implementation=impl,
            reference=ref,
            exact_match=False,
            notes=notes,
            audit=review,
        )
    )
frames_path = ROOT / "build/studio-polish-appearance-frames"
if (frames_path / "frames.json").exists():
    rec = json.loads((frames_path / "frames.json").read_text())
    frames = [frames_path / r["file"] for r in rec]
    if frames:
        ims = [Image.open(p).convert("RGB") for p in frames]
        # These are explicit state snapshots, not a claim about measured animation timing.
        ims[0].save(
            MEDIA / "camkeys-studio-v6-appearance.gif",
            save_all=True,
            append_images=ims[1:],
            duration=850,
            loop=0,
        )
        for im in ims:
            im.close()
        shutil.copyfile(frames[0], OUT / "appearance.png")
        current.append(
            dict(
                title="CamKeys Studio · live preset edits and owner menu snapshots",
                path="docs/media/panels/camkeys-studio-v6-appearance.gif",
            )
        )
nav = " · ".join(
    f'<a href="#{r["slug"]}">{html.escape(r["controls"][0]["label"])}</a>'
    for r in report["records"]
)
page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CamKeys Studio · Design review</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#151c22;color:#f5f2ec;font:16px/1.55 system-ui}main{max-width:1450px;margin:auto;padding:36px 28px}a{color:#76d7c3}h1{font-size:36px;line-height:1.1}h2{font-size:23px}p{max-width:1000px;color:#bdc8ce}.logo{width:168px;height:168px;object-fit:contain}.logo-previews{display:flex;gap:24px;align-items:center}.logo-previews img{width:144px;height:144px;background:#28323b;border-radius:24px}.logo-previews .circle{border-radius:50%}.hero,section{padding:25px;margin:24px 0;background:#202930;border:1px solid #45545d;border-radius:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}figure{margin:0}figcaption{font-size:14px;margin:12px 0;color:#aebfc7}img{width:100%;height:auto;display:block;border-radius:10px}details{margin-top:18px}summary{cursor:pointer;color:#f4a28c}details>img,.overlay{max-width:700px}.overlay{position:relative;overflow:hidden}.registered{position:relative;overflow:hidden;width:100%;border-radius:8px}.registered img{position:absolute;max-width:none;height:auto;border-radius:0}.base-layer,.reference-layer{position:absolute;top:0;left:0;width:100%}.reference-layer{opacity:.5;pointer-events:none}details>.registered{max-width:700px}input[type=range]{width:min(700px,100%)}nav{line-height:2.2}.tag{display:inline-block;background:#34554e;padding:5px 12px;border-radius:20px;margin-right:8px;font-size:13px}@media(max-width:750px){.pair{grid-template-columns:1fr}main{padding:12px}section{padding:14px}}
</style><main><img class="logo" src="../../references/camkeys-logo-v4/02-morph-body.png" alt="CamKeys logo"><h1>CamKeys Studio</h1><details><summary>Compact logo · square and circle previews</summary><div class="logo-previews"><img src="../../references/camkeys-logo-v4/02-morph-body.png" alt="Square icon footprint"><img class="circle" src="../../references/camkeys-logo-v4/02-morph-body.png" alt="Circular icon footprint"></div><p>Selected: candidate 2, Morphing camera. Camera silhouettes and artist-recognizable deformation motifs replace the earlier abstract lens mark.</p></details><p>A consumer-owned coral and mint preset over Beyond UI's shared glass, motion, binding and menu systems.</p><div class="hero"><span class="tag">337 unit tests</span><span class="tag">Blender 5.1.2 + 5.2.2</span><span class="tag">Close visual match · review ready</span><p>Studio v6 adds reusable parent/value glass surfaces, clearer selection rims, subtle list dividers, comfortable text-button padding, and missing coral/mint action presets. All 12 panel/popover states are recaptured against their immutable generated references. No product-specific styling is present in the shared library. The styling system and live Appearance dialog remain available. These are real Blender renders, not HTML imitations. Generated targets remain separate: font/glyph details, optical rims, some spacing and backdrop differences are still visible. No panel is marked pixel-exact.</p><p><a href="../../../STYLING.md">Preset integration guide</a> · <a href="report.json">Validation and boundaries</a> · <a href="../overview/index.html">Updated work estimate</a></p></div><p><a href="../../../INLINE_STYLES.md">Copy-ready bui.style() guide</a> · <a href="../camkeys-studio-v4/icon-candidates.html">All four icon candidates</a></p><nav>NAV</nav><section><h2>Live customization</h2><p>Colors, chrome opacity, text size, motion strength/speed and disable controls; Follow Blender Colors and Cancel restoration. GIF shows recorded state snapshots retained from Studio v2; the dialog was execution-tested with the new action presets, but that GIF was not recaptured in v6.</p><img style="max-width:700px" src="../../../media/panels/camkeys-studio-v6-appearance.gif"></section>CARDS</main></html>"""
page = (
    page.replace("NAV", nav)
    .replace("CARDS", "".join(cards))
    .replace("../../../STYLING.md", "../../../STYLING.md")
)
(OUT / "index.html").write_text(page)
(OUT / "panels.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "current-media.json").write_text(json.dumps(current, indent=2) + "\n")
print(f"{len(manifest)} panel states; {len(current)} real capture GIFs")
