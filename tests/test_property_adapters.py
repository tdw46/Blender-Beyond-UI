import unittest
from types import SimpleNamespace as NS
from beyond_ui import Canvas, Layout
from beyond_ui.bindings import Binding
from beyond_ui.decorator import channel_collections


class PropertyAdapters(unittest.TestCase):
    def test_legacy_action_collections_need_no_slot_or_layer_api(self):
        curves = [NS(data_path="location", array_index=0)]
        drivers = []
        data = NS(animation_data=NS(action=NS(fcurves=curves), drivers=drivers))
        collections, found_drivers = channel_collections(data)
        self.assertEqual(collections, (curves,))
        self.assertIs(found_drivers, drivers)
        self.assertEqual(channel_collections(NS(animation_data=None)), ((), None))

    def test_layered_action_reads_only_selected_slot_without_creating_channelbags(self):
        slot = object()
        calls = []
        curves = []

        def bag(value, ensure):
            calls.append((value, ensure))
            return NS(fcurves=curves)

        action = NS(is_action_layered=True, layers=[NS(strips=[NS(channelbag=bag)])])
        data = NS(animation_data=NS(action=action, action_slot=slot, drivers=[]))
        self.assertEqual(channel_collections(data)[0], (curves,))
        self.assertEqual(calls, [(slot, False)])
        data.animation_data.action_slot = None
        self.assertEqual(channel_collections(data)[0], ())

    def test_compact_decorator_slots_preserve_flexible_fields_and_small_widths(self):
        canvas = Canvas()
        row = canvas.row()
        n = row.number("n", "Number", Binding(lambda: 1, lambda v: None))
        d = row.add("decorator", "d", decorator=None, width=32, enabled=False)
        canvas.arrange(560)
        self.assertEqual(d.rect[2], 32)
        self.assertGreater(n.rect[2], 450)
        self.assertEqual(n.motion.strength, 0.15)
        canvas.arrange(25)
        self.assertGreaterEqual(n.rect[2], 0)
        self.assertLessEqual(d.rect[2], 9)
        self.assertFalse(d.enabled)
        standalone = canvas.add("decorator", "standalone", decorator=None, width=32)
        canvas.arrange(560)
        self.assertEqual(standalone.rect[2], 32)

    def test_pointer_policy_inherits_through_nested_layouts(self):
        policy = lambda owner, name: None
        ui = Layout(pointer_sources=policy)
        self.assertIs(ui.row().column().pointer_sources, policy)

    def test_popover_keeps_owner_animation_policy_across_input(self):
        from beyond_ui.widgets.picker import DataPicker

        canvas = Canvas()
        owner = canvas.add("pointer", "pointer")
        widget = DataPicker([], lambda value: None)
        canvas.overlay = dict(widget=widget, owner=owner, rect=(0, 0, 320, 240))
        event = NS(type="MOUSEMOVE", value="NOTHING")
        owner.motion.settings.strength = 0.3
        canvas._motion_input(event, 10, 10, (0, 0, 320, 240))
        self.assertEqual(widget.motion.strength, 0.3)
        widget.motion.pulse("reveal")
        self.assertTrue(widget.motion.tracks)
        canvas._motion_input(event, 10, 10, (0, 0, 320, 240))
        self.assertTrue(widget.motion.tracks)
        owner.motion.settings.enabled = False
        canvas._motion_input(event, 10, 10, (0, 0, 320, 240))
        self.assertEqual(widget.motion.strength, 0)
        self.assertFalse(widget.motion.tracks)
