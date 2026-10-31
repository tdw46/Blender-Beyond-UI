"""Small opt-in consumer lifecycle; importing creates no Blender side effects."""

from .animation import AnimationSettings


class AddonUI:
    """Register normal Panel definitions with a retained custom ``self.layout``.

    Use a unique extension package as owner. Register data/operators first, then
    panels here. Do not also register these panel definitions with bpy directly.
    """

    def __init__(
        self,
        owner,
        *,
        commit=None,
        context_menu=None,
        animation=None,
        layout_options=None,
        native_fallback=False,
    ):
        if not isinstance(owner, str) or not owner:
            raise ValueError("Use your extension's unique __package__ as owner")
        self.owner = owner
        self.native_fallback = bool(native_fallback)
        self.commit = commit
        self.context_menu = context_menu
        self.animation = animation or AnimationSettings()
        self.layout_options = dict(layout_options or {})
        if set(self.layout_options) - {
            "resolve",
            "source",
            "pointer_sources",
            "id_actions",
            "list_identity",
        }:
            raise ValueError("Unknown Layout integration option")
        self._runtime = None

    def register(self, *panels):
        if self._runtime is not None:
            if tuple(panels) != self._runtime.definitions:
                raise RuntimeError("Unregister before changing panel definitions")
            return
        from .hosts.addon import Runtime

        runtime = Runtime(self, panels)
        try:
            runtime.register()
        except Exception:
            runtime.close()
            raise
        self._runtime = runtime

    def unregister(self):
        runtime, self._runtime = self._runtime, None
        if runtime is not None:
            runtime.close()

    def refresh(self):
        """Rebuild conditional layout after the current input transaction finishes."""
        if self._runtime is not None:
            self._runtime.schedule_refresh()

    @property
    def status(self):
        if self._runtime is None:
            return {"registered": False, "panels": {}}
        return self._runtime.status()
