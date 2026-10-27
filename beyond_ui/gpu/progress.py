"""One retained analytic ring quad; changing progress updates uniforms only."""

_shader = _batch = None


def ring(rect, value, thickness, track, fill):
    global _shader, _batch
    import gpu
    from gpu_extras.batch import batch_for_shader

    if _shader is None:
        interface = gpu.types.GPUStageInterfaceInfo("beyond_ui_progress_uv")
        interface.smooth("VEC2", "uv")
        info = gpu.types.GPUShaderCreateInfo()
        info.vertex_in(0, "VEC2", "pos")
        info.vertex_out(interface)
        info.fragment_out(0, "VEC4", "fragColor")
        for kind, name in [
            ("MAT4", "mvp"),
            ("VEC4", "rect"),
            ("VEC4", "track"),
            ("VEC4", "fill"),
            ("VEC2", "state"),
        ]:
            info.push_constant(kind, name)
        info.vertex_source(
            "void main(){uv=pos;gl_Position=mvp*vec4(rect.xy+pos*rect.zw,0.,1.);}"
        )
        info.fragment_source("""
void main(){
 vec2 p=(uv-.5)*rect.zw;float radius=min(rect.z,rect.w)*.5-state.y*.5-1.;
 float d=abs(length(p)-radius)-state.y*.5;
 float coverage=1.-smoothstep(-.7,.7,d);
 float angle=mod(atan(p.x,p.y)+6.283185307,6.283185307);
 float sweep=state.x*6.283185307;
 vec2 endp=radius*vec2(sin(sweep),cos(sweep));
 float cap=min(length(p-vec2(0.,radius)),length(p-endp))-state.y*.5;
 float active=angle<=sweep ? coverage : 1.-smoothstep(-.7,.7,cap);
 if(state.x<=0.)active=0.;
 if(state.x>=1.)active=coverage;
 vec4 c=mix(track,fill,active);c.a*=max(coverage,active);fragColor=c;
}""")
        _shader = gpu.shader.create_from_info(info)
        _batch = batch_for_shader(
            _shader,
            "TRIS",
            {"pos": ((0, 0), (1, 0), (0, 1), (1, 1))},
            indices=((0, 1, 2), (2, 1, 3)),
        )
    gpu.state.blend_set("ALPHA")
    _shader.bind()
    _shader.uniform_float(
        "mvp", gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    )
    for name, value in [
        ("rect", rect),
        ("track", track),
        ("fill", fill),
        ("state", (value, thickness)),
    ]:
        _shader.uniform_float(name, value)
    _batch.draw(_shader)


def clear():
    global _shader, _batch
    _shader = _batch = None
