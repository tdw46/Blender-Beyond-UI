import unittest
from types import SimpleNamespace as NS
from beyond_ui.editing import Text
from beyond_ui.widgets.picker import DataPicker


class SearchInput(unittest.TestCase):
    def test_rejected_selection_keeps_pending_edit_for_correction(self):
        picker = DataPicker([(1, "Candidate", "object")], lambda key: False)
        picker.text_edit = Text("Candidate")
        picker.capturing = True
        self.assertFalse(picker._accept())
        self.assertTrue(picker.capturing)
        self.assertEqual(picker.text_edit.text, "Candidate")

    def test_right_click_cancels_search_without_selecting_a_result(self):
        selected = []
        picker = DataPicker([(1, "Candidate", "object")], selected.append)
        picker.text_edit = Text("Candidate")
        picker.capturing = True
        self.assertTrue(picker.event(NS(type="RIGHTMOUSE", value="PRESS"), 50, 100))
        self.assertFalse(picker.capturing)
        self.assertIsNone(picker.text_edit)
        self.assertEqual(selected, [])

    def test_suggestions_require_explicit_opt_in_and_honor_navigation(self):
        selected, typed = [], []
        picker = DataPicker([(1, "Candidate", "object")], selected.append)
        picker.text_edit = Text("Other")
        picker.query = "Other"
        picker._filter()
        self.assertFalse(picker._accept())
        self.assertEqual(selected, [])
        picker.accept_text = typed.append
        self.assertTrue(picker._accept())
        self.assertEqual(typed, ["Other"])
        picker.query = ""
        picker._filter()
        picker.text_edit = Text("")
        picker._navigate("HOME")
        self.assertTrue(picker._accept())
        self.assertEqual(selected, [1])
        self.assertEqual(typed, ["Other"])

    def test_popup_type_to_search_waits_for_real_text_input(self):
        picker = DataPicker([(1, "Zebra", "object")], lambda key: None)
        picker.focus()
        picker.type_to_search = True
        self.assertFalse(picker.capturing)
        picker.event(NS(type="Z", value="PRESS", unicode="z"), 0, 0)
        self.assertEqual(picker.query, "z")
        self.assertTrue(picker.capturing)
        picker.cancel()
        self.assertFalse(picker.capturing)

    def test_full_card_setting_inherits_to_nested_layouts(self):
        from beyond_ui import Layout

        ui = Layout()
        self.assertTrue(ui.row().search_popovers)
        ui.search_popovers = False
        self.assertFalse(ui.column().row().search_popovers)
