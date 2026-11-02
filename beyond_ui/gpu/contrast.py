"""Cached-palette contrast helpers; never sample or alter the scene framebuffer.

RGB inputs/outputs remain display-space theme colors. Transfer functions below
are solely for relative luminance measurements, not shader color conversion.
"""

def over(front, back):
    a=front[3] if len(front)>3 else 1.0
    return tuple(x*a+y*(1-a) for x,y in zip(front[:3],back[:3]))+(1.0,)


def luminance(color):
    def channel(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    return sum(channel(v)*w for v,w in zip(color[:3],(.2126,.7152,.0722)))


def ratio(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def readable(color, backgrounds, target=4.5, *, vivid=False):
    """Reach the contrast target on estimated surfaces without changing hue.

    Preserve hue by blending toward white or black, rather than substituting a
    fixed accent. Vivid accents raise value first to retain more saturation.
    Existing adequate colors pass through byte-for-byte.
    """
    def score(c):return min(ratio(over(c,b),b) for b in backgrounds)
    if score(color)>=target:return color
    ends=[(v,v,v,color[3]) for v in (0.0,1.0)]
    end=max(ends,key=score)
    if score(end)<target:return end
    start=color
    # Accent ink: raise value at constant hue/saturation before adding white.
    # Only reduce saturation when the RGB gamut cannot reach the contrast target.
    # Neutral body text retains the original minimal-blend policy.
    peak=max(color[:3])
    if vivid and end[0]==1.0 and 0.0<peak<1.0:
        bright=tuple(v/peak for v in color[:3])+(color[3],)
        if score(bright)>=target:
            end=bright
        else:
            start=bright
    lo,hi=0.0,1.0
    for _ in range(18):
        t=(lo+hi)/2
        trial=tuple(a+(b-a)*t for a,b in zip(start[:3],end[:3]))+(color[3],)
        if score(trial)>=target:hi=t
        else:lo=t
    return tuple(a+(b-a)*hi for a,b in zip(start[:3],end[:3]))+(color[3],)


def backgrounds(p):
    # Bound the effect of bright/dark scene pixels through the root glass tint.
    roots=[over(p['bg'],(v,v,v,1)) for v in (0.0,1.0)]
    return tuple(roots+[over(p[role],b) for role in ('card','input','field') for b in roots])
