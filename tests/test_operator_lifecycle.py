import unittest
from beyond_ui.operator_lifecycle import modal_registration_policy

class ModalPolicy(unittest.TestCase):
    def test_foreign_modal_descendant_protects_owned_nonmodal_base(self):
        class Base:
            is_registered = True
        class Foreign(Base):
            def modal(self, context, event): pass
        self.assertEqual(modal_registration_policy((Base,)), (set(), {Base}))

    def test_modal_inheritance_uses_in_place_and_unrelated_can_register(self):
        class Modal:
            is_registered = True
            def modal(self, context, event): pass
        class Child(Modal): pass
        class Ordinary:
            is_registered = True
        self.assertEqual(modal_registration_policy((Modal, Child, Ordinary)), ({Modal, Child}, set()))

    def test_unregistered_descendant_does_not_block_base(self):
        class Base:
            is_registered = True
        class Future(Base):
            is_registered = False
            def modal(self, context, event): pass
        self.assertEqual(modal_registration_policy((Base,)), (set(), set()))
