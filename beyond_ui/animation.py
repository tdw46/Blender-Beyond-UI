"""Source springs with finite lifetimes. No bpy, timer or GPU work on import."""

from contextlib import contextmanager, nullcontext
from math import isfinite
from time import monotonic
from weakref import WeakSet


_REST = nullcontext()


class AnimationSettings:
    """Mutable backend policy. None strength inherits the nearest parent value."""

    def __init__(self, *, enabled=True, strength=None):
        self._listeners = WeakSet()
        self._enabled = bool(enabled)
        self._strength = self._validate(strength)

    @staticmethod
    def _validate(value):
        if value is None:
            return None
        value = float(value)
        if not isfinite(value) or value < 0:
            raise ValueError("Animation strength must be finite and nonnegative")
        return value

    def _changed(self):
        for motion in tuple(self._listeners):
            motion.clear()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        value = bool(value)
        if value != self._enabled:
            self._enabled = value
            self._changed()

    @property
    def strength(self):
        return self._strength

    @strength.setter
    def strength(self, value):
        value = self._validate(value)
        if value != self._strength:
            self._strength = value
            self._changed()


animation_defaults = AnimationSettings(strength=1.0)


class Motion:
    """One retained control's chrome; logical hit regions never deform.

    Regions are declared by its painter. Only visible regions are retained.
    A host calls input() before dispatching an event and schedules while active.
    Text remains stationary, like the source's hover lens presentation.
    """

    def __init__(self, settings=None, *, clock=monotonic):
        self.settings = settings or AnimationSettings()
        self.clock = clock
        self.toggle = False
        self.wake = None
        self.regions = {}
        self.tracks = {}
        self.hover = self.pressed = self.pointer = None
        self.parents = ()
        self.bind(())

    def bind(self, parents, wake=None):
        policies = (animation_defaults, *parents, self.settings)
        if policies != self.parents:
            for policy in self.parents:
                policy._listeners.discard(self)
            self.parents = policies
            for policy in policies:
                policy._listeners.add(self)
            self.clear()
        self.wake = wake

    @property
    def strength(self):
        value = 1.0
        for policy in self.parents:
            if not policy.enabled or policy.strength == 0:
                return 0.0
            if policy.strength is not None:
                value = policy.strength
        return value

    def clear(self):
        changed = bool(self.tracks)
        self.tracks.clear()
        self.hover = self.pressed = self.pointer = None
        if changed and self.wake:
            self.wake(self)

    def begin_paint(self):
        self.regions.clear()

    def region(self, key, rect, *, circular=False):
        # Bounded even if a consumer accidentally emits an unvirtualized list.
        if len(self.regions) < 256 or key in self.regions:
            self.regions[key] = (tuple(rect), circular)

    def sample(self, key, now=None):
        track = self.tracks.get(key)
        if track is None or not self.strength:
            return (1.0, 1.0), 0.0
        start, amount, initial, angle, toggle = track
        now = self.clock() if now is None else now
        from .gpu.style import release_shape

        return release_shape(amount, now - start, initial, toggle), angle

    def pulse(self, key, amount=0.14, angle=0.0, *, toggle=False):
        toggle = toggle or self.toggle
        strength = self.strength
        if not strength:
            return
        now = self.clock()
        shape, old_angle = self.sample(key, now)
        if shape != (1.0, 1.0):
            angle = old_angle  # No directional discontinuity while retargeting.
        if len(self.tracks) >= 32 and key not in self.tracks:
            self.tracks.pop(next(iter(self.tracks)))
        # Preserve source amplitude at 1x; cap extreme user strength safely.
        amplitude = max(-0.85, min(0.85, amount * strength))
        self.tracks[key] = (now, amplitude, shape[0] - 1.0, angle, toggle)
        if self.wake:
            self.wake(self)

    def advance(self):
        from .gpu.style import SWITCH_DURATION, HANDLE_DURATION

        now = self.clock()
        for key, track in tuple(self.tracks.items()):
            duration = SWITCH_DURATION if track[4] else HANDLE_DURATION
            if not self.strength or now - track[0] >= duration:
                del self.tracks[key]
        return bool(self.tracks)

    def input(self, event, x, y):
        from .gpu.style import hover_impulse, velocity_impulse

        if event.type in {"WINDOW_DEACTIVATE", "ESC", "RIGHTMOUSE"}:
            self.clear()
            return
        if event.type not in {"MOUSEMOVE", "LEFTMOUSE"}:
            return
        now = self.clock()
        previous = self.pointer
        dx, dy, dt = (
            (x - previous[0], y - previous[1], now - previous[2])
            if previous
            else (0, 0, 1 / 60)
        )
        self.pointer = (x, y, now)
        target = next(
            (
                key
                for key, (r, _) in reversed(tuple(self.regions.items()))
                if r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]
            ),
            None,
        )
        if target is not None and target != self.hover:
            r, circular = self.regions[target]
            amount, angle = hover_impulse(r[2], r[3], circular, dx, -dy, dt)
            self.pulse(target, amount, angle)
        self.hover = target
        if event.type == "LEFTMOUSE":
            if event.value in {"PRESS", "DOUBLE_CLICK"}:
                self.pressed = target
                if target is not None:
                    self.pulse(target, -0.10)
            elif event.value == "RELEASE":
                if self.pressed is not None:
                    amount, angle = velocity_impulse(dx, -dy, dt)
                    self.pulse(self.pressed, max(0.24, amount), angle)
                self.pressed = None
        elif self.pressed is not None and (dx or dy):
            amount, angle = velocity_impulse(dx, -dy, dt)
            self.pulse(self.pressed, amount, angle)

    def deform(self, key, rect):
        """Transform retained geometry only. No allocation on the resting path."""
        shape, angle = self.sample(key)
        if shape == (1.0, 1.0):
            return _REST
        return self._deformed(rect, shape, angle)

    @staticmethod
    @contextmanager
    def _deformed(rect, shape, angle):
        import gpu
        from mathutils import Matrix

        x, y, w, h = rect
        with gpu.matrix.push_pop():
            gpu.matrix.translate((x + w / 2, y + h / 2, 0))
            if angle:
                gpu.matrix.multiply_matrix(Matrix.Rotation(angle, 4, "Z"))
            gpu.matrix.scale((*shape, 1))
            if angle:
                gpu.matrix.multiply_matrix(Matrix.Rotation(-angle, 4, "Z"))
            gpu.matrix.translate((-x - w / 2, -y - h / 2, 0))
            yield
