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
result = dict(passed=True, version=bpy.app.version_string, build=bpy.app.build_hash.decode(),
              platform=manifest['platform'], portable=True, context_restored=True,
              dynamic_enum=True, property_state_abi=True, visual_qa=False)
output = Path(os.environ.get('BEYOND_UI_TEST_RESULT', ROOT/'build/portable-smoke/result.json'))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2))
print('BEYOND_UI_PORTABLE_OK', json.dumps(result))
