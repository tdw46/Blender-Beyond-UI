"""Transactional selected-owner driver copies through capability-gated public RNA."""

from .context_menu import Entry
from .decorator import channel_collections


def plan(source, target, context):
    import bpy

    if (
        not source.valid()
        or not target.valid()
        or not target.editable()
        or target.commit is None
    ):
        return ()
    functions = bpy.types.AnimDataDrivers.bl_rna.functions
    if any(name not in functions for name in ("from_existing", "new", "remove")):
        return ()  # Unsupported runtimes retain existing context actions.
    owner = source.owner()
    path = source.property_path(owner)
    _, drivers = channel_collections(owner.id_data)
    curves = tuple(
        f
        for f in drivers or ()
        if f.data_path == path
        and (source.index is None or f.array_index == source.index)
    )
    if not curves:
        return ()
    work = []
    for candidate in source.selected(context):
        if not source.metadata(candidate).is_animatable:
            continue
        data = candidate.id_data
        if not callable(getattr(data, "animation_data_create", None)):
            continue
        destination = source.property_path(candidate)
        collections, _ = channel_collections(data)
        keyed = {
            f.array_index for c in collections for f in c if f.data_path == destination
        }
        for curve in curves:
            if curve.array_index not in keyed:
                work.append((data, destination, curve.array_index, curve))
    return tuple(work)


def copy_selected(source, target, context):
    import bpy

    work = plan(
        source, target, context
    )  # Current selection and channels, not menu snapshots.
    if not work:
        return
    staging = bpy.data.objects.new("Beyond UI driver transaction", None)
    staged = staging.animation_data_create().drivers
    receipts, created = [], {}
    try:
        # Freeze every source before touching destinations (including same-ID bones).
        templates = {}
        for _, _, _, curve in work:
            key = curve.as_pointer()
            if key not in templates:
                templates[key] = staged.from_existing(src_driver=curve)
        for data, path, index, curve in work:
            key = data.as_pointer()
            if data.animation_data is None:
                created[key] = data
            drivers = data.animation_data_create().drivers
            old = drivers.find(path, index=index)
            backup = staged.from_existing(src_driver=old) if old else None
            receipt = [data, path, index, backup, None, False]
            receipts.append(receipt)
            if old:
                drivers.remove(old)
                receipt[5] = True
            else:
                # from_existing copies the FCurve but does not tag relations.
                # Public new/remove does, without private ABI calls or a clipboard.
                placeholder = drivers.new(path, index=index)
                drivers.remove(placeholder)
            replacement = drivers.from_existing(
                src_driver=templates[curve.as_pointer()]
            )
            receipt[4] = replacement
            replacement.data_path, replacement.array_index = path, index
            data.update_tag()
        target.commit("COPY_DRIVERS_SELECTED")
    except Exception:
        for data, path, index, backup, replacement, removed in reversed(receipts):
            drivers = data.animation_data.drivers
            if replacement is not None:
                drivers.remove(replacement)
            if removed:
                restored = drivers.from_existing(src_driver=backup)
                restored.data_path, restored.array_index = path, index
            data.update_tag()
        for data in created.values():
            animation = data.animation_data
            if animation is not None and not (
                animation.action or animation.drivers or animation.nla_tracks
            ):
                data.animation_data_clear()
        raise
    finally:
        bpy.data.objects.remove(staging)


def entries(source):
    rows = []
    choices = [
        (
            source,
            "COPY_DRIVERS_SELECTED",
            "Copy Driver to Selected"
            if source.index is not None
            or not getattr(source.metadata(), "is_array", False)
            else "Copy Drivers to Selected",
        )
    ]
    if source.index is not None:
        choices.append(
            (
                source.component(None),
                "COPY_DRIVERS_SELECTED_ALL",
                "Copy All Drivers to Selected",
            )
        )
    for binding, key, label in choices:
        rows.append(
            Entry(
                key,
                label,
                lambda t, c, b=binding: copy_selected(b, t, c),
                lambda t, c, b=binding: bool(plan(b, t, c)),
                tip="Copy complete drivers to compatible selected owners; animated destination channels are skipped. Requires host undo.",
            )
        )
    return rows
