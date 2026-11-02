#!/usr/bin/env python3
"""Pack authored PNG artwork for explicit Beyond UI startup loading (Pillow required).
Input: {"sources":{"logo":"logo.png"},"icons":{"logo":{"source":"logo","fallback":"CAMERA_DATA"}}}.
Optional icon rect is top-left x,y,w,h. Omitted rect uses nontransparent ink bounds.
"""
import argparse,json,zlib
from pathlib import Path
from PIL import Image

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();spec=json.loads(args.spec.read_text());args.output.mkdir(parents=True,exist_ok=True)
    result={'sources':{},'icons':{}};images={}
    for i,(key,filename) in enumerate(spec['sources'].items()):
        im=Image.open(args.spec.parent/filename).convert('RGBA')
        if max(im.size)>4096:raise ValueError('Artwork dimensions exceed 4096')
        images[key]=im;name=f'artwork-{i}.rgba.zlib'
        (args.output/name).write_bytes(zlib.compress(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes(),9))
        result['sources'][key]={'size':list(im.size),'file':name}
    for key,data in spec['icons'].items():
        im=images[data['source']];entry=dict(data)
        if 'rect' not in entry:
            bounds=im.getchannel('A').getbbox()
            if bounds is None:raise ValueError('Empty artwork: '+key)
            x,y,r,b=bounds;entry['rect']=[x,y,r-x,b-y]
        x,y,w,h=entry['rect']
        if min(x,y)<0 or min(w,h)<=0 or x+w>im.width or y+h>im.height:raise ValueError('Invalid bounds: '+key)
        result['icons'][key]=entry
    (args.output/'artwork.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
