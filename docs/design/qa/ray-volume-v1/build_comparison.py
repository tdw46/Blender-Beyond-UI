"""Compose already-rendered Blender captures; never changes the Blender images."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font = '/System/Library/Fonts/Supplemental/Arial.ttf'
title_font = ImageFont.truetype(font, 27)
body_font = ImageFont.truetype(font, 21)
canvas = Image.new('RGB', (1320, 1430), '#17212a')
draw = ImageDraw.Draw(canvas)
draw.text((30, 18), 'Camera-ray volume prototype · fixed real camera: 50 mm',
          font=title_font, fill='#f2f5f7')
rows = [(0, 'front', 'Camera view · focus-anchored volume'),
        (0, 'side', 'Side view · focus-anchored volume'),
        (1, 'side', 'Side view · affine volume (moves physical focus depth)')]
for row, (mode, view, title) in enumerate(rows):
    y = 64 + row * 450
    draw.text((30, y), title, font=body_font, fill='#66d3bc')
    for column, lens in enumerate((25, 50, 100)):
        x = 30 + column * 430
        image = Image.open(root / f'mode-{mode}-{view}-{lens}mm.png').convert('RGB')
        canvas.paste(image.resize((380, 380)), (x + 15, y + 36))
        draw.text((x + 115, y + 416), f'Apparent {lens} mm', font=body_font, fill='#e7eef4')
canvas.save(root / 'comparison.jpg', quality=92)
