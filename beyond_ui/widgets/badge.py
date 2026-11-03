"""Configurable semantic status chip; not an action button."""
from .base import Widget,Painter
from ..gpu import skin

class Badge(Widget):
    def __init__(self,text,*,icon='CHECKMARK',height=20,width=180,color_role='toggle_on',font_size=10,padding=7,radius=10,fill_alpha=.20,text_role=None,icon_size=12):
        if not 0<=fill_alpha<=1:raise ValueError('Badge fill alpha must be within 0..1')
        super().__init__();self.text,self.icon=text,icon
        self.fill_alpha,self.text_role=fill_alpha,text_role
        self.height,self.width=height,width
        self.role,self.font_size,self.padding,self.radius=color_role,font_size,padding,radius
        self.icon_size=icon_size
    def paint(self,rect,font,palette,*,backdrop=None):
        p=Painter(rect,self.width,self.height,font,palette,backdrop,motion=self.motion,interactive=False)
        ink=palette.get(self.role,palette['accent'])
        p.surface((0,0,self.width,self.height),(*ink[:3],self.fill_alpha),self.radius,border=0)
        skin.draw(rect,(*ink[:3],.65),radius=self.radius*p.scale,border=.6*p.scale,mode=5)
        p.palette=dict(palette,text=palette[self.text_role] if self.text_role else (*ink[:3],1))
        if self.icon:
            left=self.padding if self.text else (self.width-self.icon_size)/2
            p.icon(self.icon,(left,(self.height-self.icon_size)/2,self.icon_size,self.icon_size),self.icon_size)
        if self.text:
            gutter=self.icon_size+5 if self.icon else 0
            p.text((self.padding+gutter,0,self.width-self.padding*2-gutter,self.height),self.text,size=self.font_size,inset=0)
