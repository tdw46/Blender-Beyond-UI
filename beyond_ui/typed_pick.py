"""Window-scoped eyedroppers for RNA-backed controls. No selection or mode changes."""
from .search import field_rect
from .context_menu import inside

_sessions = {}


# Object datablocks and the two more specific hits resolved by the viewport
# sampler (face material and armature bone). Store eligibility on the model
# once during authoring, including for empty search collections.
_SCENE_TYPES = frozenset({
    "Object", "Mesh", "Curve", "Curves", "MetaBall", "Light", "Speaker",
    "LightProbe", "Camera", "Lattice", "GreasePencil", "GreasePencilv3",
    "Armature", "PointCloud", "Volume", "Material", "Bone", "PoseBone", "EditBone",
})


def scene_type(rna_type):
    while rna_type is not None:
        if rna_type.identifier in _SCENE_TYPES:
            return True
        rna_type = rna_type.base
    return False


def supported(control):
    if control.kind == "enum":
        return callable(control.options.get("eyedropper_items"))
    field = control.options.get("search_field") or control.options.get("pointer_field")
    return control.kind in {"pointer", "search"} and getattr(field, "scene_pickable", False)


def button_rect(control):
    x, y, w, h = field_rect(control)
    # Leave the body accessible at very narrow widths.
    width = min(20., w * .30)
    return x+w-width, y, width, h


def _ptr(value):
    return value.as_pointer() if hasattr(value, "as_pointer") else None


def stop(key):
    record = _sessions.pop(key, None)
    if record:
        try:
            record[0].cursor_modal_restore()
            record[0].workspace.status_text_set(None)
        except (RuntimeError, ReferenceError):
            pass


def clear():
    for key in tuple(_sessions):
        stop(key)


def start(canvas, target, context):
    if not supported(target):
        return False
    win = context.window
    key = win.as_pointer()
    stop(key)
    binding = target.binding
    before = binding.read()
    model = target.options.get("search_field") or target.options.get("pointer_field")
    if target.kind == "search":
        model.refresh()  # Pin collection identity/revision exactly like the menu.
    elif target.kind == "pointer":
        picker = model.picker(canvas, target)
    else:
        enum = target.options["enum_field"]
        choices = enum.snapshot()
    owner = binding.context.owner().as_pointer()

    def assign(values, src=None):
        if (not canvas.visible or canvas.controls.get(target.key) is not target or not target.enabled
                or not binding.valid() or not binding.context.editable()
                or binding.context.owner().as_pointer() != owner or binding.read() != before):
            raise ReferenceError("The destination changed; start the eyedropper again")
        if src is target:
            return False
        if target.kind != "enum":
            for item in values:
                key = _ptr(item)
                if key is None:
                    continue
                if target.kind == "search":
                    if model.valid(key):
                        return model.select(key)
                elif picker.valid(key):
                    return picker.select(key)
            return False
        resolver = target.options["eyedropper_items"]
        ids = {_ptr(item) for item in values if _ptr(item) is not None}
        matches = {identifier for item, identifier in resolver(binding.context.owner(), binding.context.name)
                   if _ptr(item) in ids}
        if len(matches) == 1:
            identifier = matches.pop()
            choice = next((item for item in choices if item.identifier == identifier), None)
            if choice and choice in enum.snapshot():
                enum.choose(choice, original=before, exclusive=enum.flag)
                return True
        return False

    _sessions[key] = win, target, assign, canvas
    win.cursor_modal_set("EYEDROPPER")
    win.workspace.status_text_set("Pick a compatible scene item or field  •  Esc to cancel")
    return True


def _under_field(hosts, win, mx, my):
    for host in hosts:
        for key, rec in tuple(host.records.items()):
            if key[0] != win.as_pointer() or not rec.get("valid") or not rec.get("rect"):
                continue
            area = next((a for a in win.screen.areas if a.as_pointer()==key[1]), None)
            region = next((r for r in area.regions if r.as_pointer()==key[2]), None) if area else None
            if not region or not inside(rec["clip"],mx-region.x,my-region.y):
                continue
            canvas = rec["canvas"]
            x,y,w,h = rec["rect"]
            px=(mx-region.x-x)*canvas._width/max(1,w)
            py=(y+h-my+region.y)*canvas.height/max(1,h)
            control=canvas.hit(px,py,(0,0,canvas._width,canvas.height),include_disabled=True)
            if control and control.kind=="widget":
                widget=control.options["widget"]
                if hasattr(widget,"all_children"):
                    a,b,c,d=control.rect
                    rx=(px-a)*widget.width/max(1,c); ry=(py-b)*widget.height/max(1,d)
                    for child,rect,_ in widget.all_children():
                        if inside(rect,rx,ry):
                            return child.hit(rx-rect[0],ry-rect[1],(0,0,*rect[2:]),include_disabled=True)
            return control
    return None


def _field_values(src):
    if not src or not src.binding or not src.binding.valid():
        return []
    value=src.binding.read()
    if _ptr(value) is not None:
        return [value]
    model=src.options.get("search_field")
    if model and isinstance(value,str):
        return [v for v in model.collection() if getattr(v,model.item_name)==value]
    return []


