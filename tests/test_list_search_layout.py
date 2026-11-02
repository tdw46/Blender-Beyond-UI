import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.bindings import Binding
from beyond_ui.registered_list import reflow_search_item
from beyond_ui.search import CollectionSearch,clear_rect

class ListSearchLayout(unittest.TestCase):
    def build(self):
        binding=Binding(lambda:'Cam_Left',lambda value:None)
        canvas=Canvas();row=canvas.row();toggle=row.add('toggle','enabled',width=38,binding=binding)
        column=row.column();name=column.add('text','name',emboss='NONE',binding=binding);search=column.add('search','search',icon='SHAPEKEY_DATA',binding=binding)
        value=row.add('label','value','0.251');action=row.add('button','camera',icon='RESTRICT_RENDER_OFF')
        return canvas,(toggle,name,search,value,action)

    def test_shared_grid_preserves_all_controls_and_owners(self):
        canvas,controls=self.build();original=dict(canvas.controls)
        reflow_search_item(canvas);canvas.arrange(320)
        toggle,name,search,value,action=controls
        self.assertEqual(original,canvas.controls)
        self.assertAlmostEqual(name.rect[0],search.rect[0]+canvas.theme.icon_size+6)
        self.assertAlmostEqual(action.rect[0]+action.rect[2],search.rect[0]+search.rect[2])
        self.assertGreater(search.rect[1],name.rect[1])
        self.assertEqual(name.options['_inline_style']['font_weight'],'bold')
        self.assertEqual(toggle.options['width'],32)

    def test_value_surface_keeps_name_search_grid_and_button_owner(self):
        from beyond_ui.canvas import Group
        canvas, controls = self.build()
        row = canvas.children[0]
        value = controls[3]
        wrapper = Group(canvas, 'column', row, _style_wrapper=True, width=54)
        wrapper.children = [value]
        row.children[row.children.index(value)] = wrapper
        reflow_search_item(canvas)
        canvas.arrange(320)
        self.assertAlmostEqual(controls[1].rect[0], controls[2].rect[0]+canvas.theme.icon_size+6)
        self.assertTrue(controls[4].options['list_action'])
        self.assertIn(value, wrapper.children)
        self.assertEqual(wrapper.options['width'], 54)

    def test_authored_geometry_is_not_restructured(self):
        canvas,controls=self.build();row=canvas.children[0];row.options['_inline_geometry']=True
        before=tuple(row.children);reflow_search_item(canvas)
        self.assertEqual(before,tuple(row.children))

    def model(self,commit=lambda a,b:None):
        state={'value':'Cam_Left','valid':True,'editable':True}
        model=CollectionSearch.__new__(CollectionSearch)
        model.binding=Binding(lambda:state['value'],lambda v:state.update(value=v),lambda:state['valid'],commit)
        model.source=NS(editable=lambda:state['editable']);model.pointer=None;model.canvas=None;model.control=None
        return model,state

    def test_clear_is_transactional_and_revalidates_owner(self):
        commits=[];model,state=self.model(lambda a,b:commits.append((a,b)))
        self.assertTrue(model.can_clear());self.assertTrue(model.clear())
        self.assertEqual(commits,[('Cam_Left','')]);self.assertFalse(model.can_clear())
        state.update(value='Cam_Left',valid=False)
        with self.assertRaises(ReferenceError):model.clear()
        self.assertEqual(state['value'],'Cam_Left')
        state.update(valid=True,editable=False)
        with self.assertRaises(ReferenceError):model.clear()

    def test_failed_commit_rolls_back(self):
        def fail(a,b):raise RuntimeError('commit failed')
        model,state=self.model(fail)
        with self.assertRaises(RuntimeError):model.clear()
        self.assertEqual(state['value'],'Cam_Left')
        self.assertEqual(clear_rect((10,20,100,24)),(88,20,22,24))
