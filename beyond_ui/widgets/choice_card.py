"""Enum-backed media choice chrome. Button dispatch/context remains native BUI."""
from .base import Painter
from .media import MediaWidget
from ..gpu import skin
from ..text_wrap import wrap_text

class ChoiceCard:
    def __init__(self, canvas, title, description, library, media_key, *, width=300,
                 height=94, media_width=96, padding=8, radius=10, font_size=12,
                 description_size=10, line_height=15, rim_width=1.3, radio_size=14):
        self.title, self.description = title, description
        self.width,self.height=width,height
        self.media_width,self.padding,self.radius=media_width,padding,radius
        self.font_size,self.description_size,self.line_height=font_size,description_size,line_height
        self.rim_width,self.radio_size=rim_width,radio_size
        self.media=MediaWidget(library,media_key,canvas,height-2*padding,radius-2) if library else None
        self._text_layout = ((), ())
        self.render_height=height

    def dimensions(self, available, font_size, measure=None):
        """Wrap during retained layout; narrow cards grow instead of clipping copy."""
        scale = font_size / 11.0
        width = available / scale
        mw = min(self.media_width, width*.35)
        limit = max(20, width-self.padding*2-mw-10-self.radio_size-8)
        sized_measure = getattr(measure, 'at_size', None)
        def lines(text, size, role):
            def width_of(value):
                if sized_measure is not None:
                    return sized_measure(value, role, size * scale) / scale
                if measure is not None:
                    return measure(value, role) * size / font_size
                return len(value) * size * .58
            return wrap_text(text, limit, width_of)
        titles = lines(self.title, self.font_size, 'title')
        copy = lines(self.description, self.description_size, 'body')
        self._text_layout = titles, copy
        text_height=len(titles)*(self.line_height+1)+4+len(copy)*self.line_height
        self.render_height=max(self.height,text_height+2*self.padding)
        return available, self.render_height*scale

    def paint(self, rect, font, palette, *, selected=False, hovered=False, backdrop=None):
        # Preserve logical font sizes as the available width changes.
        x,y,w,h=rect; scale=h/self.render_height
        p=Painter(rect,w/scale,self.render_height,font,palette,backdrop,interactive=False)
        width=p.width;pad=self.padding; height=self.render_height
        p.surface((0,0,width,height),'selected' if selected else 'card',self.radius,border=0)
        accent=palette.get('toggle_on',palette['accent'])
        rim=(*accent[:3],.95) if selected else palette['edge']
        skin.draw(rect,rim,radius=self.radius*scale,border=(self.rim_width if selected else .6)*scale,mode=5)
        mw=min(self.media_width,width*.35)
        if self.media:
            self.media.paint(p.map((pad,pad,mw,height-2*pad)),font,palette,backdrop=backdrop)
        tx=pad+mw+10;available=max(20,width-tx-pad-self.radio_size-8)
        # Paint precisely the lines that reserved this card's height. A second
        # wrap with different hinted font metrics can add an unreserved line.
        titles, copy = self._text_layout
        total=len(titles)*(self.line_height+1)+len(copy)*self.line_height+4
        top=max(pad,(height-total)/2)
        for line in titles:
            p.text((tx,top,available,self.line_height+1),line,size=self.font_size,inset=0,weight='title');top+=self.line_height+1
        top+=4
        for line in copy:
            p.text((tx,top,available,self.line_height),line,size=self.description_size,inset=0,role='muted');top+=self.line_height
        r=self.radio_size; radio=p.map((width-pad-r,(height-r)/2,r,r))
        skin.draw(radio,(*accent[:3],1) if selected else palette['muted'],radius=r/2*scale,border=1.3*scale,mode=5)
        if selected:
            inset=3*scale
            skin.draw((radio[0]+inset,radio[1]+inset,radio[2]-2*inset,radio[3]-2*inset),(*accent[:3],1),radius=r*scale,border=0)
