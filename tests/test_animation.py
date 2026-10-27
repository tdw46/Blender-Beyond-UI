import unittest
from types import SimpleNamespace
from beyond_ui import AnimationSettings, Canvas, animation_defaults
from beyond_ui.animation import Motion
from beyond_ui.gpu.style import release_shape


class AnimationTests(unittest.TestCase):
    def motion(self, **settings):
        now = [0.0]
        motion = Motion(AnimationSettings(**settings), clock=lambda: now[0])
        wakes = []
        motion.bind((), lambda m: wakes.append(m))
        motion.region("button", (10, 10, 100, 30))
        return motion, now, wakes

    def test_source_equation_retarget_and_exact_settle(self):
        motion, now, wakes = self.motion()
        motion.pulse("button", 0.24)
        now[0] = 0.1
        self.assertEqual(motion.sample("button")[0], release_shape(0.24, 0.1, 0.0))
        before = motion.sample("button")
        motion.pulse("button", 0.4, 1.2)
        self.assertEqual(motion.sample("button"), before)
        now[0] = 0.2
        sx, sy = motion.sample("button")[0]
        self.assertAlmostEqual(sx * sy, 1.0)
        now[0] = 1.11
        self.assertFalse(motion.advance())
        self.assertEqual(motion.sample("button")[0], (1.0, 1.0))
        self.assertEqual(len(wakes), 2)

    def test_policy_inheritance_disable_live_and_strength_limits(self):
        motion, now, wakes = self.motion(strength=2)
        host = AnimationSettings(strength=0.5)
        motion.bind((host,), lambda m: wakes.append(m))
        motion.pulse("button", 0.2)
        now[0] = 0.1
        self.assertEqual(motion.sample("button")[0], release_shape(0.4, 0.1, 0.0))
        host.enabled = False
        self.assertEqual(motion.sample("button")[0], (1.0, 1.0))
        self.assertFalse(motion.advance())
        motion.pulse("button")
        self.assertFalse(motion.tracks)
        host.enabled = True
        host.strength = 0
        motion.pulse("button")
        self.assertFalse(motion.tracks)
        host.strength = 1
        motion.settings.strength = 1e30
        motion.pulse("button", 1)
        for t in range(100):
            now[0] = 0.1 + t / 100
            sx, sy = motion.sample("button")[0]
            self.assertGreater(sx, 0)
            self.assertAlmostEqual(sx * sy, 1)
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                host.strength = value

    def test_hover_is_finite_drag_retargets_and_hit_rects_stay_still(self):
        motion, now, wakes = self.motion()

        def event(kind, value="NOTHING"):
            return SimpleNamespace(type=kind, value=value)

        motion.input(event("MOUSEMOVE"), 30, 20)
        self.assertEqual(len(wakes), 1)
        now[0] = 0.2
        motion.input(event("MOUSEMOVE"), 31, 20)
        self.assertEqual(len(wakes), 1)  # Resting hover never restarts its spring.
        motion.input(event("LEFTMOUSE", "PRESS"), 31, 20)
        now[0] = 0.25
        before = motion.sample("button")
        motion.input(event("MOUSEMOVE"), 90, 22)
        self.assertEqual(motion.sample("button"), before)
        motion.input(event("LEFTMOUSE", "RELEASE"), 300, 22)
        self.assertIsNone(motion.pressed)
        self.assertEqual(motion.regions["button"][0], (10, 10, 100, 30))
        now[0] = 2
        self.assertFalse(motion.advance())

    def test_canvas_changes_hide_and_independent_policy(self):
        from beyond_ui.widgets import Progress

        canvas = Canvas()
        other = Canvas()
        c = canvas.widget("progress", Progress(0.5))
        canvas.arrange(400)
        original = c.rect
        wakes = []
        canvas.bind_animation(wake=lambda: wakes.append(True))
        canvas.notify_changed("progress")
        self.assertTrue(canvas.advance_animations())
        self.assertEqual(c.rect, original)
        self.assertFalse(other.advance_animations())
        canvas.animation.enabled = False
        self.assertFalse(canvas.advance_animations())
        canvas.animation.enabled = True
        canvas.notify_changed("progress")
        self.assertFalse(canvas.advance_animations((10000, 10000, 40, 40)))
        canvas.notify_changed("progress")
        canvas.park()
        self.assertFalse(canvas.advance_animations())
        self.assertFalse(c.motion.tracks)
        self.assertEqual(animation_defaults.strength, 1.0)


if __name__ == "__main__":
    unittest.main()
