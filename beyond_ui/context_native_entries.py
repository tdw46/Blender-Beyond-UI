"""Shared native-data actions in the custom menu; no separate renderer or motion."""

from .context_menu import Entry
from .hosts import menu_native
from .context_paths import owner_path


def entries(source, context):
    rows = []
    if source.metadata().type in {"FLOAT", "INT", "BOOLEAN", "ENUM"} and hasattr(
        getattr(source.owner(), "id_data", None), "animation_data"
    ):
        for key, label in (
            ("COPY_DRIVER", "Copy Driver"),
            ("PASTE_DRIVER", "Paste Driver"),
            ("NATIVE_DRIVER", "Copy as New Driver"),
        ):
            rows.append(
                Entry(
                    key,
                    label,
                    lambda t, c, k=key: source.execute(k, t, c),
                    lambda t, c, k=key: t.valid()
                    and source.valid()
                    and source.animation_applicable(k)
                    and menu_native.driver_enabled(k, source, t),
                    tip="Uses Blender's real driver clipboard on admitted builds; paste requires host undo.",
                )
            )
    initial_path = owner_path(source, context)
    is_favorite = menu_native.property_favorite(source, context)
    key = "REMOVE_FAVORITE" if is_favorite else "FAVORITE"
    rows.append(
        Entry(
            key,
            "Remove from Quick Favorites" if is_favorite else "Add to Quick Favorites",
            lambda t, c: source.execute(key, t, c),
            lambda t, c: t.valid()
            and source.valid()
            and owner_path(source, c) == initial_path
            and menu_native.favorite_supported(source, c),
            divider=True,
            icon="menu",
            tip="Context-relative Blender Favorite. Requires an admitted build and an untruncated owner/property path.",
        )
    )
    return rows
