"""Reversible routing of existing shortcuts targeting this package's menus only."""


class KeymapRoutes:
    def __init__(self, router):
        self.router = router
        self.items = []

    def refresh(self, wm):
        # Registration/explicit refresh only. Never scan keymaps in paint or idle.
        tracked = set()
        for item, *_ in self.items:
            try:
                tracked.add(item.as_pointer())
            except ReferenceError:
                pass
        for config in (wm.keyconfigs.addon, wm.keyconfigs.user):
            if config is None:
                continue
            for keymap in config.keymaps:
                if keymap.is_modal:
                    continue
                for item in keymap.keymap_items:
                    if item.as_pointer() in tracked:
                        continue
                    if item.idname == self.router.idname:
                        # A saved user customization or a regenerated effective
                        # keymap can already contain our stable owner-local route.
                        name = item.properties.menu_name
                        if self.router.owns_menu(name):
                            pie = item.properties.pie
                            self.items.append(
                                (
                                    item,
                                    "wm.call_menu_pie" if pie else "wm.call_menu",
                                    name,
                                    pie,
                                )
                            )
                        continue
                    if item.idname not in {"wm.call_menu", "wm.call_menu_pie"}:
                        continue
                    name = getattr(item.properties, "name", "")
                    if not self.router.owns_menu(name):
                        continue
                    original = item.idname
                    pie = original == "wm.call_menu_pie"
                    # Keep the SAME item and event chord/order/active state. Its
                    # operator schema changes, so snapshot properties first.
                    self.items.append((item, original, name, pie))
                    try:
                        item.idname = self.router.idname
                        item.properties.menu_name = name
                        item.properties.pie = pie
                    except Exception:
                        item.idname = original
                        item.properties.name = name
                        self.items.pop()
                        raise

    def close(self):
        for item, original, name, pie in reversed(self.items):
            try:
                # Respect removal/reassignment by another owner. Chord changes
                # are deliberately retained, even while this route is installed.
                if item.idname == self.router.idname:
                    current = item.properties.menu_name
                    current_pie = item.properties.pie
                    item.idname = (
                        original
                        if current_pie == pie
                        else ("wm.call_menu_pie" if current_pie else "wm.call_menu")
                    )
                    item.properties.name = current or name
            except ReferenceError:
                pass
        self.items.clear()
