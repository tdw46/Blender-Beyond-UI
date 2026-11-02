"""Bounded value-change ink, driven by existing reads and finite host animation.

No polling, RNA reads, allocations of GPU resources or geometry invalidation.
"""
from math import isfinite
from time import monotonic

DEFAULTS = dict(enabled=True, hold=.22, fade=.18, epsilon=1e-6, role='accent')
_MISSING = object()

def normalize(options):
    from .stylesheet import _COLORS
    if isinstance(options, bool):options={'enabled':options}
    if not isinstance(options, dict) or options.keys()-DEFAULTS.keys():
        raise ValueError('Invalid value_feedback options')
    result=dict(options)
    for key,value in result.items():
        if key=='enabled':
            if type(value) is not bool:raise ValueError('enabled must be Boolean')
        elif key=='role':
            if value not in _COLORS:raise ValueError('Unknown feedback color role')
        elif isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or not 0<=value<= (1 if key=='epsilon' else 5):
            raise ValueError('Invalid feedback '+key)
    return result

def snapshot(value):
    if isinstance(value,(str,bool,int,float)) or value is None:return value
    # Bound vector/enum-flag snapshots; never traverse arbitrary RNA owners.
    if isinstance(value,(tuple,list,set,frozenset)) or type(value).__name__=='bpy_prop_array':
        if len(value)<=32:
            values=tuple(value)
            if all(isinstance(v,(bool,int,float,str)) for v in values):
                return frozenset(values) if isinstance(value,(set,frozenset)) else values
    return _MISSING

def equal(a,b,epsilon):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return a==b or abs(a-b)<=epsilon or (not isfinite(a) and not isfinite(b))
    if isinstance(a,tuple) and isinstance(b,tuple):
        return len(a)==len(b) and all(equal(x,y,epsilon) for x,y in zip(a,b))
    return a==b

class ValueFeedback:
    def __init__(self,canvas,*,clock=monotonic):
        self.canvas=canvas;self.clock=clock;self.settings=dict(DEFAULTS)
        self.values={};self.active={};self.parent=None

    def configure(self,options):
        self.settings=dict(DEFAULTS,**normalize(options))
        if not self.enabled():self.clear()

    def options(self,control):
        settings=self.parent.settings if self.parent is not None else self.settings
        overrides=control.options.get('value_feedback',{})
        if not overrides:return settings
        cached=getattr(control,'_feedback_options',None)
        if cached is None or cached[0] is not settings or cached[1] is not overrides:
            cached=(settings,overrides,dict(settings,**overrides));control._feedback_options=cached
        return cached[2]

    def enabled(self):
        return self.settings['enabled'] and (self.parent is None or self.parent.enabled())

    def observe(self,control,value,now=None):
        if not self.canvas.visible or not self.enabled():return
        options=self.options(control)
        if not options['enabled']:
            self.values.pop(control.key,None);self.active.pop(control.key,None);return
        current=snapshot(value)
        if current is _MISSING:return
        old=self.values.get(control.key,_MISSING)
        self.values[control.key]=current
        if old is _MISSING or equal(old,current,options['epsilon']):return
        now=self.clock() if now is None else now
        self.active[control.key]=(control,now)
        if self.canvas._animation_wake:self.canvas._animation_wake()

    def amount(self,control,now=None):
        entry=self.active.get(control.key)
        if entry is None:return 0
        options=self.options(control)
        now=self.clock() if now is None else now
        elapsed=now-entry[1]-options['hold']
        amount=1 if elapsed<=0 else max(0,1-elapsed/max(options['fade'],1e-9))
        if not self.enabled() or not options['enabled']:amount=0
        if not amount:self.active.pop(control.key,None)
        return amount

    def advance(self,clip=None):
        if not self.canvas.visible:
            self.clear();return False
        now=self.clock()
        for key,(control,_) in tuple(self.active.items()):
            if clip is not None:
                x,y,w,h=control.rect;a,b,c,d=clip
                if not (x<a+c and x+w>a and y<b+d and y+h>b):
                    self.active.pop(key,None);self.values.pop(key,None);continue
            self.amount(control,now)
        return bool(self.active)

    def prune(self):
        for key in tuple(self.values):
            if key not in self.canvas.controls:
                self.values.pop(key,None);self.active.pop(key,None)

    def clear(self):
        self.values.clear();self.active.clear()
