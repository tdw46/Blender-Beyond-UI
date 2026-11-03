"""Opt-in authored row revisions preserve live bindings and stale-owner guards."""
import bpy, json, os, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
import registered_lists_fixture as fixture
from beyond_ui import Layout

draws = 0
class BUI_UL_revision(bpy.types.UIList):
    def draw_item_cache_key(self, context, owner, item, index):
        return item.name
    def draw_item(self, context, layout, owner, item, icon, active_data, active_property, index):
        global draws
        draws += 1
        layout.label(text=item.name)
        layout.prop(item, 'enabled')

class BUI_UL_text_revision(BUI_UL_revision):
    def draw_item_cache_key(self, context, owner, item, index):
        return 'same structure'
    def draw_item_texts(self, context, owner, item, index):
        return (item.name,)

try:
    fixture.register(20)
    bpy.utils.register_class(BUI_UL_revision)
    ui = Layout(context=bpy.context, list_identity=lambda owner, prop, item: item.uid)
    ui.template_list('BUI_UL_revision', 'revision', bpy.context.scene, 'bui_list_items', bpy.context.scene, 'bui_list_active', rows=5)
    ui.canvas.arrange(560)
    widget = next(c.options['widget'] for c in ui.canvas.controls.values() if c.kind=='widget')
    before = draws
    for _ in range(20): widget.refresh_display()
    assert draws == before, (draws, before)
    child, _, item = next(iter(widget.row_map.values()))
    control = next(c for c in child.controls.values() if c.kind=='toggle')
    value = control.binding.read()
    item.owner.enabled = not value
    widget.refresh_display()
    assert control.binding.read() is not value and draws == before
    item.owner.name = 'Changed authored text'
    widget.prepare()  # Layout-only passes cannot acknowledge unauthored text.
    assert draws == before
    widget.refresh_display()
    assert draws == before + 1
    assert any(c.label=='Changed authored text' for c in child.controls.values())
    bpy.context.scene.bui_list_items.remove(item.index)
    widget._painting_context = widget.context
    assert not control.binding.valid(), 'Paint scope hid deleted exact owner'
    widget._painting_context = None
    assert not control.binding.valid(), 'Deleted row retained editable ownership'
    ui.canvas.park()
    bpy.utils.register_class(BUI_UL_text_revision)
    text_ui = Layout(context=bpy.context, list_identity=lambda owner, prop, item: item.uid)
    text_ui.template_list('BUI_UL_text_revision', 'texts', bpy.context.scene, 'bui_list_items', bpy.context.scene, 'bui_list_active', rows=5)
    text_ui.canvas.arrange(560)
    text_widget = next(c.options['widget'] for c in text_ui.canvas.controls.values() if c.kind=='widget')
    text_child, _, text_item = next(iter(text_widget.row_map.values()))
    before = draws
    text_item.owner.name = 'Text-only current label'
    text_widget.refresh_display()
    assert draws == before, 'Text-only update reran the row callback'
    assert any(c.label=='Text-only current label' for c in text_child.controls.values())
    text_ui.canvas.park()
    bpy.utils.unregister_class(BUI_UL_text_revision)
    bpy.utils.unregister_class(BUI_UL_revision)
    fixture.unregister()
    result = dict(passed=True, checks=['Unchanged rows skip authoring', 'Bound values remain live', 'Changed literal reauthors one row', 'Deletion invalidates exact owner'])
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ['BEYOND_UI_TEST_RESULT']).write_text(json.dumps(result,indent=2))
