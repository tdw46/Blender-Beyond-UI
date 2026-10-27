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
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(json.dumps(result, indent=2))
