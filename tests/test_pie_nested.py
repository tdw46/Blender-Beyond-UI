import unittest
from types import SimpleNamespace as NS
from dataclasses import replace
from beyond_ui import Canvas
from beyond_ui.context_menu import Menu, Entry, Target
from beyond_ui.pie_layout import PieRows, Slots, Compound
from beyond_ui.pie_menu import PieMenu
from beyond_ui.registered_menu import MenuLayout, retarget


def event(kind, value="PRESS"):
    return NS(type=kind, value=value)


class NestedPie(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas()
        self.calls = []
        self.reads = []
        self.allowed = True
        self.clock = [0.0]
        self.clip = (0, 0, 1200, 900)

        def children(t, c):
            self.reads.append("draw")
            return PieRows(
                (
                    Entry(
                        "apply",
                        "Apply",
                        lambda t, c: self.calls.append("apply"),
                        context=lambda t, c: (
                            Entry(
                                "copy", "Copy", lambda t, c: self.calls.append("copy")
                            ),
                        ),
                    ),
                )
            )

        self.root = PieMenu(
            Target("owner"),
            (
                Entry(
                    "nested",
                    "Nested",
                    children=children,
                    enabled=lambda t, c: self.allowed,
                ),
            ),
            (600, 450),
            self.clip,
            clock=lambda: self.clock[0],
        )
        self.root.on_navigate = self.canvas._navigate_menu
        self.canvas.context_menu = self.root
        self.root.motion.bind((self.canvas.animation,), self.canvas._wake_motion)

    def point(self, menu, index=0):
        _, (x, y, w, h), _ = next(v for v in menu.visible_rows() if v[0] == index)
        return x + w / 2, y + h / 2

    def emit(self, kind, value="PRESS", point=None):
        menu = self.canvas.context_menu
        return self.canvas.event(
            event(kind, value), *(point or self.point(menu)), self.clip
        )

    def click(self):
        p = self.point(self.canvas.context_menu)
        self.emit("LEFTMOUSE", point=p)
        self.emit("LEFTMOUSE", "RELEASE", p)

    def test_release_opens_new_ring_without_dispatch_and_back_restores_parent(self):
        p = self.point(self.root)
        self.click()
        child = self.canvas.context_menu
        self.assertIsInstance(child, PieMenu)
        self.assertIs(child.navigation_parent, self.root)
        self.assertEqual(child.origin, p)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.reads, ["draw"])
        self.clock[0] = 1
        self.emit("LEFT_ARROW")
        self.assertIs(self.canvas.context_menu, self.root)
        self.assertFalse(self.root.closed)
        self.assertTrue(child.closed)
        self.click()
        self.click()
        self.assertEqual(self.calls, ["apply"])
        self.assertIsNone(self.canvas.context_menu)
        self.assertTrue(self.root.closed)
        self.assertFalse(self.canvas.advance_animations())

    def test_exact_child_context_back_and_global_disable(self):
        self.click()
        child = self.canvas.context_menu
        self.canvas.animation.enabled = False
        self.assertEqual(child.motion.strength, 0)
        self.emit("RIGHTMOUSE")
        self.assertEqual(child.page.rows[1].label, "Copy")
        self.emit("LEFT_ARROW")
        self.assertTrue(child.radial())
        self.emit("ESC")
        self.assertIs(self.canvas.context_menu, self.root)
        self.assertFalse(self.canvas.advance_animations())

    def test_center_back_is_clickable_bounded_and_separate_from_petals(self):
        self.click()
        child = self.canvas.context_menu
        i, (x, y, w, h), _ = next(
            v for v in child.visible_rows() if v[2].key == "__back__"
        )
        self.assertTrue(0 <= x < x + w <= 1200 and 0 <= y < y + h <= 900)
        for a, b, c, d in child.rectangles:
            self.assertTrue(x + w <= a or a + c <= x or y + h <= b or b + d <= y)
        p = (x + w / 2, y + h / 2)
        self.emit("LEFTMOUSE", point=p)
        self.emit("LEFTMOUSE", "RELEASE", p)
        self.assertIs(self.canvas.context_menu, self.root)

    def test_parent_disabled_after_child_press_never_executes(self):
        self.click()
        p = self.point(self.canvas.context_menu)
        self.emit("LEFTMOUSE", point=p)
        self.allowed = False
        self.emit("LEFTMOUSE", "RELEASE", p)
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.canvas.context_menu)

    def test_owner_guard_remains_valid_during_close_before_action_dispatch(self):
        self.click()
        child = self.canvas.context_menu
        child.page.rows = (
            replace(
                child.page.rows[0], action=lambda t, c: self.calls.append(t.valid())
            ),
            *child.page.rows[1:],
        )
        self.click()
        self.assertEqual(self.calls, [True])
        self.assertTrue(self.root.closed)

    def test_list_to_pie_and_child_list_return(self):
        self.root = Menu(Target("owner"), self.root.page.rows, (100, 100), self.clip)
        self.root.on_navigate = self.canvas._navigate_menu
        self.canvas.context_menu = self.root
        self.click()
        self.assertIsInstance(self.canvas.context_menu, PieMenu)
        self.emit("LEFT_ARROW")
        self.assertIs(self.canvas.context_menu, self.root)

    def test_narrow_fallback_context_does_not_access_radial_surface_cache(self):
        menu = PieMenu(
            Target("owner"),
            [
                Entry(str(i), "Action", context=lambda t, c: (Entry("copy", "Copy"),))
                for i in range(8)
            ],
            (0, 0),
            (0, 0, 280, 300),
            navigation_back=True,
        )
        self.assertEqual(menu.layout_mode, "LIST_FALLBACK")
        self.assertTrue(menu.open_row_context(1, None))
        with menu.surface_transform(menu.root.rect, lambda rect: rect, 1):
            pass
        menu.back()
        self.assertEqual(menu.page.rows[0].key, "__back__")

    def test_navigation_budget_includes_saved_pies_and_context_pages(self):
        def more(t, c):
            return PieRows((Entry("next", "Next", children=more),))

        self.root.page.rows = (replace(self.root.page.rows[0], children=more),)
        for _ in range(3):
            self.click()
        last = self.canvas.context_menu
        self.click()
        self.assertIs(self.canvas.context_menu, last)
        self.assertEqual(last.navigation_depth(), 3)
        self.canvas.cancel()
        self.assertTrue(last.closed)
        self.assertTrue(self.root.closed)


