"""Runtime API coverage and register/reload probes; no file/preferences saves."""

import bpy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui import NativeLayout as Layout
from beyond_ui.bindings import rna_binding, Edit

inventory = json.loads((ROOT / "docs/api_inventory.json").read_text())
version = ".".join(str(v) for v in bpy.app.version[:2])
missing = {}
for typename, data in inventory[version].items():
    cls = getattr(bpy.types, typename)
    absent = [
        name
        for name in data["members"]
        if not hasattr(cls, name)
        and name not in cls.bl_rna.properties
        and name not in cls.bl_rna.functions
    ]
    # RNA instance properties are materialized on instances; class definitions
    # above need only expose their RNA descriptors, not instance attribute reads.
    if absent:
        missing[typename] = absent
assert not missing, missing
scene = bpy.context.scene
binding = rna_binding(lambda: scene.render, "resolution_percentage")
old = binding.read()
edit = Edit(binding)
edit.update(37)
assert binding.read() == 37
edit.finish(cancel=True)
assert binding.read() == old
for name in ("beyond_ui_test_vendor_a", "beyond_ui_test_vendor_b"):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "beyond_ui/__init__.py",
        submodule_search_locations=[str(ROOT / "beyond_ui")],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert module.Canvas().__class__.__module__ == name + ".canvas"

