"""Bounded 2D edit pad. RNA ownership/undo remain in its supplied binding."""
import math
from time import monotonic
from dataclasses import replace
from .base import Widget, Painter, contains
from ..bindings import Binding, Edit
from ..context_menu import Target, Entry, default_entries


def pair_binding(x, y, commit):
    """Atomic two-property edits; freeze both owners for the entire drag."""
    def write(value):
        before=(x.read(),y.read())
        try:
            x.write(value[0]);y.write(value[1])
        except Exception:
            if x.valid():x.write(before[0])
            if y.valid():y.write(before[1])
            raise
    return Binding(lambda:(x.read(),y.read()),write,
        lambda:x.valid() and y.valid(),commit,
        snapshot=lambda:pair_binding(x.frozen(),y.frozen(),commit))


class Joystick(Widget):
    width=height=104.
    design_font_size=11.

    def __init__(self,binding,*,axes=(),minimum=(-1.,-1.),maximum=(1.,1.),default=(0.,0.),radius=12.,handle_radius=5.,mode="POSITION",speed=.35,velocity_curve=(0.,0.),edge_speed_multiplier=1.,edge_start=.7,fine_speed_scale=.25,clock=monotonic):
        super().__init__()
        self.binding=binding;self.axes=axes;self.minimum=tuple(minimum);self.maximum=tuple(maximum);self.default=tuple(default)
        if any(len(v)!=2 for v in (self.minimum,self.maximum,self.default)) or not all(math.isfinite(v) for v in (*self.minimum,*self.maximum,*self.default,radius,handle_radius)) or any(a>=b for a,b in zip(self.minimum,self.maximum)):
            raise ValueError('Joystick ranges must be finite and increasing')
        if radius < 0 or handle_radius <= 0 or any(not a <= v <= b for a,b,v in zip(self.minimum,self.maximum,self.default)):
            raise ValueError('Joystick default must lie within its range')
        self.radius=radius;self.handle_radius=handle_radius;self.transaction=None
        if mode not in {'POSITION','VELOCITY'} or not math.isfinite(speed) or speed<0 or len(velocity_curve)!=2 or not 0<=velocity_curve[0]<=velocity_curve[1]<=1:
            raise ValueError('Invalid joystick motion configuration')
        if (not math.isfinite(edge_speed_multiplier) or edge_speed_multiplier < 1 or
                not math.isfinite(edge_start) or not 0 <= edge_start < 1):
            raise ValueError('Invalid joystick edge acceleration')
        if not math.isfinite(fine_speed_scale) or not 0 < fine_speed_scale <= 1:
            raise ValueError('fine_speed_scale must be finite in (0, 1]')
        self.fine_speed_scale=fine_speed_scale;self.fine=False
        self.edge_speed_multiplier=edge_speed_multiplier;self.edge_start=edge_start
        self.mode=mode;self.speed=speed;self.velocity_curve=tuple(velocity_curve);self.clock=clock
        self.deflection=(0.,0.);self.last_time=None

    def cancel(self):
        if self.transaction:self.transaction.finish(cancel=True)
        self.transaction=None;self.deflection=(0.,0.);self.last_time=None;self.fine=False
        super().cancel()

    def reset(self):
        edit=Edit(self.binding);edit.update(self.default);edit.finish()

    def event(self,event,x,y,*,clipboard=None):
        if not self.binding.valid():self.cancel();return False
        kind=event.type
        if hasattr(event,'shift'):self.fine=bool(event.shift)
        elif kind in {'LEFT_SHIFT','RIGHT_SHIFT'}:self.fine=event.value!='RELEASE'
        elif not self.capturing:self.fine=False
        if self.capturing:
            if kind in {'LEFT_SHIFT','RIGHT_SHIFT'}:return True
            if kind in {'ESC','RIGHTMOUSE','WINDOW_DEACTIVATE'}:self.cancel();return True
            if kind=='MOUSEMOVE':self._move(x,y);return True
            if kind=='LEFTMOUSE' and event.value=='RELEASE':
                self.transaction.finish();self.transaction=None;self.capturing=False;self.deflection=(0.,0.);self.last_time=None;self.fine=False;return True
            return False
        if kind=='LEFTMOUSE' and event.value=='DOUBLE_CLICK':self.reset();return True
        if kind=='LEFTMOUSE' and event.value=='PRESS' and contains((0,0,104,104),x,y):
            self.transaction=Edit(self.binding);self.capturing=True;self.last_time=self.clock();self._move(x,y)
            if self.motion.wake:self.motion.wake(self.motion)
            return True
        if kind in {'LEFT_ARROW','RIGHT_ARROW','UP_ARROW','DOWN_ARROW','HOME'} and event.value=='PRESS':
            if kind=='HOME':self.reset();return True
            value=list(self.binding.read());axis=int(kind in {'UP_ARROW','DOWN_ARROW'})
            step=(self.maximum[axis]-self.minimum[axis])*(.005 if getattr(event,'shift',False) else .025)
            value[axis]+=step*(-1 if kind in {'LEFT_ARROW','DOWN_ARROW'} else 1)
            edit=Edit(self.binding);edit.update(self.clamp(value));edit.finish();return True
        return False

    def clamp(self,values):
        if len(values)!=2 or not all(math.isfinite(v) for v in values):raise ValueError('Joystick needs two finite values')
        return tuple(max(a,min(b,v)) for a,b,v in zip(self.minimum,self.maximum,values))

    def _move(self,x,y):
        t=(max(0.,min(1.,(x-10)/84)),max(0.,min(1.,1-(y-10)/84)))
        if self.mode=='VELOCITY':self.deflection=tuple(2*v-1 for v in t)
        else:self.transaction.update(tuple(a+(b-a)*v for a,b,v in zip(self.minimum,self.maximum,t)))

    def advance(self,now=None):
        if not self.capturing or self.mode!='VELOCITY':return False
        if not self.transaction.binding.valid():self.cancel();return False
        now=self.clock() if now is None else now
        dt=min(1/15,max(0.,now-(self.last_time if self.last_time is not None else now)));self.last_time=now
        values=list(self.transaction.binding.read());p1,p2=self.velocity_curve
        for i,v in enumerate(self.deflection):
            u=max(0.,(abs(v)-.025)/.975)
            gain=3*(1-u)**2*u*p1+3*(1-u)*u*u*p2+u**3
            # Preserve the original inner response exactly. Smoothstep has
            # zero slope at both ends of the configurable outer boost band.
            edge=max(0.,min(1.,(abs(v)-self.edge_start)/(1-self.edge_start)))
            boost=1+(self.edge_speed_multiplier-1)*edge*edge*(3-2*edge)
            values[i]+=math.copysign(self.speed*gain*boost*dt*(self.fine_speed_scale if self.fine else 1.),v)
        values=self.clamp(values)
        if values!=tuple(self.transaction.binding.read()):self.transaction.update(values)
        return True

    def target_at(self,key,x,y):
        return Target(key,('pad',),self.binding,self.binding.valid,self.binding.read,self)

    def entries(self,target,context):
        rows=[Entry('JOYSTICK_RESET','Reset Offset',lambda t,c:self.reset(),enabled=lambda t,c:t.editable() and self.binding.valid(),icon='LOOP_BACK')]
        if self.binding.context:rows.extend(default_entries(target,context))
        for index,binding in enumerate(self.axes):
            part=replace(target,part=('component',index),binding=binding,valid=binding.valid,value=binding.read)
            rows.append(Entry('JOYSTICK_AXIS_'+str(index),'XY'[index],children=lambda t,c,part=part:default_entries(part,c)))
        return rows

    def paint(self,rect,font,palette,*,backdrop=None):
        p=Painter(rect,104,104,font,palette,backdrop,motion=self.motion)
        p.surface((0,0,104,104),'well',self.radius,1,motion_key=False)
        p.line(((10,52),(94,52),None,(52,10),(52,94)),palette['muted'],.55*p.scale)
        p.line(((7,52),(11,52),None,(93,52),(97,52),None,(52,7),(52,11),None,(52,93),(52,97)),palette['text'],p.scale)
        try:values=self.binding.read()
        except ReferenceError:return
        u,v=tuple((v+1)/2 for v in self.deflection) if self.mode=='VELOCITY' else tuple((n-a)/(b-a) for a,b,n in zip(self.minimum,self.maximum,values))
        p.circle((10+84*max(0,min(1,u)),94-84*max(0,min(1,v))),self.handle_radius,palette['accent'],motion_key='handle')
