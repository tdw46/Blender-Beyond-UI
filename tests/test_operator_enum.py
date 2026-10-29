"""Operator choice safety without bpy or GPU imports."""

import unittest
from contextlib import nullcontext
from types import SimpleNamespace as NS
from unittest.mock import patch
from beyond_ui.operator_enum import OperatorEnum, context_key


class OperatorChoices(unittest.TestCase):
    def setUp(self):
        self.pointer = [42]
        self.poll = [True]
        self.calls = []
        self.rows = [
            NS(identifier="A", name="Alpha", description="First", value=1),
            NS(identifier="B", name="Beta", description="Second", value=2),
        ]
        self.meta = NS(type="ENUM", is_enum_flag=False)
        info = NS(
            as_pointer=lambda: self.pointer[0],
            properties={"choice": self.meta},
            name="Test",
            description="Test action",
        )

        class Op:
            get_rna_type = lambda _: info
            poll = lambda _: self.poll[0]

            def __call__(_, invocation, **properties):
                self.calls.append((invocation, properties))
                return {"FINISHED"}

        self.op = Op()
        self.context = NS(scene=NS(as_pointer=lambda: 8), mode="OBJECT")
        self.addCleanup(patch.stopall)
        patch("beyond_ui.operator_enum.operator", return_value=self.op).start()
        patch(
            "beyond_ui.operator_enum.override", side_effect=lambda *_: nullcontext()
        ).start()
        self.items = patch(
            "beyond_ui.operator_enum.operator_items",
            side_effect=lambda *a, **k: self.rows,
        ).start()
        self.model = OperatorEnum(
            "test.choice", "choice", self.context, "EXEC_DEFAULT", {}, lambda x: x
        )

    def test_prepare_does_not_execute_and_selection_uses_exact_arguments(self):
        self.model.properties.amount = 3
        rows, valid = self.model.rows(self.context)
        self.assertTrue(valid())
        self.assertFalse(self.calls)
        rows[1].action(None, self.context)
        self.assertEqual(self.calls, [("EXEC_DEFAULT", {"amount": 3, "choice": "B"})])

    def test_pending_argument_edit_rejects_old_menu(self):
        self.model.properties.amount = 2
        rows, valid = self.model.rows(self.context)
        self.model.properties.amount = 4
        self.assertFalse(valid())
        with self.assertRaises(ReferenceError):
            rows[0].action(None, self.context)
        self.assertFalse(self.calls)

    def test_reregistration_and_poll_revoke_actions(self):
        rows, valid = self.model.rows(self.context)
        self.poll[0] = False
        self.assertFalse(valid())
        with self.assertRaises(ReferenceError):
            rows[0].action(None, self.context)
        self.poll[0] = True
        self.pointer[0] += 1
        with self.assertRaises(ReferenceError):
            rows[0].action(None, self.context)
        self.assertFalse(self.calls)

    def test_choice_numeric_remap_and_removal_reject_stale_button(self):
        item = self.model.snapshot()[0]
        self.rows[0].value = 99
        with self.assertRaises(ReferenceError):
            self.model.execute(item, self.context)
        self.rows.pop(0)
        with self.assertRaises(ReferenceError):
            self.model.execute(item, self.context)
        self.assertFalse(self.calls)

    def test_context_change_and_callback_side_effect_reject(self):
        rows, valid = self.model.rows(self.context)
        self.context.mode = "EDIT_MESH"
        self.assertFalse(valid())
        with self.assertRaises(ReferenceError):
            rows[0].action(None, self.context)
        self.context.mode = "OBJECT"
        item = self.model.snapshot()[0]

        def mutate(*a, **kw):
            self.context.mode = "EDIT_MESH"
            return self.rows

        self.items.side_effect = mutate
        with self.assertRaises(ReferenceError):
            self.model.execute(item, self.context)
        self.assertFalse(self.calls)

    def test_selection_change_with_same_active_owner_rejects(self):
        self.context.selected_objects = [NS(as_pointer=lambda: 100)]
        rows, _ = self.model.rows(self.context)
        self.context.selected_objects = [NS(as_pointer=lambda: 101)]
        with self.assertRaisesRegex(ReferenceError, "selection changed"):
            rows[0].action(None, self.context)
        self.assertFalse(self.calls)

    def test_flags_pass_a_set_and_group_rows_are_not_actions(self):
        self.model.flag = True
        self.rows.insert(0, NS(identifier="", name="Group", description="", value=0))
        rows, _ = self.model.rows(self.context)
        self.assertTrue(rows[0].heading)
        self.assertIsNone(rows[0].action)
        rows[1].action(None, self.context)
        self.assertEqual(self.calls[-1][1]["choice"], {"A"})

    def test_duplicates_and_bounds_fail_explicitly(self):
        self.rows.append(self.rows[0])
        with self.assertRaises(ValueError):
            self.model.snapshot()
        self.rows = self.rows * 1400
        with self.assertRaisesRegex(ValueError, "4096"):
            self.model.snapshot()

    def test_validation_does_not_rescan_choices(self):
        _, valid = self.model.rows(self.context)
        calls = self.items.call_count
        for _ in range(25):
            self.assertTrue(valid())
        self.assertEqual(calls, self.items.call_count)
