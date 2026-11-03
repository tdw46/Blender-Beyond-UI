import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout
from beyond_ui.layout_recording import Tape
from beyond_ui.hosts.floating import visible_region_rect

class LiveDisplay(unittest.TestCase):
    def test_retained_text_refresh_matches_full_recording_without_authoring(self):
        ui = Layout()
        old = self.tape('0.000')
        old.play(ui)
        ui.canvas.arrange(300)
        control = next(iter(ui.canvas.controls.values()))
        for value in ('0.250', '0.800', '0.000'):
            old.patch_texts((value, 'Unchanged'))
            self.assertEqual(control.label, value)
            self.assertEqual(old.signature, self.tape(value).signature)
        with self.assertRaises(ValueError): old.patch_texts(('missing label',))
        with self.assertRaises(TypeError): old.patch_texts((3, 'Unchanged'))

    def test_fixed_value_refresh_preserves_geometry_motion_and_other_edit(self):
        from beyond_ui import style
        def record(value, wrap=False):
            tape = Tape()
            tape.root.label(text=value, translate=False)
            style(tape.root, width=48, wrap=wrap)
            tape.root.label(text='Stable', translate=False)
            return tape
        ui = Layout()
        old = record('0.000')
        old.play(ui)
        ui.canvas.arrange(300)
        control = next(iter(ui.canvas.controls.values()))
        before = (ui.canvas.layout_count, ui.canvas.backdrop_revision, control.rect)
        edit = object()
        ui.canvas.edit = edit
        for value in ('0.125', '0.800', '1.000'):
            self.assertTrue(old.patch_display(record(value)))
            ui.canvas.arrange(300)
            self.assertEqual(control.label, value)
            self.assertEqual((ui.canvas.layout_count, ui.canvas.backdrop_revision, control.rect), before)
            self.assertIs(ui.canvas.edit, edit)
        self.assertFalse(old.patch_display(record('1.000', wrap=True)))

    def test_changed_text_uses_recorded_non_display_command_snapshots(self):
        from unittest.mock import patch
        import beyond_ui.layout_recording as recording
        ui = Layout()
        old, new = self.tape('0.000'), self.tape('0.250')
        old.play(ui)
        original = recording.freeze
        def freeze(value):
            # Only the changed label's text-free structural signature needs
            # comparison. All other command snapshots already exist.
            if isinstance(value, tuple) and len(value) == 6:
                self.assertEqual(value[2], 'label')
                self.assertNotIn('text', value[4])
            return original(value)
        with patch.object(recording, 'freeze', freeze):
            self.assertTrue(old.patch_display(new))

    def test_intrinsic_label_reflows_without_cancelling_an_unrelated_edit(self):
        ui = Layout()
        old = self.tape('Short')
        old.play(ui)
        ui.canvas.arrange(300)
        count = ui.canvas.layout_count
        edit = object()
        ui.canvas.edit = edit
        self.assertTrue(old.patch_display(self.tape('A much longer label')))
        ui.canvas.arrange(300)
        self.assertGreater(ui.canvas.layout_count, count)
        self.assertIs(ui.canvas.edit, edit)

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

    def test_window_overlay_includes_sidebar_excludes_headers(self):
        window = NS(type='WINDOW', x=4,y=417,width=2602,height=1509)
        sidebar = NS(type='UI', x=1766,y=417,width=840,height=1401)
        header = NS(type='HEADER',x=4,y=1872,width=2602,height=54)
        tool_header = NS(type='TOOL_HEADER',x=4,y=1818,width=2602,height=54)
        area = NS(regions=[window,sidebar,header,tool_header])
        self.assertEqual(visible_region_rect(area,window),(0,0,2602,1401))
        sidebar.width=sidebar.height=1
        self.assertEqual(visible_region_rect(area,window),(0,0,2602,1401))

    def test_window_overlay_includes_nonoverlapping_sidebar_and_toolbar(self):
        window=NS(type='WINDOW',x=100,y=30,width=700,height=500)
        sidebar=NS(type='UI',x=800,y=30,width=300,height=500)
        tools=NS(type='TOOLS',x=100,y=30,width=40,height=500)
        self.assertEqual(visible_region_rect(NS(regions=[window,sidebar,tools]),window),(0,0,1000,500))
