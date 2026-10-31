"""Exact-ID asset actions with complete metadata rollback and no native button."""

from .context_menu import Entry
from .rna_owner import identity


def entries(resolve, context):
    import bpy

    item = resolve()
    if not isinstance(item, bpy.types.ID):
        return ()
    key = identity(item)

    def current():
        value = resolve()
        if identity(value) != key:
            raise ReferenceError("Asset target changed")
        return value

    def supported(t, c, clear):
        value = current()
        if (
            not t.valid()
            or not t.editable()
            or t.commit is None
            or not value.is_editable
            or value.library
        ):
            return False
        if not all(
            callable(getattr(value, name, None))
            for name in ("asset_mark", "asset_clear")
        ):
            return False
        # Prefer the single-ID poll; older builds use the explicit ID context.
        mark = getattr(bpy.ops.asset, "mark_single", None)
        try:
            mark.get_rna_type()
        except (AttributeError, RuntimeError):
            mark = bpy.ops.asset.mark
        with c.temp_override(id=value, selected_ids=[value]):
            if not mark.poll():
                return False
        if clear and value.bl_rna.properties["asset_data"].is_readonly:
            return False  # Full metadata restoration requires the public copy setter.
        return bool(value.asset_data) == clear

    def execute(t, c, clear):
        if not supported(t, c, clear):
            raise ReferenceError("Asset action is unavailable")
        value = current()
        fake = value.use_fake_user
        backup = None
        try:
            if clear:
                backup = bpy.data.objects.new("Beyond UI asset transaction", None)
                backup.asset_mark()
                backup.asset_data = value.asset_data
                value.asset_clear()
            else:
                value.asset_mark()
            if bool(value.asset_data) == clear:
                raise RuntimeError("Blender did not apply the asset action")
            t.commit("ASSET_CLEAR" if clear else "ASSET_MARK")
        except Exception:
            if clear:
                if value.asset_data is None:
                    value.asset_mark()
                if backup is not None:
                    value.asset_data = backup.asset_data
            else:
                value.asset_clear()
            value.use_fake_user = fake
            raise
        finally:
            if backup is not None:
                bpy.data.objects.remove(backup)
        if not clear and not bpy.app.background:
            preview = getattr(value, "asset_generate_preview", None)
            if callable(preview):
                preview()

    return tuple(
        Entry(
            "ASSET_CLEAR" if clear else "ASSET_MARK",
            "Clear Asset" if clear else "Mark as Asset",
            lambda t, c, remove=clear: execute(t, c, remove),
            lambda t, c, remove=clear: supported(t, c, remove),
            divider=not clear,
        )
        for clear in (False, True)
    )
