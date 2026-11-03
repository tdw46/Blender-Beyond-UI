"""Review actual Blender captures beside immutable approved references."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,html,shutil
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/design/qa/camkeys-onboarding-v2'
board=Image.open(ROOT/'docs/design/references/camkeys-onboarding-v1/direction-b.png').convert('RGB')
crops={'target':(220,52,526,547),'workflow':(658,52,989,547),'angles':(1122,52,1453,547),'perspective':(220,568,532,1013),'dolly':(658,568,991,1013),'ready':(1120,568,1454,1013)}
labels={'target':'Choose your subject','workflow':'Choose a workflow','detected':'Directional shape confirmation','angles':'Add More / manual capture','perspective':'Forced Perspective','dolly':'Dolly Zoom','ready':'Ready'}
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
comparisons=[];stages=[]
for key,title in labels.items():
 raw=Image.open(out/f'{key}.png').convert('RGB');raw=raw.crop((24,24,raw.width-24,raw.height-24))
 actual=raw.resize((320,round(raw.height*320/raw.width)),Image.Resampling.LANCZOS)
 if key=='detected':
  ref=Image.open(ROOT/'docs/design/references/camkeys-directional-setup-v1/reference.png').convert('RGB').crop((173,48,849,1488))
 else:ref=board.crop(crops[key])
 ref=ref.resize((320,round(ref.height*320/ref.width)),Image.Resampling.LANCZOS)
 ref.save(out/f'{key}-reference.png');actual.save(out/f'{key}-actual.png')
 height=max(ref.height,actual.height)
 pair=Image.new('RGB',(688,height+64),'#12191f');d=ImageDraw.Draw(pair)
 d.text((16,12),'Generated reference',font=font,fill='#edf5f5');d.text((352,12),'Actual Blender / Metal',font=font,fill='#edf5f5')
 pair.paste(ref,(16,44));pair.paste(actual,(352,44));pair.save(out/f'{key}-comparison.png')
 comparisons.append((key,title))
 stage=Image.new('RGB',(368,820),'#12191f');stage.paste(actual,(24,45));ImageDraw.Draw(stage).text((24,12),title,font=font,fill='white');stages.append(stage)
media=ROOT/'docs/media/panels';media.mkdir(exist_ok=True)
stages[0].save(media/'camkeys-onboarding-v2.gif',save_all=True,append_images=stages[1:],duration=1600,loop=0)
frames=[]
for path in sorted((out/'motion').glob('*.png')):
 img=Image.open(path).convert('RGB');img=img.resize((344,round(img.height/2)),Image.Resampling.LANCZOS);frames.append(img)
frames[0].save(out/'media-loop.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
rows=[]
for key,title in comparisons:
 rows.append(f'<section id="{key}"><h2>{html.escape(title)}</h2><img src="{key}-comparison.png" alt="{html.escape(title)} reference and Blender"><details><summary>Registered overlay comparison</summary><div class="overlay"><img src="{key}-reference.png"><img class="actual" src="{key}-actual.png"></div><input type="range" min="0" max="100" value="50" oninput="this.previousElementSibling.lastElementChild.style.opacity=this.value/100"></details><a href="{key}.png">Full-resolution Blender PNG</a></section>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CamKeys onboarding · implemented review</title><style>body{background:#12191f;color:#ecf3f3;font:16px system-ui;line-height:1.5;margin:0}main{max-width:1100px;padding:24px;margin:auto}a{color:#83ddc8}h1{font-size:30px}section{margin:36px 0}section>img{width:100%;max-width:688px;height:auto}nav{display:flex;gap:16px;flex-wrap:wrap}.note{border:1px solid #54656c;padding:18px;border-radius:14px;background:#1e2930}.overlay{position:relative;width:320px;max-width:100%}.overlay img{width:100%;display:block}.overlay .actual{position:absolute;top:0;left:0;opacity:.5}input{width:320px;max-width:100%}.motion{width:344px;max-width:100%}</style><main><h1>CamKeys · Demo-first onboarding</h1><p><a href="../onboarding-locales-v1/index.html">New: completed translations and full-panel help review</a></p><p>B implemented with existing CamKeys artwork and real supplied clips. New directional shape confirmation appears before manual camera-angle capture.</p><div class="note"><strong>Actual Blender 5.2.2 Metal component renders from the saved Uraraka scene.</strong><p>These are production BUI GPU/glass renders over a controlled backdrop, not live-sidebar screenshots. Direction B and the new directional panel remain immutable references. Layouts are registered at equal panel width, without stretching their height.</p><p>Latest corrections: Viewport-first Forced Perspective with a source picker; Back on final screens; Lens Tricks uses the supplied AutoFOV comparison clip. Reference-style feature icons, left-aligned help rows with 24-unit question accessories, matching button/rim radii, Back arrows and trailing external-link icons. Redundant shapes heading removed; rounded media now restores alpha blending and follows UI scale. No media captions, timestamps or transport controls; Sonic on the subject screen; preserve the requested Forced Perspective and Dolly workflow descriptions. Detected rig/head chips reflect actual metadata. Whole-card radio selection and native property/shape-key search ownership remain intact.</p><p>Intentional differences: original supplied media and logo replace generated artwork; source aspect ratios are preserved. Back/manual navigation, true scene names, missing-data messages and valid four-step progress add functional content. Tint, overall height and some typography still differ; this is review evidence, not a pixel-perfect acceptance claim.</p><p>All three setup routes and selected directional auto-add pass on 5.1.2/5.2.2. Real custom popup playback/cleanup and queued eyedropper input pass on Metal. Physical Windows/Vulkan/OpenGL and 4.2 wizard QA remain open. No version bumps.</p></div><nav>NAV</nav>ROWS<h2>Looping media · actual rendered frames</h2><img class="motion" src="media-loop.gif" alt="Actual custom media playback"><p>10 FPS source sampling; full clip durations are preserved in the installed package. This short QA GIF shows 1.2 seconds of playback.</p><p><a href="report.json">Evidence and limits</a> · <a href="copy.json">Recorded copy</a> · <a href="../../../WIZARD_MEDIA.md">Reusable BUI integration</a> · <a href="../overview/index.html">Overview and estimate</a></p></main></html>'''
page=page.replace('NAV',''.join(f'<a href="#{k}">{html.escape(v)}</a>' for k,v in comparisons)).replace('ROWS',''.join(rows));(out/'index.html').write_text(page)
current=[dict(title='CamKeys Demo First wizard · actual stage snapshots',path='docs/media/panels/camkeys-onboarding-v2.gif')];(out/'current-media.json').write_text(json.dumps(current,indent=2)+'\n')
print('Seven comparisons, overlay review, stage GIF and media GIF written')
