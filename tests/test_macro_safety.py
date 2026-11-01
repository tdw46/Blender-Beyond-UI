import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from beyond_ui.macro_safety import protected_operators


class MacroSafetyTests(unittest.TestCase):
    def fixture(self, *, broken=False):
        class Macro:
            pass

        class Step:
            bl_idname = "owned.step"
            bl_rna = NS(identifier="OWNED_OT_step")

        class ForeignMacro(Macro):
            __module__ = "another_addon"
            bl_idname = "foreign.group"
            bl_rna = NS(identifier="FOREIGN_OT_group")

        class UnregisteredChild(ForeignMacro):
            bl_idname = "foreign.unregistered"

        def metadata():
            if broken:
                raise RuntimeError("RNA unavailable")
            return NS(properties=[NS(identifier="OWNED_OT_step", type="POINTER")])

        bpy = NS(
            types=NS(Macro=Macro),
            ops=NS(foreign=NS(group=NS(get_rna_type=metadata))),
        )
        return bpy, Step, (ForeignMacro, UnregisteredChild)

    def test_foreign_macro_without_is_registered_protects_owned_child(self):
        bpy, step, retained = self.fixture()
        with patch.dict("sys.modules", bpy=bpy):
            protected, references = protected_operators([step])
        self.assertEqual(protected, {step})
        self.assertEqual(
            references, [{"macro": "foreign.group", "operator": "owned.step"}]
        )

    def test_failed_metadata_audit_preserves_types_instead_of_guessing(self):
        bpy, step, retained = self.fixture(broken=True)
        with patch.dict("sys.modules", bpy=bpy):
            protected, references = protected_operators([step])
        self.assertEqual(protected, {step})
        self.assertTrue(references[0]["audit_failed"])

    def test_macro_capability_absence_keeps_normal_routing(self):
        with patch.dict("sys.modules", bpy=NS(types=NS())):
            self.assertEqual(protected_operators([]), (set(), []))
