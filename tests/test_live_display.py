import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout
from beyond_ui.layout_recording import Tape
from beyond_ui.hosts.floating import visible_region_rect

class LiveDisplay(unittest.TestCase):
    def test_unchanged_redraw_uses_recorded_signature(self):
        from unittest.mock import patch

        old, new = self.tape('0.251'), self.tape('0.251')
        with patch('beyond_ui.layout_recording.freeze', side_effect=AssertionError('refrozen')):
            self.assertTrue(old.patch_display(new))

    def tape(self, text, *, icon='NONE', enabled=True):
        tape = Tape()
        row = tape.root.row()
        row.enabled = enabled
        row.label(text=text, icon=icon, translate=False)
        row.label(text='Unchanged', translate=False)
        return tape

    def test_text_updates_preserve_controls_and_skip_unchanged_layout(self):
        ui = Layout()
        tape = self.tape('0.251')
        tape.play(ui)
        ui.canvas.arrange(300)
        controls = tuple(ui.canvas.controls.values())
        count = ui.canvas.layout_count
        self.assertTrue(tape.patch_display(self.tape('0.251')))
        ui.canvas.arrange(300)
        self.assertEqual(ui.canvas.layout_count, count)
        self.assertTrue(tape.patch_display(self.tape('0.750')))
        self.assertEqual(controls[0].label, '0.750')
        self.assertEqual(tuple(ui.canvas.controls.values()), controls)
        self.assertEqual(controls[1].label, 'Unchanged')
        self.assertFalse(tape.patch_display(self.tape('0.999', enabled=False)))
        self.assertEqual(controls[0].label, '0.750')

    def test_list_membership_changes_cannot_be_mistaken_for_text_only(self):
        ui = Layout()
        old = self.tape("0.2")
        old.play(ui)
        new = self.tape("0.2")
        old.extra_signature = [(2, 0, "a")]
        new.extra_signature = [(3, 1, "b")]
        self.assertFalse(old.patch_display(new))

    def test_overlapping_sidebar_and_headers_excluded(self):
        window = NS(type='WINDOW', x=4,y=417,width=2602,height=1509)
        sidebar = NS(type='UI', x=1766,y=417,width=840,height=1401)
        header = NS(type='HEADER',x=4,y=1872,width=2602,height=54)
        tool_header = NS(type='TOOL_HEADER',x=4,y=1818,width=2602,height=54)
        area = NS(regions=[window,sidebar,header,tool_header])
        self.assertEqual(visible_region_rect(area,window),(0,0,1762,1401))
        sidebar.width=sidebar.height=1
        self.assertEqual(visible_region_rect(area,window),(0,0,2602,1401))

    def test_nonoverlapping_sidebar_does_not_shrink_view_and_left_toolbar_offsets(self):
        window=NS(type='WINDOW',x=100,y=30,width=700,height=500)
        sidebar=NS(type='UI',x=800,y=30,width=300,height=500)
        tools=NS(type='TOOLS',x=100,y=30,width=40,height=500)
        self.assertEqual(visible_region_rect(NS(regions=[window,sidebar,tools]),window),(40,0,660,500))
