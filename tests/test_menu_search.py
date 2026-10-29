"""Search changes presentation only; original actions, owners and bounds survive."""

import unittest
from types import SimpleNamespace as NS
from beyond_ui.context_menu import Menu, Entry, Target, inside
from beyond_ui import Canvas
from beyond_ui.bindings import Binding


def event(kind="A", text="", **kw):
    return NS(type=kind, value=kw.pop("value", "PRESS"), unicode=text, **kw)


class SearchMenus(unittest.TestCase):
    def menu(self, rows=None, **kw):
        self.chosen = []
        rows = rows or tuple(
            Entry(str(i), f"Choice {i:03}", lambda t, c, i=i: self.chosen.append(i))
            for i in range(200)
        )
        return Menu(
            Target("owner"), rows, (10, 10), (0, 0, 560, 520), row_limit=4096, **kw
        )

    def type(self, menu, value):
        for c in value:
            self.assertTrue(menu.event(event(text=c), 20, 20))

    def test_filter_retargets_motion_and_shrinks_without_moving_search(self):
        m = self.menu()
        m.motion.clock = lambda: 0.0
        m.motion.pulse("reveal", 0.12)
        m.motion.pulse(("row", 0), 0.12)
        rect = m.page.rect
        search = m.search_rect()
        self.type(m, "199")
        self.assertIn("reveal", m.motion.tracks)
        self.assertIn("search", m.motion.tracks)
        self.assertNotIn(("row", 0), m.motion.tracks)
        self.assertEqual(m.search_rect(), search)
        self.assertLess(m.page.rect[3], rect[3])
        m.event(event("ESC"), 20, 20)
        self.assertEqual(m.page.rect, rect)
        m.motion.settings.enabled = False
        self.type(m, "199")
        self.assertFalse(m.motion.advance())

    def test_unfocused_command_shortcuts_remain_available(self):
        from beyond_ui.context_menu import Shortcut

        rows = (
            Entry(
                "copy",
                "Copy",
                lambda t, c: self.chosen.append("copy"),
                bindings=(Shortcut("C", ctrl=True),),
            ),
            *(Entry(str(i), f"Action {i}") for i in range(15)),
        )
        m = self.menu(rows)
        m.event(event("C", ctrl=True), 20, 20, NS(window_manager=NS(clipboard="keep")))
        self.assertEqual(self.chosen, ["copy"])

    def test_unfocused_delete_and_paste_shortcuts_keep_their_actions(self):
        from beyond_ui.context_menu import Shortcut

        for kind, mods in [("DEL", {}), ("V", {"ctrl": True})]:
            rows = (
                Entry(
                    "action",
                    "Action",
                    lambda t, c: self.chosen.append("ran"),
                    bindings=(Shortcut(kind, **mods),),
                ),
                *(Entry(str(i), f"Other {i}") for i in range(15)),
            )
            m = self.menu(rows)
            m.event(
                event(kind, **mods), 20, 20, NS(window_manager=NS(clipboard="query"))
            )
            self.assertEqual(self.chosen, ["ran"])

    def test_type_selects_original_action(self):
        m = self.menu()
        self.type(m, "CHOICE 199")
        self.assertEqual([r.key for r in m.page.rows], ["199"])
        self.assertEqual(self.chosen, [])
        m.event(event("RET"), 20, 20)
        self.assertEqual(self.chosen, [199])
        self.assertTrue(m.closed)
        self.assertIsNone(m.page.search)

    def test_group_names_and_nonselectable_headers(self):
        rows = (
            Entry("head1", "Main", heading=True, enabled=False),
            Entry("a", "Alpha", lambda t, c: None),
            Entry("head2", "Extras", heading=True, enabled=False),
            Entry("b", "Beta", lambda t, c: None, divider=True),
        )
        m = self.menu(rows, search_threshold=1)
        self.type(m, "extras")
        self.assertEqual([r.key for r in m.page.rows], ["head2", "b"])
        self.assertEqual(m.page.highlight, 1)
        m.event(event("HOME"), 20, 20)  # text caret, not a result
        m.event(event("UP_ARROW"), 20, 20)
        self.assertEqual(m.page.highlight, 1)

    def test_empty_results_escape_then_dismiss(self):
        m = self.menu()
        self.type(m, "unfindable")
        self.assertEqual(m.page.rows[0].label, "No matches")
        m.event(event("RET"), 20, 20)
        self.assertFalse(m.closed)
        m.event(event("ESC"), 20, 20)
        self.assertEqual(len(m.page.rows), 200)
        self.assertFalse(m.closed)
        m.event(event("ESC"), 20, 20)
        self.assertTrue(m.closed)

    def test_clipboard_selection_clear_and_mouse(self):
        m = self.menu()
        ctx = NS(window_manager=NS(clipboard="Choice 198"))
        m.event(event("V", ctrl=True), 20, 20, ctx)
        self.assertEqual(m.page.rows[0].key, "198")
        m.event(event("A", oskey=True), 20, 20, ctx)
        m.event(event("X", oskey=True), 20, 20, ctx)
        self.assertEqual(ctx.window_manager.clipboard, "Choice 198")
        self.assertEqual(len(m.page.rows), 200)
        self.type(m, "199")
        x, y, w, h = m.search_rect()
        m.event(event("LEFTMOUSE"), x + w - 5, y + h / 2, ctx)
        self.assertEqual(m.page.search.text.text, "")
        self.assertEqual(len(m.page.rows), 200)

    def test_query_bound_and_right_click_cancellation(self):
        m = self.menu()
        m.event(
            event("V", ctrl=True), 20, 20, NS(window_manager=NS(clipboard="x" * 9000))
        )
        self.assertEqual(len(m.page.search.text.text), 4096)
        self.assertTrue(m.event(event("RIGHTMOUSE"), 20, 20))
        self.assertFalse(m.closed)
        self.assertEqual(len(m.page.rows), 200)
        self.type(m, "19")
        self.assertFalse(m.event(event("RIGHTMOUSE"), -20, -20))
        self.assertTrue(m.closed)

    def test_nested_search_retained_on_back_and_no_eager_children(self):
        calls = []
        children = lambda t, c: calls.append(True) or tuple(
            Entry(str(i), f"Nested {i}") for i in range(30)
        )
        rows = (Entry("branch", "Group", children=children), Entry("x", "Extra"))
        m = self.menu(rows, search_threshold=1)
        self.type(m, "Group")
        self.assertEqual(calls, [])
        m.event(event("RET"), 20, 20)
        self.assertEqual(calls, [True])
        self.type(m, "29")
        self.assertEqual([r.key for r in m.page.rows], ["__back__", "29"])
        m.event(event("ESC"), 20, 20)  # clear query first
        m.event(event("ESC"), 20, 20)  # return to filtered parent
        self.assertEqual(m.page.search.text.text, "Group")
        self.assertEqual(m.page.rows[0].key, "branch")

    def test_disabled_and_stale_owner_do_not_execute(self):
        m = self.menu(
            (Entry("x", "Locked", lambda t, c: self.chosen.append(1), enabled=False),),
            search_threshold=1,
        )
        self.type(m, "Locked")
        m.event(event("RET"), 20, 20)
        self.assertEqual(self.chosen, [])
        m = self.menu()
        self.type(m, "199")
        m.target = Target("gone", valid=lambda: False)
        m.event(event("RET"), 20, 20)
        self.assertEqual(self.chosen, [])
        self.assertTrue(m.closed)

    def test_short_menus_unchanged_and_pinned_search(self):
        m = self.menu(tuple(Entry(str(i), str(i)) for i in range(11)))
        self.assertIsNone(m.page.search)
        m = self.menu()
        initial = m.search_rect()
        m.event(event("END"), 20, 20)
        self.assertEqual(m.page.highlight, 199)
        self.assertEqual(m.search_rect(), initial)
        self.assertLessEqual(len(list(m.visible_rows())), 18)
        for _, r, _ in m.visible_rows():
            self.assertGreaterEqual(r[1], initial[1] + initial[3])
            self.assertTrue(inside(m.page.rect, r[0], r[1]))

    def test_enum_filter_preserves_flag_transaction_and_stale_snapshot(self):
        from beyond_ui.enum_field import EnumField, Item

        value = [{"I1"}]
        commits = []
        binding = Binding(
            lambda: value[0],
            lambda v: value.__setitem__(0, v),
            commit=lambda a, b: commits.append((a, b)),
        )
        field = EnumField(
            binding,
            lambda: tuple(
                Item(f"I{i}", f"Option {i:03}", value=1 << i) for i in range(20)
            ),
            flag=True,
        )
        c = Canvas()
        control = c.add("enum", "flags", binding=binding, enum_field=field)
        c.arrange(560)
        self.assertTrue(c.open_enum_menu(control, (0, 0, 560, 520), None))
        m = c.context_menu
        self.type(m, "019")
        m.event(event("RET"), 20, 20)
        self.assertEqual(value[0], {"I1", "I19"})
        self.assertEqual(len(commits), 1)
        c.open_enum_menu(control, (0, 0, 560, 520), None)
        m = c.context_menu
        self.type(m, "018")
        value[0] = {"I2"}
        m.event(event("RET"), 20, 20)
        self.assertEqual(value[0], {"I2"})
        self.assertEqual(len(commits), 1)


if __name__ == "__main__":
    unittest.main()
