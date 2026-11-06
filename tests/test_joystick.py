from types import SimpleNamespace
import unittest
from beyond_ui.bindings import Binding
from beyond_ui.widgets.joystick import Joystick, pair_binding

def event(kind,value='PRESS',**kw):return SimpleNamespace(type=kind,value=value,**kw)

class JoystickTests(unittest.TestCase):
    def make(self,**kw):
        state=[(0.,0.)];commits=[]
        binding=Binding(lambda:state[0],lambda v:state.__setitem__(0,tuple(v)),commit=lambda a,b:commits.append((a,b)))
        return Joystick(binding,clock=lambda:0.,**kw),state,commits
    def test_velocity_ramp_and_release(self):
        small,a,_=self.make(mode='VELOCITY');edge,b,commits=self.make(mode='VELOCITY')
        small.event(event('LEFTMOUSE'),56.2,52);edge.event(event('LEFTMOUSE'),94,52)
        for i in range(1,61):small.advance(i/60);edge.advance(i/60)
        self.assertGreater(a[0][0],0);self.assertLess(a[0][0],b[0][0]/100)
        self.assertAlmostEqual(b[0][0],.35)
        edge.event(event('LEFTMOUSE','RELEASE'),94,52)
        self.assertEqual(len(commits),1);self.assertEqual(edge.deflection,(0.,0.));self.assertFalse(edge.advance(2))
    def test_edge_boost_preserves_inner_speed_and_reaches_four_times(self):
        def sample(deflection,multiplier):
            w,s,_=self.make(mode='VELOCITY',minimum=(-20,-20),maximum=(20,20),
                          edge_speed_multiplier=multiplier,edge_start=.7)
            w.event(event('LEFTMOUSE'),52+42*deflection,52)
            w.advance(.05)
            return s[0][0]
        for value in (0,.1,.3,.5,.7,-.1,-.7):
            self.assertEqual(sample(value,4),sample(value,1))
        self.assertAlmostEqual(sample(1,4),4*sample(1,1))
        self.assertAlmostEqual(sample(-1,4),4*sample(-1,1))
        previous=sample(.7,4)
        for i in range(701,1001):
            current=sample(i/1000,4)
            self.assertGreater(current,previous)
            self.assertLess(current-previous,.0004)
            previous=current
        self.assertAlmostEqual(sample(.85,4)/sample(.85,1),2.5)

    def test_uniform_speed_and_shift_during_hold(self):
        for deflection in (.1,.4,.7,1.,-1.):
            old,a,_=self.make(mode='VELOCITY',minimum=(-20,-20),maximum=(20,20))
            new,b,commits=self.make(mode='VELOCITY',speed=1.4,minimum=(-20,-20),maximum=(20,20))
            for w in (old,new):w.event(event('LEFTMOUSE',shift=False),52+42*deflection,52)
            old.advance(.05);new.advance(.05)
            self.assertAlmostEqual(b[0][0],4*a[0][0])
            new.event(event('LEFT_SHIFT',shift=True),52,52)
            before=b[0][0];new.advance(.1)
            self.assertAlmostEqual(b[0][0]-before,a[0][0])
            new.event(event('LEFT_SHIFT','RELEASE',shift=False),52,52)
            before=b[0][0];new.advance(.15)
            self.assertAlmostEqual(b[0][0]-before,4*a[0][0])
            new.event(event('LEFTMOUSE','RELEASE'),52,52)
            self.assertEqual(len(commits),1);self.assertFalse(new.fine)
        w,s,_=self.make(mode='VELOCITY',speed=1.4)
        w.event(event('LEFTMOUSE',shift=True),94,52);w.advance(.05)
        self.assertAlmostEqual(s[0][0],.35*.05)

    def test_cancel_and_reset(self):
        w,s,c=self.make(mode='VELOCITY');w.event(event('LEFTMOUSE'),94,10);w.advance(.05)
        self.assertNotEqual(s[0],(0.,0.));w.event(event('RIGHTMOUSE'),94,10)
        self.assertEqual(s[0],(0.,0.));self.assertFalse(c)
        s[0]=(1.,1.);w.reset();self.assertEqual(s[0],(0.,0.));self.assertEqual(len(c),1)
    def test_idle_and_clamped_stalls(self):
        w,s,c=self.make(mode='VELOCITY');self.assertFalse(w.advance(100))
        w.event(event('LEFTMOUSE'),94,52);w.advance(100)
        self.assertLessEqual(s[0][0],.35/15);self.assertFalse(c)
    def test_pair_rollback(self):
        state=[1.,2.]
        x=Binding(lambda:state[0],lambda v:state.__setitem__(0,v))
        def set_y(v):
            if v==9:raise ValueError('invalid')
            state[1]=v
        y=Binding(lambda:state[1],set_y);b=pair_binding(x,y,lambda a,b:None)
        with self.assertRaises(ValueError):b.write((4.,9.))
        self.assertEqual(state,[1.,2.])
    def test_stale_owner_stops(self):
        w,s,c=self.make(mode='VELOCITY');w.event(event('LEFTMOUSE'),94,52)
        w.binding.valid=lambda:False
        self.assertFalse(w.advance(.05));self.assertFalse(w.capturing)
    def test_position_and_exact_axes(self):
        w,s,c=self.make();w.event(event('LEFTMOUSE'),94,10);w.event(event('LEFTMOUSE','RELEASE'),94,10)
        self.assertEqual(s[0],(1.,1.));self.assertEqual(len(c),1)
    def test_bad_configuration(self):
        for kw in ({'speed':float('nan')},{'velocity_curve':(.8,.2)},{'minimum':(1.,1.)},{'edge_speed_multiplier':float('nan')},{'edge_speed_multiplier':.9},{'edge_start':1},{'edge_start':-.1},{'fine_speed_scale':0},{'fine_speed_scale':1.1},{'fine_speed_scale':float('nan')}):
            with self.assertRaises(ValueError):self.make(**kw)

if __name__=='__main__':unittest.main()
