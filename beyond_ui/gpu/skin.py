"""Analytic translucent reference skin; no captured/reference-image textures.

Uses the source library's shared glass lens when a host supplies its backdrop.
All chrome remains translucent in the tint-only compatibility path as well.
"""

_shader = _batch = None


def rgba(hex_value, alpha=1.0):
    return tuple(int(hex_value[i : i + 2], 16) / 255 for i in (0, 2, 4)) + (alpha,)


# Values are display-space tint colors. Alpha is deliberate material opacity,
# not a fake opaque approximation of a particular captured background.
ROLES = {
    "card": (rgba("202224", 0.70), rgba("222426", 0.70)),
    "header": (rgba("282b2e", 0.36), rgba("303133", 0.36)),
    "field": (rgba("303235", 0.50), rgba("3a3c3f", 0.50)),
    "input": (rgba("1c1f22", 0.48), rgba("292c2f", 0.48)),
    "button": (rgba("333639", 0.65), rgba("3b3e41", 0.65)),
    "graph": (rgba("212326", 0.34), rgba("27292c", 0.34)),
    "tab": (rgba("2087e5", 0.93), rgba("2d9bf2", 0.93)),
    "selected": (rgba("214d78", 0.83), rgba("285e8b", 0.83)),
    "track": (rgba("35393c", 0.65), rgba("42464a", 0.65)),
    "thumb": (rgba("83868a", 0.80), rgba("a4a7aa", 0.80)),
    "fill": (rgba("209be9", 0.96), rgba("31b9ef", 0.96)),
}
TEXT = rgba("f0f1f3")
MUTED = rgba("b9bdc2")
EDGE = rgba("91969c", 0.45)


def ensure():
    global _shader, _batch
    if _shader is not None:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader

    interface = gpu.types.GPUStageInterfaceInfo("beyond_ui_glass_skin_uv")
    interface.smooth("VEC2", "uv")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.push_constant("MAT4", "mvp")
    info.push_constant("VEC4", "rect")
    info.push_constant("VEC4", "lower")
    info.push_constant("VEC4", "upper")
    info.push_constant("VEC4", "params")
    info.vertex_source(
        "void main(){uv=pos;gl_Position=mvp*vec4(rect.xy+pos*rect.zw,0.,1.);}"
    )
    info.fragment_source("""
vec3 hue(float h) { return clamp(abs(fract(vec3(h)+vec3(0.,2./3.,1./3.))*6.-3.)-1.,0.,1.); }
void main(){
 vec2 s=rect.zw; float r=min(params.x,min(s.x,s.y)*.5);
 vec2 q=abs((uv-.5)*s)-s*.5+r;
 float d=length(max(q,vec2(0.)))+min(max(q.x,q.y),0.)-r;
 if(params.z==3.)d=(length((uv-.5)*2.)-1.)*min(s.x,s.y)*.5;
 float aa=max(fwidth(d),.65);float coverage=1.-smoothstep(-aa*.6,aa*.6,d);
 vec4 c=mix(lower,upper,uv.y);
 if(params.z==1.)c=vec4(mix(vec3(1.),hue(params.w),uv.x)*uv.y,1.);
 if(params.z==2.)c=vec4(hue(uv.x),1.);
 // Soft diagonal illumination on translucent glass, no extra capture/pass.
 if(params.z==4.)c.rgb+=.008*exp(-dot((uv-vec2(.35,.65))*vec2(1.5,2.),(uv-vec2(.35,.65))*vec2(1.5,2.)));
 if(params.y>0.){
  float edge=smoothstep(-params.y-aa*.5,-params.y+aa*.5,d);
  float chroma=max(c.r,max(c.g,c.b))-min(c.r,min(c.g,c.b));
  vec3 rim=mix(vec3(.48,.50,.52),min(c.rgb+vec3(.18),vec3(1.)),step(.15,chroma));
  c=mix(c,vec4(rim,.92),edge*.75);
 }
 fragColor=vec4(c.rgb,c.a*coverage);
}""")
    _shader = gpu.shader.create_from_info(info)
    _batch = batch_for_shader(
        _shader,
        "TRIS",
        {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
        indices=((0, 1, 2), (2, 1, 3)),
    )


def draw(rect, lower, upper=None, *, radius=8.0, border=0.7, mode=0.0, hue=0.0):
    import gpu

    if rect[2] <= 0 or rect[3] <= 0:
        return
    ensure()
    gpu.state.blend_set("ALPHA")
    _shader.bind()
    _shader.uniform_float(
        "mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    )
    _shader.uniform_float("rect", rect)
    _shader.uniform_float("lower", lower)
    _shader.uniform_float("upper", upper if upper is not None else lower)
    _shader.uniform_float("params", (radius, border, mode, hue))
    _batch.draw(_shader)


def clear():
    global _shader, _batch
    _shader = _batch = None


def palette():
    """Reference roles are independent of the user's native Blender theme."""
    return {
        "accent": ROLES["tab"][1],
        "bg": rgba("222528", 0.30),
        "card": ROLES["card"][0],
        "bar": ROLES["header"][1],
        "field": ROLES["field"][0],
        "text": TEXT,
        "selected_text": TEXT,
        "tab": ROLES["tab"][1],
        "slider_track": ROLES["track"][0],
        "slider_fill": ROLES["fill"][0],
        "toggle_off": ROLES["track"][0],
        "toggle_on": ROLES["tab"][1],
        "muted": MUTED,
        "selected": ROLES["selected"][0],
        "hover": rgba("3c474f", 0.66),
        "overlay": rgba("222528", 0.85),
        "api": rgba("72c8ff"),
    }
