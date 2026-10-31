"""Lazy identity migration is read-only at discovery, finite and transactional."""

import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from beyond_ui.list_identity import StableListIDs, KEY
from beyond_ui.list_source import UnsafeListIdentity


class Row(dict):
    __module__ = "consumer.props"


class ListIdentities(unittest.TestCase):
    def setUp(self):
        self.timers = NS(
            is_registered=Mock(return_value=False), register=Mock(), unregister=Mock()
        )
        self.patch = patch.dict(sys.modules, bpy=NS(app=NS(timers=self.timers)))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.changed = Mock()
        self.ids = StableListIDs("consumer", self.changed)
        self.owner = NS(rows=[Row(), Row()], as_pointer=lambda: 42, id_data=None)

    def test_discovery_is_readonly_and_completion_is_finite(self):
        with self.assertRaises(UnsafeListIdentity):
            self.ids.prepare(self.owner, "rows")
        self.assertTrue(all(not row for row in self.owner.rows))
        self.assertIsNone(self.ids.flush())
        tokens = [row[KEY] for row in self.owner.rows]
        self.assertEqual(len(set(tokens)), 2)
        self.changed.assert_called_once()
        self.ids.prepare(self.owner, "rows")
        self.assertFalse(self.ids.pending)
        self.assertEqual(tokens, [row[KEY] for row in self.owner.rows])

    def test_duplicates_revoke_every_ambiguous_token(self):
        for row in self.owner.rows:
            row[KEY] = "duplicated"
        with self.assertRaises(UnsafeListIdentity):
            self.ids.prepare(self.owner, "rows")
        self.ids.flush()
        self.assertTrue(all(row[KEY] != "duplicated" for row in self.owner.rows))
        self.assertNotEqual(*[row[KEY] for row in self.owner.rows])

    def test_read_only_and_foreign_owners_fail_closed(self):
        self.owner.id_data = NS(
            as_pointer=lambda: 5, is_editable=False, library=object()
        )
        with self.assertRaises(UnsafeListIdentity):
            self.ids.prepare(self.owner, "rows")
        self.ids.flush()
        self.assertTrue(self.ids.errors)
        self.assertTrue(all(not row for row in self.owner.rows))
        self.owner.rows = [{}]
        with self.assertRaises(UnsafeListIdentity):
            self.ids.prepare(self.owner, "rows")

    def test_close_cancels_scheduled_work(self):
        with self.assertRaises(UnsafeListIdentity):
            self.ids.prepare(self.owner, "rows")
        self.timers.is_registered.return_value = True
        self.ids.close()
        self.timers.unregister.assert_called_once_with(self.ids.callback)
        self.assertFalse(self.ids.pending)
        self.ids.flush()
        self.assertTrue(all(not row for row in self.owner.rows))

    def test_keyword_template_signature_does_not_walk_collection(self):
        from beyond_ui.layout_recording import Tape

        class Values:
            def __len__(self):
                return 100000

            def __iter__(self):
                raise AssertionError("Steady authoring scanned collection")

            def __getitem__(self, index):
                assert index == 8
                return Row({KEY: "active"})

        owner = NS(rows=Values(), active=8)
        tape = Tape()
        tape.root.template_list(
            "TEST_UL_rows",
            "",
            dataptr=owner,
            propname="rows",
            active_dataptr=owner,
            active_propname="active",
        )
        self.assertEqual(tape.signature[-1], (100000, 8, "active"))
