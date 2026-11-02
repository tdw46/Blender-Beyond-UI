import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas
from beyond_ui.tooltips import active, description


class ControlTooltips(unittest.TestCase):
    def fixture(self, enabled=True):
        c=Canvas(); b=c.button('b','Action',lambda:None,tooltip='Preserved native description', enabled=enabled)
        c.arrange(300); calls=[]; c.bind_context_tooltips(calls.append)
        ctx=NS(preferences=NS(view=NS(show_tooltips=True)))
        return c,b,calls,ctx

    def hover(self,c,b,ctx):
        x,y,w,h=b.rect
        c.event(NS(type='MOUSEMOVE',value='NOTHING'),x+w/2,y+h/2,(0,0,300,300),context=ctx)

    def test_disabled_controls_show_descriptions_and_cancel_clears_state(self):
        c,b,calls,ctx=self.fixture(False)
        self.hover(c,b,ctx); tip=active(c)
        self.assertIsNotNone(tip); self.assertEqual(calls,[0.55])
        tip.motion.clock=lambda:tip.tip_pending[4]+1
        self.assertIsNone(tip.reveal_tip(ctx));self.assertIn('Preserved native description', ' '.join(tip.tooltip[1]))
        c.cancel(); self.assertIsNone(active(c)); self.assertIsNone(tip.tooltip)

    def test_same_hover_retained_and_preferences_and_stale_owner_respected(self):
        c,b,calls,ctx=self.fixture();self.hover(c,b,ctx);tip=active(c)
        self.hover(c,b,ctx);self.assertIs(active(c),tip);self.assertEqual(calls,[0.55])
        ctx.preferences.view.show_tooltips=False
        tip.reveal_tip(ctx);self.assertIsNone(tip.tooltip)
        ctx.preferences.view.show_tooltips=True
        self.hover(c,b,ctx);c.controls.pop(b.key)
        tip.reveal_tip(ctx);self.assertIsNone(tip.tooltip)

    def test_rna_metadata_and_enum_help_preserved(self):
        item=NS(description='Choice details')
        meta=NS(description='Property details',type='ENUM',enum_items={'A':item})
        source=NS(metadata=lambda:meta,owner=lambda:NS(mode='A'),name='mode')
        c=NS(options={},binding=NS(context=source),label='Mode')
        self.assertEqual(description(c,None),'Property details\nChoice details')

    def test_widget_is_attached_before_its_first_layout_and_failure_rolls_back(self):
        c,b,_,_=self.fixture()
        widget=NS()
        def dimensions(*args):
            self.assertIs(c.overlay['widget'],widget)
            return 100,80
        widget.dimensions=dimensions
        c.open_widget(widget,b,(0,0,300,300));previous=c.overlay
        broken=NS(dimensions=lambda *a:(_ for _ in ()).throw(ValueError('bad layout')))
        with self.assertRaises(ValueError):c.open_widget(broken,b,(0,0,300,300))
        self.assertIs(c.overlay,previous)

    def test_developer_preferences_append_exact_component_path(self):
        from beyond_ui.tooltips import property_description
        ctx=NS(preferences=NS(view=NS(show_developer_ui=False,show_tooltips_python=False)))
        source=NS(owner=lambda:NS(bl_rna=NS(identifier='Object')),name='location',index=2,
                  paths=lambda:('location[2]', 'bpy.data.objects["Cube"].location[2]'))
        self.assertEqual(property_description(source,ctx,'Position'),'Position')
        for pref in ('show_developer_ui','show_tooltips_python'):
            setattr(ctx.preferences.view,pref,True)
            text=property_description(source,ctx,'Position')
            self.assertIn('Python: Object.location[2]',text)
            self.assertIn('bpy.data.objects["Cube"].location[2]',text)
            setattr(ctx.preferences.view,pref,False)

    def test_provider_contributions_keep_bound_actions_and_exact_clipboard(self):
        from beyond_ui.bindings import Binding
        from beyond_ui.context_menu import Entry
        c=Canvas();ctx=NS(preferences=NS(view=NS()),window_manager=NS(clipboard=''))
        source=NS(entries=lambda t,ctx:[Entry('FULL_PATH','Copy Full Data Path',
                         lambda t,ctx:setattr(ctx.window_manager,'clipboard','exact.owner.path'))])
        b=c.number('value','Value',Binding(lambda:1,lambda x:None,context=source),
                   context_menu=lambda t,ctx:[Entry('EXTRA','Extra')])
        c.arrange(300)
        self.assertTrue(c.open_context(b,20,20,(0,0,300,400),context=ctx),c.menu_error)
        self.assertEqual([r.key for r in c.context_menu.page.rows],['FULL_PATH','EXTRA'])
        c.context_menu.choose(0,ctx)
        self.assertEqual(ctx.window_manager.clipboard,'exact.owner.path')

    def test_menu_tooltip_lazy_and_stale_owner_safe(self):
        from beyond_ui.context_menu import Entry,Menu,Target
        c,b,calls,ctx=self.fixture();seen=[]
        m=Menu(Target('row'),[Entry('row','Field',tooltip=lambda ctx:seen.append(1) or 'Python: owner.value')],
               (0,0),(0,0,300,400),context=ctx)
        self.assertEqual(seen,[])
        m.hover_tip(0,20,20,ctx);self.assertEqual(seen,[1])
        self.assertEqual(m.tip_pending[1],'Python: owner.value')
