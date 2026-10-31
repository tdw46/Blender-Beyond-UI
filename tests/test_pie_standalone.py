import unittest
from types import SimpleNamespace as NS
from beyond_ui import Layout
from beyond_ui.context_menu import Entry, Target
from beyond_ui.context_edit import Field
from beyond_ui.pie_menu import PieMenu
from beyond_ui.pie_layout import Compound


class StandalonePieTests(unittest.TestCase):
    def test_hover_freezes_whole_compound_including_padding_and_leaving_restarts(self):
        now = [0.0]
        menu = PieMenu(
            Target("test"),
            [
                Entry(
                    "slot",
                    "",
                    compound=Compound(
                        "column",
                        [
                            Entry("a", "Action"),
                            Entry("b", "Toggle", toggle=True),
                        ],
                    ),
                )
            ],
            (600, 450),
            (0, 0, 1200, 900),
            clock=lambda: now[0],
        )
        x, y, w, h = menu.rectangles[0]
        geometry = dict(menu.row_rectangles)
        menu.update_pointer(x + w + 1, y + h / 2)
        now[0] = 1
        self.assertNotEqual(menu.pull(0), (0, 0))
        menu.motion.pulse(("row", 0), 0.8)
        menu.update_pointer(x + 1, y + 1)  # Padding, not an interactive leaf.
        self.assertEqual(menu.pull(0), (0, 0))
        self.assertEqual(menu.proximity[0], 1)
        self.assertFalse(menu.row_motion_enabled(menu.page, 0))
        self.assertNotIn(("row", 0), menu.motion.tracks)
        self.assertFalse(menu.motion.positions)
        for elapsed in (1.01, 1.2, 2):
            now[0] = elapsed
            menu.update_pointer(x + w * 0.75, y + h * 0.7)
            self.assertEqual(menu.pull(0), (0, 0))
        menu.motion.advance()
        self.assertFalse(menu.motion.advance())
        menu.update_pointer(x + w + 1, y + h / 2)
        self.assertEqual(menu.pull(0), (0, 0))  # Resume from rest, no stale spring.
        now[0] += 1
        self.assertNotEqual(menu.pull(0), (0, 0))
        self.assertEqual(menu.row_rectangles, geometry)

    def test_standalone_opens_reopens_cancels_and_revalidates_scope_and_owner(self):
        context = NS()
        ui = Layout(context=context)
        pie = ui.menu_pie()
        calls = []
        pie._add(Entry("apply", "Apply", lambda t, c: calls.append(1)))
        menu = pie.open(anchor=(600, 450), clip=(0, 0, 1200, 900))
        self.assertIs(menu, ui.canvas.context_menu)
        menu.choose(0, context)
        self.assertEqual(calls, [1])
        again = pie.open(anchor=(600, 450), clip=(0, 0, 1200, 900))
        self.assertIsNot(menu, again)
        ui.enabled = False
        self.assertFalse(again.refresh(context))
        with self.assertRaises(ReferenceError):
            pie.open(anchor=(600, 450), clip=(0, 0, 1200, 900))
        ui.enabled = True
        with self.assertRaises(ReferenceError):
            pie.open(anchor=(600, 450), clip=(0, 0, 1200, 900), context=NS(mode="EDIT"))
        with self.assertRaises(ValueError):
            Layout().menu_pie()
        ui.canvas.cancel()
        self.assertFalse(ui.canvas.advance_animations())

    def test_compound_flags_inherit_and_init_edits_never_execute_default(self):
        ui = Layout(context=NS())
        ui.alert = True
        pie = ui.menu_pie()
        col = pie.column()
        col.emboss = "NONE"
        col.active_default = True
        col._add(Entry("apply", "Apply", lambda t, c: self.fail("Executed on open")))
        col.activate_init = True
        col._add(
            Entry(
                "value", "Value", field=Field(lambda t, c: "hello", lambda *args: None)
            )
        )
        menu = pie.open(anchor=(600, 450), clip=(0, 0, 1200, 900))
        self.assertEqual(menu.editor.text.text, "hello")
        self.assertEqual(menu.page.highlight, 1)
        self.assertTrue(all(r.alert and r.emboss == "NONE" for r in menu.page.rows))
        self.assertTrue(menu.page.rows[0].active_default)
        self.assertFalse(menu.page.rows[1].active_default)
        with self.assertRaises(ValueError):
            col.emboss = "invalid"
        ui.canvas.cancel()
