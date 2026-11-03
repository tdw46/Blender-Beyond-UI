"""Small read-only wizard stepper using the shared palette and typography."""
from .base import Widget, Painter
from ..gpu import style

class Stepper(Widget):
    height = 24
    def __init__(self, step, steps):
        super().__init__()
        self.step, self.steps = step, steps
    def paint(self, rect, font, palette, *, backdrop=None):
        p = Painter(rect,self.width,self.height,font,palette,backdrop,motion=self.motion,interactive=False)
        gap=44; start=(self.width-(self.steps-1)*gap)/2
        for i in range(self.steps):
            x=start+i*gap
            if i:
                style.draw(*p.map((x-gap+12,11,gap-24,1)),palette['edge'],radius=0)
            if i < self.step:
                style.draw(*p.map((x-9,3,18,18)),palette.get('toggle_on',palette['accent']),radius=9*p.scale)
                p.text((x-9,3,18,18),str(i+1),size=10,align='center',inset=0,weight='title')
            else:
                style.draw(*p.map((x-3,9,6,6)),palette['muted'],radius=3*p.scale)
