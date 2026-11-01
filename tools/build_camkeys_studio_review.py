"""Assemble unchanged Blender capture frames and a reference/implementation review."""

from pathlib import Path
import html, json, shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/design/qa/camkeys-studio-v1"
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
current = []
cards = []
manifest = []
for row in report["records"]:
    slug = row["slug"]
    title = row["controls"][0]["label"]
    active = len(row["controls"]) > 1
    frames = sorted((ROOT / "build/studio-motion-frames" / slug).glob("*.png"))
    gif = MEDIA / f"camkeys-studio-{slug}.gif"
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
    notes = "Actual scene data; real Blender GPU render over a diagnostic backdrop. Geometry, source icons and glass finish still require reference acceptance."
    if slug == "lattice_auto_fov_modifier":
        notes = "Conditional fixture: a temporary lattice controller targets the existing Uraraka head mesh. Created only in the disposable test process; source scene unchanged."
    if slug == "dolly_expressions":
        notes = "Shape Keys mode in a disposable copy. The empty expression target list reflects the scene data; the prior VRM dependency notice is archived separately."
    if slug == "distance_falloff_popover":
        notes = "Seven real options retained. The incorrect shortened v2 generated variant is rejected; v1 is the comparison target."
    ref_size = Image.open(OUT / ref).size
    impl_size = Image.open(OUT / impl).size
    ratio = max(ref_size[1] / ref_size[0], impl_size[1] / impl_size[0])
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
    cards.append(f'''<section id="{slug}"><h2>{html.escape(title)}</h2><p>{notes}</p>{embedded}<p>{scales}</p>
<div class="pair"><figure><figcaption>Generated target · {version}</figcaption><img loading="lazy" src="{ref}"></figure><figure><figcaption>Actual Blender implementation · 360 logical px / 2×</figcaption><img loading="lazy" src="{impl}"></figure></div>
<details><summary>Overlay comparison</summary><p>Normalized to equal width, original aspect ratios retained. This exposes differences; it is not an exact-match certification.</p><input aria-label="Reference opacity" type="range" min="0" max="1" step=".01" value=".5" oninput="this.nextElementSibling.querySelector('.over').style.opacity=this.value"><div class="overlay" style="aspect-ratio:1/{ratio}"><img src="{impl}" loading="lazy"><img class="over" src="{ref}" loading="lazy"></div></details>{motion}</section>''')
    manifest.append(
        dict(
            panel=row["panel"],
            slug=slug,
            reference_version=version,
            implementation=impl,
            reference=ref,
            exact_match=False,
            notes=notes,
        )
    )
frames_path = ROOT / "build/studio-appearance-final-frames"
if (frames_path / "frames.json").exists():
    rec = json.loads((frames_path / "frames.json").read_text())
    frames = [frames_path / r["file"] for r in rec]
    if frames:
        ims = [Image.open(p).convert("RGB") for p in frames]
        # These are explicit state snapshots, not a claim about measured animation timing.
        ims[0].save(
            MEDIA / "camkeys-studio-appearance.gif",
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
                path="docs/media/panels/camkeys-studio-appearance.gif",
            )
        )
nav = " · ".join(
    f'<a href="#{r["slug"]}">{html.escape(r["controls"][0]["label"])}</a>'
    for r in report["records"]
)
page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CamKeys Studio · Design review</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#151c22;color:#f5f2ec;font:16px/1.55 system-ui}main{max-width:1450px;margin:auto;padding:36px 28px}a{color:#76d7c3}h1{font-size:36px;line-height:1.1}h2{font-size:23px}p{max-width:1000px;color:#bdc8ce}.logo{width:min(500px,90%)}.hero,section{padding:25px;margin:24px 0;background:#202930;border:1px solid #45545d;border-radius:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}figure{margin:0}figcaption{font-size:14px;margin:12px 0;color:#aebfc7}img{width:100%;height:auto;display:block;border-radius:10px}details{margin-top:18px}summary{cursor:pointer;color:#f4a28c}details>img,.overlay{max-width:700px}.overlay{position:relative;overflow:hidden}.over{position:absolute;top:0;left:0;opacity:.5;pointer-events:none}input[type=range]{width:min(700px,100%)}nav{line-height:2.2}.tag{display:inline-block;background:#34554e;padding:5px 12px;border-radius:20px;margin-right:8px;font-size:13px}@media(max-width:750px){.pair{grid-template-columns:1fr}main{padding:12px}section{padding:14px}}
</style><main><img class="logo" src="../../references/camkeys-studio-v1/logo.png" alt="CamKeys logo"><h1>CamKeys Studio</h1><p>A consumer-owned coral and mint preset over Beyond UI's shared glass, motion, binding and menu systems.</p><div class="hero"><span class="tag">305 unit tests</span><span class="tag">Blender 5.1.2 + 5.2.2</span><span class="tag">Reference acceptance open</span><p>The styling system and live Appearance dialog are implemented. These are real Blender renders, not HTML imitations. Generated targets remain separate: font/glyph details, optical rims, some spacing and backdrop differences are still visible. No panel is marked pixel-exact.</p><p><a href="../../../../STYLING.md">Preset integration guide</a> · <a href="report.json">Validation and boundaries</a> · <a href="../overview/index.html">Updated work estimate</a></p></div><nav>NAV</nav><section><h2>Live customization</h2><p>Colors, chrome opacity, text size, motion strength/speed and disable controls; Follow Blender Colors and Cancel restoration. GIF shows recorded state snapshots.</p><img style="max-width:700px" src="../../../media/panels/camkeys-studio-appearance.gif"></section>CARDS</main></html>"""
page = (
    page.replace("NAV", nav)
    .replace("CARDS", "".join(cards))
    .replace("../../../../STYLING.md", "../../../STYLING.md")
)
(OUT / "index.html").write_text(page)
(OUT / "panels.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "current-media.json").write_text(json.dumps(current, indent=2) + "\n")
print(f"{len(manifest)} panel states; {len(current)} real capture GIFs")
