"""Disposable-profile ABI smoke test; requires the portable package, never legacy fallback."""
import json
import os
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.hosts import bridge, portable, portable_actions, menu_context, menu_native

lib, manifest = portable.load()
state = bridge.load()
assert state.portable, 'Legacy fallback cannot qualify portable support'
assert portable_actions.library() is lib
assert menu_native.api() is not None, menu_native.reason()
context = bpy.context
with menu_context.scope(context, {'beyond_probe': 'Outer Δ'}):
    assert context.beyond_probe == 'Outer Δ'
    with menu_context.scope(context, {'beyond_probe': 'Inner'}):
        assert context.beyond_probe == 'Inner'
    assert context.beyond_probe == 'Outer Δ'
assert getattr(context, 'beyond_probe', None) is None
assert lib.beyond_context_active() == 0
items = menu_native.enum_items(context.object, 'rotation_mode', context)
assert items and any(item.identifier == 'XYZ' for item in items), items
portable_actions.property_api(lib)
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Target
area=next(a for a in context.screen.areas if a.type == 'VIEW_3D')
with context.temp_override(area=area):
    owner=context.object
    source=rna_binding(lambda:owner,'location',index=1).context
    target=Target('Location',valid=source.valid,commit=lambda _:None)
    driver=owner.driver_add('location',1)
    driver.driver.expression='2.75'
    menu_native.driver_apply('COPY_DRIVER',source,target)
    assert menu_native.api()['available']()
    owner.driver_remove('location',1)
    menu_native.driver_apply('PASTE_DRIVER',source,target)
    assert owner.animation_data.drivers[0].driver.expression == '2.75'
    menu_native.add_property_favorite(source,context)
    assert menu_native.property_favorite(source,context)
    assert menu_native.property_favorite(source,context,remove=True)
    assert not menu_native.property_favorite(source,context)
    menu_native.add_operator_favorite('wm.context_toggle',{'data_path':'object.show_name'},'INVOKE_DEFAULT',context)
    assert menu_native.operator_favorite('wm.context_toggle',{'data_path':'object.show_name'},'INVOKE_DEFAULT',context,operation='REMOVE')
    owner['probe_gain']=0.5
    custom=rna_binding(lambda:owner,'["probe_gain"]').context
    assert menu_context.custom_property(context,custom) is not None
    assert lib.beyond_context_active() == 0
result = dict(passed=True, version=bpy.app.version_string, build=bpy.app.build_hash.decode(),
              platform=manifest['platform'], portable=True, context_restored=True,
              dynamic_enum=True, property_state_abi=True, driver_clipboard=True, favorites=True, custom_property_context=True, visual_qa=False)
output = Path(os.environ.get('BEYOND_UI_TEST_RESULT', ROOT/'build/portable-smoke/result.json'))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2))
print('BEYOND_UI_PORTABLE_OK', json.dumps(result))
