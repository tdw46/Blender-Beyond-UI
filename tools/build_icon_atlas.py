"""Offline build of source Blender glyphs; production reads only the bundled atlas."""

import ast, concurrent.futures, hashlib, io, json, urllib.request, zlib
from pathlib import Path
import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "beyond_ui/assets/icons"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = OUT / "svg"
SOURCE.mkdir(exist_ok=True)
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--consumer", type=Path, help="Optional add-on to discover additional literal icons"
)
args = parser.parse_args()
icons = set(json.loads((OUT / "atlas.json").read_text())["entries"])
if args.consumer:
    for p in args.consumer.glob("*.py"):
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n, ast.keyword) and n.arg == "icon":
                icons.update(
                    c.value
                    for c in ast.walk(n.value)
                    if isinstance(c, ast.Constant)
                    and isinstance(c.value, str)
                    and c.value.isupper()
                )
version = "v5.2.2"
if args.consumer:
    url = f"https://api.github.com/repos/blender/blender/contents/release/datafiles/icons_svg?ref={version}"
    known = {
        r["name"] for r in json.loads(urllib.request.urlopen(url, timeout=30).read())
    }
    icons = {name for name in icons if name.lower() + ".svg" in known}


def fetch(name):
    url = f"https://raw.githubusercontent.com/blender/blender/{version}/release/datafiles/icons_svg/{name.lower()}.svg"
    p = SOURCE / (name + ".svg")
    if not p.exists():
        try:
            p.write_bytes(urllib.request.urlopen(url, timeout=30).read())
        except Exception as error:
            raise RuntimeError(name + " " + url) from error
    return name, p, url


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows = sorted(pool.map(fetch, icons))
size = 64
cols = 8
height = ((len(rows) + cols - 1) // cols) * size
atlas = Image.new("RGBA", (cols * size, height))
entries = {}
ink_bounds = {}
sources = {}
for i, (name, p, url) in enumerate(rows):
    tile = Image.open(
        io.BytesIO(resvg_py.svg_to_bytes(svg_path=str(p), width=size, height=size))
    ).convert("RGBA")
    bounds = tile.getchannel("A").getbbox()
    assert bounds, name
    x = (i % cols) * size
    y = (i // cols) * size
    atlas.paste(tile, (x, y))
    entries[name] = [x, y, size, size]
    ink_bounds[name] = list(bounds)
    sources[name] = dict(url=url, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
atlas.save(OUT / "atlas.png")
(OUT / "atlas.rgba.zlib").write_bytes(
    zlib.compress(atlas.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes(), 9)
)
(OUT / "atlas.json").write_text(
    json.dumps(
        dict(dimensions=list(atlas.size), entries=entries, ink_bounds=ink_bounds),
        indent=2,
    )
    + "\n"
)
(OUT / "provenance.json").write_text(
    json.dumps(
        dict(
            source="Blender official source",
            version=version,
            license="GPL-2.0-or-later (Blender repository); distributed here under GPL-3.0-or-later",
            generator="tools/build_icon_atlas.py; resvg-py",
            sources=sources,
        ),
        indent=2,
    )
    + "\n"
)
print(f"{len(rows)} original Blender icons, one {atlas.size} atlas")
