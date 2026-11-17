import unittest
from beyond_ui import Layout, style
from beyond_ui.gpu.icons import layer_color


class SegmentedIcons(unittest.TestCase):
    def test_segment_style_retains_action_and_selection(self):
        ui=Layout();clicked=[]
        control=ui.group.button('choice','Choice',lambda:clicked.append(True),selected=True,menu_option=True)
        action=control.action
        style(ui,enum_style='segment',icon='BUI_LENS',font_weight='bold')
        self.assertFalse(control.options['menu_option'])
        self.assertIs(control.action,action)
        self.assertTrue(control.options['selected'])
        style(ui,enum_style='track')
        self.assertFalse(control.options['menu_option'])
        self.assertIs(control.action,action)
        style(ui,enum_style='menu')
        self.assertTrue(control.options['menu_option'])
        with self.assertRaises(ValueError):style(ui,enum_style='invalid')

    def test_joined_track_allocates_equal_adjacent_hit_targets(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row(align=True)
        style(row, scope="group", enum_style="track", gap=0)
        left = row.group.button("on", "On", lambda: None, selected=True)
        right = row.group.button("off", "A longer choice", lambda: None, selected=False)
        for width in (92, 240, 400):
            ui.canvas.arrange(width)
            x, y, w, h = left.rect
            self.assertEqual(right.rect, (x+w, y, w, h))
            self.assertEqual(left.options["_track_edges"], (True, False))
            self.assertEqual(right.options["_track_edges"], (False, True))

    def test_split_action_reserves_menu_width_without_a_seam_gap(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row(align=True)
        style(row, scope="group", enum_style="track", gap=0)
        label = row.group.button("category", "Category", lambda: None)
        menu = row.group.button("actions", "", lambda: None)
        style(row, width=24, icon="DOWNARROW_HLT")
        for width in (96, 180, 260):
            ui.canvas.arrange(width)
            x, y, w, h = label.rect
            self.assertEqual(menu.rect, (x + w, y, 24, h))
            self.assertGreater(w, 24)

    def test_compact_track_centers_beside_a_tall_caption(self):
        ui = Layout()
        ui.canvas.panel_layout = True
        row = ui.row()
        caption = row.group.button("simulation", "Spring Simulation", lambda: None)
        style(row, height=44)
        track = row.row()
        style(track, scope="group", enum_style="track", gap=0, height=22)
        on = track.group.button("on", "ON", lambda: None)
        track.group.button("off", "OFF", lambda: None)
        ui.canvas.arrange(320)
        self.assertAlmostEqual(caption.rect[1] + caption.rect[3]/2, on.rect[1] + on.rect[3]/2)

    def test_authored_enum_row_can_be_styled_on_the_recording_tape(self):
        from beyond_ui.layout_recording import Tape
        tape = Tape()
        row = tape.root.beyond_segments(None, "mode")
        style(row, scope="group", enum_style="track")
        self.assertEqual(tape.commands[-1][1], tape.commands[0][-1])
        self.assertIsNotNone(tape.commands[0][-1])

    def test_boolean_segments_select_explicit_values_and_commit_once(self):
        from beyond_ui.bindings import Binding
        from unittest.mock import patch
        state = {"enabled": False}
        commits = []
        binding = Binding(lambda: state["enabled"],
                          lambda value: state.update(enabled=value),
                          commit=lambda old, new: commits.append((old, new)))
        ui = Layout()
        with patch.object(Layout, "_binding", return_value=binding):
            row = ui.beyond_bool_segments(None, "enabled")
        on, off = row.group.children
        for button in (on, on, off, off):
            button.action()
            self.assertTrue(button.options["selected"]())
        self.assertEqual(commits, [(False, True), (True, False)])

    def test_duotone_uses_theme_or_consumer_roles_and_retains_opacity(self):
        ink=(1,1,1,.4);native={'accent':(.5,.2,.8,1),'toggle_on':(.3,.5,.8,.7)}
        self.assertEqual(layer_color(native,'accent',ink),(.5,.2,.8,.4))
        self.assertEqual(layer_color(native,'accent_2',ink),(.3,.5,.8,.4))
        self.assertEqual(layer_color(dict(native,accent_2=(.2,.9,.5,1)),'accent_2',ink),(.2,.9,.5,.4))