# Validate host-independent demo class registration twice; no native GPU calls
# are allowed in background mode.
spec = importlib.util.spec_from_file_location(
    "beyond_ui_demo_test", ROOT / "examples/demo.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
for _ in range(2):
    for cls in demo.CLASSES:
        bpy.utils.register_class(cls)
    for cls in reversed(demo.CLASSES):
        bpy.utils.unregister_class(cls)
result = {
    "passed": True,
    "version": bpy.app.version_string,
    "build": bpy.app.build_hash.decode(),
    "documented_members": {k: len(v["members"]) for k, v in inventory[version].items()},
    "checks": [
        "documented RNA availability",
        "RNA edit rollback",
        "two vendor namespaces",
        "register/unregister twice",
    ],
    "platform": sys.platform,
}
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
print("BEYOND_UI_RUNTIME_PASS", json.dumps(result))

# Custom authoring must never forward to a native UI. Exercise real RNA models.
from beyond_ui import Layout as CustomLayout, UnsupportedControl
from beyond_ui.widgets.rna import color_ramp, curve_mapping

custom = CustomLayout(context=bpy.context)
custom.prop(scene.render, "resolution_percentage")
custom.prop(scene.render, "film_transparent")
assert {c.kind for c in custom.canvas.controls.values()} == {"number", "toggle"}
material = bpy.data.materials.new("Beyond UI isolated fixture")
try:
    material.use_nodes = True
    ramp_node = material.node_tree.nodes.new("ShaderNodeValToRGB")
    curve_node = material.node_tree.nodes.new("ShaderNodeRGBCurve")
    curve_node.mapping.initialize()
    custom.template_color_picker(ramp_node.color_ramp.elements[0], "color")
    custom.template_color_ramp(ramp_node, "color_ramp")
    custom.template_curve_mapping(curve_node, "mapping")
    rb, ramp = color_ramp(ramp_node, "color_ramp", lambda a, b: None)
    before = rb.read()
    edit = Edit(rb)
    edit.update(((0.2, (0.1, 0.2, 0.3, 1.0)), before[1]))
    edit.finish(cancel=True)
    assert rb.read() == before
    cb, mapping, curve = curve_mapping(curve_node, "mapping", lambda a, b: None, [0])
    before = cb.read()
    edit = Edit(cb)
    edit.update(((0.2, 0.3), before[1]))
    edit.finish(cancel=True)
    assert cb.read() == before
    try:
        custom.template_waveform(None, "scopes")
    except UnsupportedControl:
        pass
    else:
        raise AssertionError("Unsupported custom template must not silently fall back")
finally:
    bpy.data.materials.remove(material)
result["checks"] += [
    "custom RNA authoring without native delegation",
    "custom ramp/curve transaction rollback",
    "unsupported template fails explicitly",
]
# New custom palette/progress/matrix adapters, with disposable RNA owners.
from beyond_ui.widgets.rna import matrix_components, palette_source
from mathutils import Matrix, Euler, Vector
from types import SimpleNamespace

palette = bpy.data.palettes.new("Beyond UI test palette")
obj = bpy.data.objects.new("Beyond UI matrix test", None)
bpy.types.Scene.beyond_ui_test_palette = bpy.props.PointerProperty(
    type=bpy.types.Palette
)
try:
    scene.beyond_ui_test_palette = palette
    for rgb in ((0.1, 0.2, 0.3), (0.3, 0.4, 0.5), (0.5, 0.6, 0.7)):
        palette.colors.new().color = rgb
    palette.colors.active = palette.colors[0]
    commits = []
    edited = []
    source = palette_source(
        scene,
        "beyond_ui_test_palette",
        lambda a, b: commits.append((a, b)),
        edit=edited.append,
    )
    source.select(1)
    assert palette.colors.active == palette.colors[1]
    source.add()
    assert len(palette.colors) == 4 and source.active() == 3
    source.remove()
    assert len(palette.colors) == 3 and source.active() == 2
    source.edit(0)
    binding = edited[-1]
    before = binding.read()
    edit = Edit(binding)
    edit.update((0.8, 0.7, 0.6))
    edit.finish(cancel=True)
    assert binding.read() == before
    # Deferred picker cannot be redirected to the next element after deletion.
    palette.colors.remove(palette.colors[0])
    assert not binding.valid()
    ui = type(custom)(context=bpy.context)
    control = ui.template_palette(scene, "beyond_ui_test_palette", color=True)
    assert control.options["widget"].show_colors
    default_control = ui.template_palette(scene, "beyond_ui_test_palette")
    native_has_color = (
        "color" in bpy.types.UILayout.bl_rna.functions["template_palette"].parameters
    )
    assert default_control.options["widget"].show_colors == (not native_has_color)
    ui.progress(factor=0.65, type="BAR", text="Preparing assets")
    ui.progress(factor=0.65, type="RING")
    obj.matrix_world = Matrix.LocRotScale(
        Vector((2, 3, 4)), Euler((0.1, 0.2, 0.3)).to_quaternion(), Vector((2, 3, 4))
    )
    matrix = matrix_components(obj, "matrix_world")
    before = tuple(tuple(row) for row in obj.matrix_world)
    values = matrix.read()
    assert all(abs(a - b) < 1e-5 for a, b in zip(values[0], (2, 3, 4)))
    assert values is matrix.read(), "Warm matrix decomposition was repeated"
    assert all(abs(a - b) < 1e-4 for a, b in zip(values[2], (2, 3, 4)))
    try:
        matrix.write(None)
    except TypeError:
        pass
    else:
        raise AssertionError("Matrix template must be read-only")
    ui.template_matrix(obj, "matrix_world")
    assert tuple(tuple(row) for row in obj.matrix_world) == before
    try:
        ui.template_matrix(obj, "location")
    except TypeError:
        pass
    else:
        raise AssertionError("Matrix template must reject non-matrix RNA")
    # Preserve the legacy weight-value route without treating a scalar as RGB.
    from beyond_ui.bindings import Binding

    weight = [0.37]
    wb = Binding(lambda: weight[0], lambda v: weight.__setitem__(0, v))
    weight_source = palette_source(
        scene, "beyond_ui_test_palette", lambda a, b: None, brush=wb, value_mode=True
    )
    weight_source.add()
    assert abs(palette.colors[-1].weight - 0.37) < 1e-6
    palette.colors[0].weight = 0.63
    weight_source.select(0)
    assert abs(weight[0] - 0.63) < 1e-6
    scene.beyond_ui_test_palette = None
    assert not source.valid()
    assert len(commits) == 3
    result["checks"] += [
        "custom palette selection/add/remove and canceled color edit",
        "palette stale-element and owner rejection",
        "legacy palette color flag and 5.2 default",
        "read-only matrix decomposition cache and type validation",
        "custom BAR/RING authoring",
    ]
finally:
    del bpy.types.Scene.beyond_ui_test_palette
    bpy.data.palettes.remove(palette)
    bpy.data.objects.remove(obj)
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
