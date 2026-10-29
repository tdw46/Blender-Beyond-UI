"""Public collection-wrapper identity and readonly compatibility branches."""

import unittest
from types import SimpleNamespace as NS
from beyond_ui.rna_owner import identity, readonly
from beyond_ui.bindings import rna_binding


class OwnerIdentity(unittest.TestCase):
    def collection(self):
        data = NS(as_pointer=lambda: 10)
        owner = NS(
            id_data=data,
            path_from_id=lambda: "nodes",
            active=None,
            bl_rna=NS(identifier="Nodes", properties={"active": NS(is_readonly=False)}),
        )
        data.path_resolve = lambda path: owner
        return owner

    def test_collection_reacquisition_uses_id_path_and_rna_type(self):
        owner = self.collection()
        self.assertEqual(identity(owner), (10, "nodes", "Nodes"))
        wrapper = NS(**vars(owner))
        self.assertEqual(identity(wrapper), identity(owner))
        owner.id_data.path_resolve = lambda path: NS(bl_rna=NS(identifier="Other"))
        with self.assertRaises(ReferenceError):
            identity(wrapper)

    def test_collection_binding_rejects_another_id_at_same_path(self):
        owner = self.collection()
        current = [owner]
        binding = rna_binding(lambda: current[0], "active")
        binding.write("value")
        self.assertEqual(binding.read(), "value")
        replacement = self.collection()
        replacement.id_data.as_pointer = lambda: 11
        current[0] = replacement
        self.assertFalse(binding.valid())
        with self.assertRaises(ReferenceError):
            binding.write("wrong owner")

    def test_readonly_metadata_fallback_and_live_struct_query(self):
        owner = self.collection()
        self.assertFalse(readonly(owner, "active"))
        owner.bl_rna.properties["active"].is_readonly = True
        self.assertTrue(readonly(owner, "active"))
        owner.is_property_readonly = lambda name: False
        self.assertFalse(readonly(owner, "active"))

    def test_deleted_collection_path_invalidates_binding(self):
        owner = self.collection()
        binding = rna_binding(lambda: owner, "active")

        def deleted(path):
            raise ValueError("Path no longer exists")

        owner.id_data.path_resolve = deleted
        self.assertFalse(binding.valid())
        self.assertFalse(binding.context.valid())

    def test_struct_identity_includes_owning_data(self):
        owner = NS(as_pointer=lambda: 20, id_data=NS(as_pointer=lambda: 10))
        self.assertEqual(identity(owner), (10, 20))
        owner.id_data.as_pointer = lambda: 11
        self.assertEqual(identity(owner), (11, 20))
