import math
import unittest
from types import SimpleNamespace as NS
from beyond_ui.numeric import Numeric, checked_units


def codec(subtype="NONE", unit="NONE", **kw):
    meta = NS(
        type="FLOAT",
        subtype=subtype,
        unit=unit,
        soft_min=-1000.0,
        soft_max=1000.0,
        step=3,
        precision=3,
    )
    for k, v in kw.items():
        setattr(meta, k, v)
    context = NS(
        scene=NS(
            unit_settings=NS(
                system="NONE",
                scale_length=1.0,
                system_rotation="DEGREES",
                length_unit="ADAPTIVE",
                use_separate=False,
            )
        ),
        preferences=NS(view=NS(factor_display_type="FACTOR")),
    )
    return Numeric(meta, context)


class NumericSemantics(unittest.TestCase):
    def test_rotation_and_roundtrip(self):
        n = codec("ANGLE")
        self.assertEqual(n.format(math.pi / 2), "90°")
        self.assertAlmostEqual(n.parse("90", 0), math.pi / 2)
        original = 1.23456789123
        self.assertEqual(n.parse(n.format(original), original), original)
        n.context.scene.unit_settings.system_rotation = "RADIANS"
        self.assertEqual(n.format(math.pi), "3.142 rad")
        self.assertEqual(n.parse("2+3", original), 5)

    def test_factor_percentage_and_live_settings(self):
        n = codec("FACTOR")
        self.assertEqual(n.parse("50%", 0), 0.5)
        n.context.preferences.view.factor_display_type = "PERCENTAGE"
        self.assertEqual(n.format(0.25), "25%")
        self.assertEqual(n.parse("50", 0), 0.5)
        self.assertEqual(codec("PERCENTAGE").parse("50%", 0), 50)
        self.assertEqual(codec(type="INT").format(12345), "12345")
        self.assertEqual(codec("PERCENTAGE", type="INT").format(100), "100%")

    def test_unit_guard(self):
        for good in (
            "1m 3cm",
            "2ft+3in",
            "(1m+2cm)/2",
            "90°",
            "1e-3m",
            "2m²",
            "3' 2\"",
        ):
            self.assertEqual(checked_units(good), good)
        for bad in (
            "__import__('os')",
            "(1).__class__",
            "2**999999999",
            "2//3",
            "[1]*2",
            "open('x')",
            "1m;2",
            "(" * 13 + "1" + ")" * 13,
        ):
            with self.assertRaises(ValueError):
                checked_units(bad)

    def test_bounded_drag_and_precision(self):
        n = codec("ANGLE", soft_min=-1e38, soft_max=1e38)
        step = n.drag(n.snapshot())
        self.assertGreater(step, 0)
        self.assertLess(step, 0.01)
        self.assertAlmostEqual(n.drag(n.snapshot(), precision=True), step / 4)

    def test_rejected_commit_rolls_back_and_closes_edit(self):
        from beyond_ui import Canvas
        from beyond_ui.bindings import Binding

        values = [1.23456789]

        def reject(before, after):
            raise RuntimeError("rejected host undo")

        binding = Binding(
            lambda: values[0], lambda value: values.__setitem__(0, value), commit=reject
        )
        canvas = Canvas()
        control = canvas.number("n", "Value", binding)
        canvas._begin(control)
        canvas._write(9)
        with self.assertRaises(RuntimeError):
            canvas.finish()
        self.assertEqual(values[0], 1.23456789)
        self.assertIsNone(canvas.edit)
        self.assertIsNone(canvas.active)

    def test_unchanged_numeric_confirmation_does_not_call_setter(self):
        from beyond_ui import Canvas
        from beyond_ui.bindings import Binding

        writes = []
        canvas = Canvas()
        control = canvas.number(
            "n",
            "Angle",
            Binding(lambda: 1.23456789, writes.append),
            numeric=codec("ANGLE"),
        )
        canvas.arrange(300)
        clip = (0, 0, 300, canvas.height)
        canvas.event(NS(type="LEFTMOUSE", value="DOUBLE_CLICK"), 20, 20, clip)
        canvas.event(NS(type="RET", value="PRESS"), 20, 20, clip)
        self.assertEqual(writes, [])
        self.assertIsNone(canvas.edit)

    def test_wide_numeric_motion_is_fifteen_percent_with_parent_policy(self):
        from beyond_ui import Canvas
        from beyond_ui.bindings import Binding
        from beyond_ui.animation import AnimationSettings

        canvas = Canvas(animation=AnimationSettings(strength=2))
        canvas.wide_numeric_motion_scale = 0.15  # Configure before first arrange.
        binding = Binding(lambda: 0, lambda value: None)
        wide = canvas.number("wide", "Wide", binding)
        row = canvas.row()
        small = row.number("small", "Small", binding)
        row.number("other", "Other", binding)
        button = canvas.button("button", "Button", lambda: None)
        canvas.arrange(600)
        self.assertAlmostEqual(wide.motion.strength, 0.3)
        self.assertEqual(small.motion.strength, 2)
        self.assertEqual(button.motion.strength, 2)
        wide.motion.clock = lambda: 0
        wide.motion.pulse("body", 0.2)
        self.assertAlmostEqual(wide.motion.tracks["body"][1], 0.06)
        rect = wide.rect
        canvas.wide_numeric_motion_scale = 0.1
        self.assertEqual(wide.rect, rect)
        self.assertFalse(wide.motion.tracks)
        self.assertAlmostEqual(wide.motion.strength, 0.2)
        canvas.animation.enabled = False
        self.assertEqual(wide.motion.strength, 0)
        for bad in (float("nan"), -1, None):
            with self.assertRaises(ValueError):
                canvas.wide_numeric_motion_scale = bad