def _viewport(context,target,mx,my):
    from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d
    from mathutils import Vector
    area=next((a for a in context.window.screen.areas if a.type=="VIEW_3D" and inside((a.x,a.y,a.width,a.height),mx,my)),None)
    if not area:
        return []
    region=next((r for r in area.regions if r.type=="WINDOW" and inside((r.x,r.y,r.width,r.height),mx,my)),None)
    if not region or any(r.type!="WINDOW" and r.width>1 and r.height>1 and inside((r.x,r.y,r.width,r.height),mx,my) for r in area.regions):
        return []
    with context.temp_override(area=area,region=region):
        rv=context.region_data
        if not rv:
            return []
        at=Vector((mx-region.x,my-region.y))
        model=target.options.get("search_field")
        resolver=target.options.get("eyedropper_items")
        eligible = ({_ptr(item) for item,_ in resolver(target.binding.context.owner(),target.binding.context.name)}
                    if resolver else set())
        pointer=target.options.get("pointer_field")
        bone_pointer = getattr(getattr(pointer, "type", None), "__name__", "") in {"Bone","PoseBone","EditBone"}
        if model and model.name in {"bones","edit_bones"} or eligible or bone_pointer:
            owner=model.resolve() if model else None
            nearest=None
            for obj in context.visible_objects:
                if obj.type!="ARMATURE" or not (bone_pointer or eligible or obj.data==owner or obj.pose==owner):
                    continue
                for bone in (obj.data.edit_bones if obj.mode=="EDIT" else obj.pose.bones):
                    data=getattr(bone,"bone",bone)
                    if eligible and _ptr(data) not in eligible and _ptr(bone) not in eligible:
                        continue
                    if getattr(data,"hide",False) or not getattr(data,"visible",True):
                        continue
                    a=location_3d_to_region_2d(region,rv,obj.matrix_world@bone.head)
                    b=location_3d_to_region_2d(region,rv,obj.matrix_world@bone.tail)
                    if a is None or b is None:
                        continue
                    ab=b-a
                    dist=(at-(a+ab*max(0,min(1,(at-a).dot(ab)/max(ab.length_squared,1e-9))))).length
                    if dist<=10*context.preferences.system.ui_scale and (nearest is None or dist<nearest[0]):
                        nearest=(dist,bone,data)
            if nearest:
                return [model.collection().get(nearest[1].name)] if model else list(nearest[1:])
            if model:
                return []
        # Wire-only scene objects have no ray-cast surface. Sample their visible
        # origin within a small screen-space tolerance, not a global active ID.
        points = []
        for obj in context.visible_objects:
            if obj.type not in {"EMPTY","LIGHT","CAMERA","SPEAKER","LIGHT_PROBE"} or eligible and _ptr(obj) not in eligible:
                continue
            uv=location_3d_to_region_2d(region,rv,obj.matrix_world.translation)
            if uv is not None and (uv-at).length <= 9*context.preferences.system.ui_scale:
                points.append(((uv-at).length,obj))
        if points:
            obj=min(points,key=lambda pair:pair[0])[1]
            return [obj,obj.data]
        deps=context.evaluated_depsgraph_get()
        hit,_,_,face,obj,_=context.scene.ray_cast(deps,region_2d_to_origin_3d(region,rv,at),region_2d_to_vector_3d(region,rv,at))
        if not hit or not obj:
            return []
        obj=obj.original
        values=[obj,obj.data]
        evaluated=obj.evaluated_get(deps)
        polys=getattr(evaluated.data,"polygons",())
        if 0<=face<len(polys):
            idx=polys[face].material_index
            if idx<len(evaluated.material_slots):
                mat=evaluated.material_slots[idx].material
                if mat:
                    mat=mat.original
                    values.append(mat)
        return values


def dispatch(runtime,context,event):
    if not _sessions:
        return None
    win=context.window
    key=win.as_pointer() if win else 0
    state=_sessions.get(key)
    if not state:
        return None
    if event.type in {"ESC","RIGHTMOUSE","WINDOW_DEACTIVATE"}:
        stop(key)
    elif event.type=="LEFTMOUSE" and event.value=="PRESS":
        _,target,assign,canvas=state
        try:
            src=_under_field(runtime.hosts.values(),win,event.mouse_x,event.mouse_y)
            values=_field_values(src) if src else _viewport(context,target,event.mouse_x,event.mouse_y)
            if assign(values,src):
                stop(key)
                runtime.redraw()
            else:
                win.workspace.status_text_set("No compatible value here  •  Pick again or press Esc")
        except (AttributeError,ReferenceError,RuntimeError,ValueError,TypeError) as error:
            canvas.menu_error=str(error)
            stop(key)
    elif event.type not in {"MOUSEMOVE","INBETWEEN_MOUSEMOVE","LEFTMOUSE"}:
        return {"PASS_THROUGH"}
    return {"RUNNING_MODAL"}
