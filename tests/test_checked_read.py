import unittest
from dataclasses import replace
from types import SimpleNamespace as NS
from beyond_ui.bindings import rna_binding


class CheckedRead(unittest.TestCase):
    def setUp(self):
        self.count = 0
        self.owner = NS(id_data=None, as_pointer=lambda: 123, value=3,
                        bl_rna=NS(properties={'value': NS(is_array=False, is_readonly=False)}))
        def resolve():
            self.count += 1
            return self.owner
        self.binding = rna_binding(resolve, 'value')
        self.count = 0

    def test_read_resolves_once_and_reads_current_value_each_time(self):
        self.assertEqual(self.binding.read(), 3)
        self.assertEqual(self.count, 1)
        self.owner.value = 8
        self.assertEqual(self.binding.read(), 8)
        self.assertEqual(self.count, 2)

    def test_stale_owner_fails_and_readonly_still_displays_without_writes(self):
        self.owner.as_pointer = lambda: 456
        with self.assertRaises(ReferenceError): self.binding.read()
        self.owner.as_pointer = lambda: 123
        self.owner.bl_rna.properties['value'].is_readonly = True
        self.assertEqual(self.binding.read(), 3)
        self.assertFalse(self.binding.valid())
        with self.assertRaises(ReferenceError): self.binding.write(7)
        self.assertEqual(self.owner.value, 3)
        self.owner.bl_rna.properties.clear()
        with self.assertRaises(ReferenceError): self.binding.read()

    def test_binding_overrides_cannot_bypass_custom_valid_or_get(self):
        with self.assertRaises(ReferenceError):
            replace(self.binding, valid=lambda: False).read()
        self.assertEqual(replace(self.binding, get=lambda: 42).read(), 42)

    def test_arrays_are_copied_not_retained(self):
        self.owner.value = [1, 2, 3]
        self.owner.bl_rna.properties['value'].is_array = True
        result = self.binding.read()
        self.owner.value[0] = 4
        self.assertEqual(result, (1, 2, 3))
