import unittest
from types import SimpleNamespace as NS
from beyond_ui.presentation import property_options
from beyond_ui.numeric import Numeric


class PresentationHints(unittest.TestCase):
    def test_class_and_qualified_panel_override(self):
        class Owner:
            beyond_ui_props = {'lens': {'precision': 1, 'suffix': 'mm'}}
            bl_rna = NS(identifier='CameraSettings')
        data = Owner()
        hints = property_options(data, 'lens', {'CameraSettings.lens': {'value_width': 78}})
        self.assertEqual(hints, {'precision': 1, 'suffix': 'mm', 'value_width': 78})
        hints['precision'] = 6
        self.assertEqual(data.beyond_ui_props['lens']['precision'], 1)
        self.assertEqual(property_options(data, 'other'), {})

    def test_invalid_hints_fail_before_authoring(self):
        for hints in ({'precision': 1.5}, {'suffix': '\n'}, {'value_width': float('nan')},
                      {'disabled_accent': 1}, {'typo': True}, {'width': -1}):
            with self.assertRaises(ValueError):
                property_options(object(), 'value', {'value': hints})

    def test_fixed_decimal_suffix_preserves_value_and_input(self):
        meta = NS(type='FLOAT', unit='NONE', subtype='NONE', precision=3,
                  soft_min=0, soft_max=500, step=3)
        n = Numeric(meta, presentation={'precision': 1, 'suffix': 'mm'})
        original = 210.351234
        self.assertEqual(n.format(original), '210.4 (mm)')
        self.assertEqual(n.parse(n.format(original), original), original)
        self.assertEqual(n.parse('155.2 (mm)', original), 155.2)
        self.assertEqual(n.parse('150 + 5', original), 155)
        meta.unit = 'LENGTH'
        with self.assertRaises(ValueError):
            Numeric(meta, presentation={'suffix': 'mm'})

    def test_precision_preserves_percentage_scale(self):
        meta = NS(type='FLOAT', unit='NONE', subtype='FACTOR', precision=3,
                  soft_min=0, soft_max=1, step=3)
        n = Numeric(meta, presentation={'precision': 1})
        state = ('NONE', 1, 'DEGREES', 'ADAPTIVE', False, 'PERCENTAGE')
        self.assertEqual(n.format(.375, state), '37.5%')
        self.assertEqual(n.parse('42.5%', .375, state), .425)
        with self.assertRaises(ValueError):
            Numeric(meta, presentation={'suffix': 'mm'})
