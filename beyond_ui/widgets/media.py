"""Retained media surface; decoded/uploaded only by its library scheduler."""
from weakref import ref
from .base import Widget

class MediaWidget(Widget):
    def __init__(self, library, key, canvas, height=160, radius=12, *, caption="", caption_size=10, caption_padding=8):
        super().__init__()
        self.library, self.key, self.owner = library, key, ref(canvas)
        self.height, self.radius = float(height), float(radius)
        self.caption, self.caption_size, self.caption_padding = str(caption), float(caption_size), float(caption_padding)
        try:
            from bpy.app.translations import pgettext_iface
        except ImportError:
            pgettext_iface=lambda text:text
        self.loading_text=pgettext_iface('Loading example…')
        self.unavailable_text=pgettext_iface('Preview unavailable')

    def dimensions(self, font_size, available_width, available_height=None):
        # Media is a responsive viewport, not a uniformly scaled compound editor.
        height = self.height * font_size / self.design_font_size
        if available_height is not None:
            height = min(height, available_height)
        return max(1, available_width), max(1, height)

    def all_children(self):
        return ()

    def route(self, *args, **kwargs):
        return None

    def advance(self, clip=None):
        return False

    def cancel(self):
        super().cancel()
        self.library.release(self)

    def paint(self, rect, font, palette, *, backdrop=None):
        from ..gpu import style
        from .base import Painter
        self.library.touch(self)
        frame = self.library.frames.get(self.key)
        if frame is None:
            p = Painter(rect, self.width, self.height, font, palette, backdrop)
            p.surface((0, 0, self.width, self.height), 'input', self.radius)
            p.text((10, 10, self.width-20, self.height-20),
                   self.unavailable_text if self.key in self.library.errors else self.loading_text, size=11)
            return
        texture, _, width, height = frame
        x, y, w, h = rect
        ratio = min(w/width, h/height)
        dw, dh = width*ratio, height*ratio
        style.preview(texture, x+(w-dw)/2, y+(h-dh)/2, dw, dh,
                      radius=self.radius * h / self.height, display_space=True)

        if self.caption:
            # Caption belongs to the media viewport; no transport/timestamp chrome.
            # Fixed neutral scrim protects text over arbitrary user-authored footage.
            p = Painter(rect, w * self.height / h, self.height, font, palette, backdrop)
            pad = self.caption_padding
            band = self.caption_size + 2 * pad
            p.surface((0, self.height-band, p.width, band), (0,0,0,.55), self.radius, border=0)
            p.palette = dict(palette, text=(1,1,1,1))
            p.text((pad,self.height-band,p.width-2*pad,band),self.caption,
                   size=self.caption_size,inset=0,weight='title')
