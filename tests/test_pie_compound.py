import unittest
from types import SimpleNamespace as NS
from dataclasses import replace
from unittest.mock import patch
from contextlib import nullcontext
from beyond_ui import Canvas
from beyond_ui.context_menu import Entry, Target
from beyond_ui.pie_menu import PieMenu
from beyond_ui.pie_layout import Compound
from beyond_ui.pie_timing import PieSettings
from beyond_ui.registered_menu import MenuLayout


def event(kind, value="PRESS", **kwargs):
    return NS(type=kind, value=value, **kwargs)


class PieCompound(unittest.TestCase):
    def make(self, rows=None, **kwargs):
        self.now = [0.0]
        self.calls = []
        if rows is None:
            rows = [
                Entry(str(i), f"Action {i}", lambda t, c, i=i: self.calls.append(i))
                for i in range(8)
            ]
        return PieMenu(
            Target("owner"),
            rows,
            (600, 450),
            (0, 0, 1200, 900),
            clock=lambda: self.now[0],
            **kwargs,
        )

    def test_native_tap_hold_drag_and_recenter_boundaries(self):
        menu = self.make(trigger="Q", settings=PieSettings(tap=0.2, recenter=0.1))
        menu.event(event("Q", "RELEASE"), *menu.origin)
        self.assertFalse(menu.closed)
        menu = self.make(trigger="Q")
        self.now[0] = 0.201
        menu.event(event("Q", "RELEASE"), *menu.origin)
        self.assertTrue(menu.closed)
        menu = self.make(trigger="Q")
        menu.event(event("MOUSEMOVE", "NOTHING"), 700, 450)
        menu.event(event("Q", "RELEASE"), 700, 450)
        self.assertEqual(self.calls, [1])
        menu = PieMenu(
            Target("owner"),
            [Entry("a", "A")],
            (0, 0),
            (0, 0, 1200, 900),
            clock=lambda: self.now[0],
            settings=PieSettings(recenter=0.1),
        )
        self.assertEqual(menu.direction_origin(), (0, 0))
        self.now[0] = 0.101
        self.assertEqual(menu.direction_origin(), menu.center)

    def test_confirm_wait_retargets_cancels_and_checks_exact_owner(self):
        menu = self.make(trigger="Q", settings=PieSettings(confirm=20))
        menu.event(event("MOUSEMOVE", "NOTHING"), 700, 450)
        self.now[0] = 0.019
        self.assertTrue(menu.advance())
        self.assertEqual(self.calls, [])
        menu.event(event("MOUSEMOVE", "NOTHING"), 500, 450)
        self.now[0] = 0.03
        menu.advance()
        self.assertEqual(self.calls, [])
        self.now[0] = 0.041
        menu.advance()
        self.assertEqual(self.calls, [0])
        menu = self.make(trigger="Q", settings=PieSettings(confirm=20))
        menu.event(event("MOUSEMOVE", "NOTHING"), 700, 450)
        menu.target = Target("gone", valid=lambda: False)
        self.now[0] = 0.03
        menu.advance()
        self.assertTrue(menu.closed)
        self.assertEqual(self.calls, [])

    def test_no_timer_action_survives_navigation_or_teardown(self):
        menu = self.make(trigger="Q", settings=PieSettings(confirm=20))
        menu.event(event("MOUSEMOVE", "NOTHING"), 700, 450)
        menu.page.rows = tuple(
            replace(r, context=lambda t, c: (Entry("copy", "Copy"),))
            for r in menu.page.rows
        )
        menu.open_row_context(1, None)
        self.now[0] = 1
        self.assertFalse(menu.advance())
        self.assertEqual(self.calls, [])
        menu.close()
        self.assertFalse(menu.advance())

    def test_compound_groups_keep_individual_hits_and_one_direction(self):
        calls = []
        leaf = lambda key: Entry(key, key, lambda t, c: calls.append(key))
        group = Entry(
            "group",
            "",
            compound=Compound(
                "column",
                [
                    leaf("top"),
                    Entry(
                        "row",
                        "",
                        compound=Compound("row", [leaf("left"), leaf("right")]),
                    ),
                ],
            ),
        )
        menu = self.make([group, leaf("east")])
        self.assertEqual(menu.layout_mode, "PIE")
        self.assertEqual(len(menu.slots.roots), 2)
        self.assertEqual(len(menu.page.rows), 4)
        self.assertIsNone(menu.direction_leaf(0))
        a = menu.row_rectangles[1]
        b = menu.row_rectangles[2]
        self.assertEqual(a[1], b[1])
        self.assertLess(a[0] + a[2], b[0])
        x, y, w, h = b
        menu.event(event("LEFTMOUSE"), x + w / 2, y + h / 2)
        self.assertEqual(calls, [])
        menu.event(event("LEFTMOUSE", "RELEASE"), x + w / 2, y + h / 2)
        self.assertEqual(calls, ["right"])

    def test_collector_preserves_tree_and_parent_disable(self):
        model = NS(
            invocation="EXEC_DEFAULT",
            pointers=NS(values=lambda: {}),
            layout=NS(_text=lambda text, *a: text),
        )
        root = MenuLayout(model, None, None, 0)
        pie = root.menu_pie()
        box = pie.box()
        col = box.column(heading="Settings")
        row = col.row(align=True)
        row.label(text="A")
        row.label(text="B")
        pie.label(text="East")
        self.assertEqual(len(root.rows), 2)
        self.assertTrue(row.eligible())
        box.enabled = False
        self.assertFalse(row.eligible())
        menu = self.make(root.rows)
        self.assertEqual(len(menu.slots.roots), 2)
        self.assertEqual(
            [r.label for r in menu.page.rows], ["Settings", "A", "B", "East"]
        )
        self.assertGreater(len(menu.surfaces(menu.page)), 2)

    def test_bounded_empty_or_cyclic_trees(self):
        from itertools import repeat

        blank = Entry("empty", "", compound=Compound("column", ()))
        with self.assertRaises(ValueError):
            self.make([Entry("many", "", compound=Compound("column", repeat(blank)))])
        children = []
        root = Entry("cyclic", "", compound=Compound("column", children))
        children.append(root)
        with self.assertRaises(ValueError):
            self.make([root])

    def test_growth_tension_proximity_disable_and_idle(self):
        menu = self.make(settings=PieSettings(animation=0.1))
        geometry = dict(menu.row_rectangles)
        self.assertEqual(menu.opening(), 0)
        self.now[0] = 0.05
        self.assertAlmostEqual(menu.opening(), 0.5)
        x, y, w, h = menu.rectangles[1]
        menu.event(event("MOUSEMOVE", "NOTHING"), 650, 450)
        low = menu.highlight_alpha(menu.page, 1)
        menu.event(event("MOUSEMOVE", "NOTHING"), x - 1, y + h / 2)
        self.assertGreater(menu.highlight_alpha(menu.page, 1), low)
        self.assertEqual(menu.guide()[0], menu.origin)
        self.now[0] = 0.5
        self.assertNotEqual(menu.pull(1), (0, 0))
        self.assertEqual(menu.row_rectangles, geometry)
        canvas = Canvas()
        canvas.context_menu = menu
        menu.motion.bind((canvas.animation,), canvas._wake_motion)
        canvas.animation.enabled = False
        self.assertEqual(menu.pull(1), (0, 0))
        self.assertEqual(menu.opening(), 1)
        self.assertFalse(canvas.advance_animations())
        canvas.animation.enabled = True
        menu.event(event("MOUSEMOVE", "NOTHING"), *menu.center)
        self.now[0] = 3
        self.assertEqual(menu.pull(1), (0, 0))
        self.assertFalse(canvas.advance_animations())

    def test_preference_snapshot_units_fallbacks_validation(self):
        view = NS(
            pie_animation_timeout=12,
            pie_tap_timeout=30,
            pie_initial_timeout=5,
            pie_menu_radius=110,
            pie_menu_threshold=14,
            pie_menu_confirm=20,
        )
        settings = PieSettings.from_context(NS(preferences=NS(view=view)))
        self.assertEqual(
            (settings.animation, settings.tap, settings.recenter), (0.12, 0.3, 0.05)
        )
        view.pie_tap_timeout = 100
        self.assertEqual(settings.tap, 0.3)
        self.assertEqual(PieSettings.from_context(None), PieSettings())
        view.use_reduce_motion = True
        reduced = PieSettings.from_context(NS(preferences=NS(view=view)))
        menu = self.make(settings=reduced)
        self.assertEqual(menu.opening(), 1)
        menu.update_pointer(700, 450)
        self.assertEqual(menu.pull(1), (0, 0))
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                PieSettings(tap=value)

    def test_painter_traverses_transforms_without_gpu_or_binding_reads(self):
        # Command traversal only. It cannot establish rendered appearance.
        from beyond_ui.gpu import menus, skin, style, glass, paint, typography

        menu = self.make()
        self.now[0] = 0.03
        menu.update_pointer(700, 450)
        fake_gpu = NS(
            matrix=NS(
                push_pop=lambda: nullcontext(),
                translate=lambda *a: None,
                scale=lambda *a: None,
                multiply_matrix=lambda *a: None,
            )
        )
        fake_blf = NS(size=lambda *a: None)
        draws = []
        with (
            patch.dict(
                "sys.modules",
                gpu=fake_gpu,
                blf=fake_blf,
                mathutils=NS(Matrix=NS(Rotation=lambda *a: None)),
            ),
            patch.object(typography, "motion_text", return_value=nullcontext()),
            patch.object(
                paint, "measure", side_effect=lambda f, s, t: (len(t) * 6, 10)
            ),
            patch.object(skin, "draw"),
            patch.object(glass, "lens", return_value=True),
            patch.object(style, "icon"),
            patch.object(
                menus, "text_run", side_effect=lambda *a, **kw: draws.append(a[1])
            ),
        ):
            menus.context_menu(
                menu,
                lambda r: r,
                1,
                0,
                style.theme_palette(reference=True),
                "retained",
                (0, 0, 1200, 900),
            )
        self.assertEqual(draws, [f"Action {i}" for i in range(8)])
        self.assertTrue(menu.glass_ready)

    def test_pending_compound_click_does_not_retarget_another_child(self):
        calls = []
        group = Entry(
            "group",
            "",
            compound=Compound(
                "row",
                [
                    Entry("a", "A", lambda t, c: calls.append("a")),
                    Entry("b", "B", lambda t, c: calls.append("b")),
                ],
            ),
        )
        menu = self.make([group])
        a = menu.row_rectangles[0]
        b = menu.row_rectangles[1]
        menu.event(event("LEFTMOUSE"), a[0] + 5, a[1] + 5)
        menu.event(event("MOUSEMOVE", "NOTHING"), b[0] + 5, b[1] + 5)
        menu.event(event("LEFTMOUSE", "RELEASE"), b[0] + 5, b[1] + 5)
        self.assertEqual(calls, [])

    def test_canvas_click_captures_exact_pointer_origin(self):
        canvas = Canvas()
        model = NS(
            context=None, pie=True, rows=lambda ctx: ((Entry("a", "A"),), lambda: True)
        )
        button = canvas.button("pie", "Pie", None, menu_model=model)
        canvas.arrange(1200)
        x, y, w, h = button.rect
        self.assertTrue(
            canvas.event(event("LEFTMOUSE"), x + 17, y + 9, (0, 0, 1200, 900))
        )
        self.assertEqual(canvas.context_menu.origin, (x + 17, y + 9))

    def test_opening_strength_is_live_and_nonsingular(self):
        menu = self.make(settings=PieSettings(animation=0.1))
        menu.motion.settings.strength = 0.25
        self.assertEqual(menu.opening(), 0.75)
        menu.motion.settings.strength = 1e30
        self.assertEqual(menu.opening(), 0)
        menu.motion.settings.strength = 0
        self.assertEqual(menu.opening(), 1)

    def test_petal_labels_reserve_toggle_field_and_shortcut_lanes(self):
        from beyond_ui.pie_layout import Slots
        from beyond_ui.context_edit import Field

        rows = [
            Entry("toggle", "Transparent", toggle=True),
            Entry(
                "field", "Resolution", field=Field(lambda t, c: 100, lambda *a: None)
            ),
            Entry(
                "shortcut", "Action", shortcut="Shift Ctrl X", children=lambda t, c: ()
            ),
        ]
        measure = lambda text, size: len(text) * size * 0.6
        slots = Slots(rows, measure)
        self.assertGreaterEqual(
            slots.sizes[0][0] - 27 - 8 - 50, measure("Transparent", 11)
        )
        self.assertGreaterEqual(
            slots.sizes[1][0] * 0.44 - 27, measure("Resolution", 11)
        )
        self.assertGreaterEqual(
            slots.sizes[2][0] - 27 - 8 - 16 - 14 - measure("Shift Ctrl X", 10),
            measure("Action", 11),
        )

    def test_circular_placement_retains_radius_and_separates_unequal_slots(self):
        from math import hypot

        rows = [Entry(str(i), "Wide label " * (1 + i % 3)) for i in range(8)]
        menu = self.make(rows)
        self.assertEqual(menu.layout_mode, "PIE")
        for i, (x, y, w, h) in enumerate(menu.rectangles):
            self.assertAlmostEqual(
                hypot(x + w / 2 - menu.center[0], y + h / 2 - menu.center[1]),
                menu.placement_radius,
            )
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + w, 1200)
            for a, b, c, d in menu.rectangles[:i]:
                self.assertTrue(x + w <= a or a + c <= x or y + h <= b or b + d <= y)


if __name__ == "__main__":
    unittest.main()