class CompoundLayout(unittest.TestCase):
    def layout(self):
        model = NS(
            invocation="EXEC_DEFAULT",
            pointers=NS(values=lambda: {}),
            layout=NS(_text=lambda text, *args: text),
        )
        layout = MenuLayout(model, None, None, 0)
        return layout.menu_pie()

    def test_split_grid_flow_alignment_scaling_and_spacer_geometry(self):
        pie = self.layout()
        column = pie.column()
        split = column.split(factor=0.3)
        split.label(text="Left")
        split.label(text="Right")
        grid = column.grid_flow(
            columns=2, row_major=True, even_columns=True, even_rows=True
        )
        for i in range(4):
            grid.label(text=str(i))
        flow = column.column_flow(columns=2)
        for i in range(4):
            flow.label(text="flow" + str(i))
        row = column.row(align=True)
        row.ui_units_x = 20
        row.scale_y = 1.5
        row.label(text="A")
        row.separator_spacer()
        row.label(text="B")
        column.separator(factor=2, type="LINE")
        slots = Slots(pie.rows, lambda text, size: len(text) * size * 0.6)
        root = slots.roots[0]
        w, h = slots.sizes[root]
        slots.arrange(root, (0, 0, w, h))
        rect = slots.rectangles
        self.assertAlmostEqual(rect[0][2] / (rect[0][2] + rect[1][2]), 0.3)
        self.assertEqual(rect[2][1], rect[3][1])
        self.assertGreater(rect[4][1], rect[2][1])
        self.assertEqual(rect[6][0], rect[7][0])
        self.assertGreater(rect[8][0], rect[6][0])
        self.assertGreater(rect[11][0] - rect[10][0], 300)
        self.assertEqual(rect[10][3], 34.5)
        self.assertEqual(rect[12][3], 16)
        self.assertEqual(len(rect), 13)
        # Packing is retained: placement does not mutate the author's tree.
        self.assertEqual(len(row.rows), 3)

    def test_alignment_and_dimensions_validate_without_native_fallback(self):
        pie = self.layout()
        row = pie.row()
        row.ui_units_x = 20
        row.alignment = "RIGHT"
        row.label(text="A")
        slots = Slots(pie.rows, lambda t, s: len(t) * 6)
        root = slots.roots[0]
        w, h = slots.sizes[root]
        slots.arrange(root, (0, 0, w, h))
        x, y, rw, rh = slots.rectangles[0]
        self.assertAlmostEqual(x + rw, w)
        self.assertGreater(x, 0)
        for name, value in (
            ("scale_x", float("inf")),
            ("ui_units_y", -1),
            ("alignment", "BAD"),
        ):
            with self.assertRaises(ValueError):
                setattr(row, name, value)
        with self.assertRaises(ValueError):
            pie.separator_spacer()
        with self.assertRaises(ValueError):
            row.column_flow(columns=-1)
        with self.assertRaises(ValueError):
            row.split(factor=2)

    def test_compound_owner_cycles_fail_with_the_same_bounded_depth(self):
        group = Compound("column", [])
        row = Entry("cycle", "", compound=group)
        group.rows.append(row)
        with self.assertRaisesRegex(ValueError, "depth"):
            retarget(PieRows((row,)), Target("owner"))

    def test_retarget_preserves_radial_type_and_compound_owner_guards(self):
        valid = [True]
        calls = []
        child = Entry("action", "Action", lambda t, c: calls.append(t.key))
        rows = PieRows((Entry("group", "", compound=Compound("column", [child])),))
        result = retarget(rows, Target("inner", valid=lambda: valid[0]))
        self.assertIsInstance(result, PieRows)
        leaf = result[0].compound.rows[0]
        leaf.action(Target("outer"), None)
        self.assertEqual(calls, ["inner"])
        valid[0] = False
        self.assertFalse(leaf.enabled(Target("outer"), None))
        with self.assertRaises(ReferenceError):
            leaf.action(Target("outer"), None)


if __name__ == "__main__":
    unittest.main()
