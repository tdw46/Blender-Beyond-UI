"""Offline themed SVG layers. Run with Pillow and resvg-py; no runtime SVG I/O."""
from pathlib import Path
import copy, io, json, zlib, xml.etree.ElementTree as ET
import resvg_py
from PIL import Image

root = Path(__file__).resolve().parents[1] / 'beyond_ui/assets/icons/duotone'
size = 128
rows = sorted(root.glob('*.svg'))
atlas = Image.new('RGBA', (size * 2, size * len(rows)))
entries, layers = {}, {}
for y, path in enumerate(rows):
    source = ET.parse(path).getroot()
    icon = 'BUI_' + path.stem.upper().replace('-', '_')
    layers[icon] = []
    for x, group in enumerate(n for n in source if n.get('data-color-role')):
        single = ET.Element(source.tag, source.attrib)
        single.append(copy.deepcopy(group))
        raster = resvg_py.svg_to_bytes(svg_string=ET.tostring(single, encoding='unicode'), width=size, height=size)
        image = Image.open(io.BytesIO(raster)).convert('RGBA')
        atlas.paste(image, (x * size, y * size))
        token = '_bui_duotone:' + path.stem + ':' + str(x)
        entries[token] = ['atlas', [x*size, y*size, size, size], True]
        # CamKeys primary=coral, secondary=mint; native themes supply these roles.
        role = 'accent_2' if group.get('data-color-role') == 'accent' else 'accent'
        layers[icon].append([token, role])
atlas.save(root/'atlas.png')
(root/'atlas.rgba.zlib').write_bytes(zlib.compress(atlas.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes(),9))
(root/'atlas.json').write_text(json.dumps(dict(dimensions=list(atlas.size),entries=entries,layers=layers),indent=2)+'\n')
print(len(rows), 'duotone icons built')
