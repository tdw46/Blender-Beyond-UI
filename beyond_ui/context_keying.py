"""Exact-owner scene keying-set actions, prepared only on menu input."""

from .context_menu import Entry


def entries(source, target, context):
    scene = context.scene
    scene_id = scene.as_pointer()
    initial = scene.keying_sets_all.active
    initial_id = initial.as_pointer() if initial is not None else 0

    def active():
        if context.scene.as_pointer() != scene_id:
            raise ReferenceError("Keying-set scene changed")
        current = scene.keying_sets_all.active
        if (current.as_pointer() if current is not None else 0) != initial_id:
            raise ReferenceError("Active keying set changed")
        return current

    def paths(ks, binding):
        if ks is None:
            return ()
        owner = binding.owner()
        path = binding.property_path(owner)
        return tuple(
            p
            for p in ks.paths
            if p.id == owner.id_data
            and p.data_path == path
            and (
                binding.index is None
                or p.use_entire_array
                or p.array_index == binding.index
            )
        )

    def enabled(t, c, binding, remove):
        if (
            c.scene.as_pointer() != scene_id
            or not t.editable()
            or t.commit is None
            or not binding.valid()
        ):
            return False
        ks = active()
        if not getattr(scene, "is_editable", True) or (
            ks is not None and not ks.is_path_absolute
        ):
            return False
        return bool(paths(ks, binding)) if remove else True

    def execute(t, c, binding, remove):
        if not enabled(t, c, binding, remove):
            raise ReferenceError("Keying-set action is unavailable")
        ks = active()
        created = ks is None
        old_index = scene.keying_sets.active_index
        if created:
            ks = scene.keying_sets.new(
                idname="ButtonKeyingSet", name="Button Keying Set"
            )
            scene.keying_sets.active = ks
        removed, added = [], None
        try:
            existing = paths(ks, binding)
            if remove:
                for p in existing:
                    removed.append(
                        (
                            p.id,
                            p.data_path,
                            -1 if p.use_entire_array else p.array_index,
                            p.group_method,
                            p.group,
                            {
                                n: getattr(p, n)
                                for n in (
                                    "use_insertkey_override_needed",
                                    "use_insertkey_override_visual",
                                    "use_insertkey_needed",
                                    "use_insertkey_visual",
                                )
                                if hasattr(p, n)
                            },
                        )
                    )
                    ks.paths.remove(p)
            elif not any(
                p.use_entire_array
                or binding.index is not None
                and p.array_index == binding.index
                for p in existing
            ):
                owner = binding.owner()
                added = ks.paths.add(
                    owner.id_data,
                    binding.property_path(owner),
                    index=-1 if binding.index is None else binding.index,
                )
            if added is not None or removed:
                t.commit("KEYING_REMOVE" if remove else "KEYING_ADD")
        except Exception:
            if added is not None:
                ks.paths.remove(added)
            for owner, path, index, method, group, flags in removed:
                restored = ks.paths.add(
                    owner, path, index=index, group_method=method, group_name=group
                )
                for name, value in flags.items():
                    setattr(restored, name, value)
            if created:
                import bpy

                # Public collection has no remove method. Remove only our newly
                # created empty set under its explicit scene, then restore active.
                with c.temp_override(scene=scene):
                    scene.keying_sets.active = ks
                    bpy.ops.anim.keying_set_remove()
                    scene.keying_sets.active_index = old_index
            raise

    rows = []
    for key, label, binding, remove in (
        ("KEYING_ADD", "Add to Keying Set", source, False),
        ("KEYING_REMOVE", "Remove from Keying Set", source, True),
    ):
        rows.append(
            Entry(
                key,
                label,
                lambda t, c, b=binding, r=remove: execute(t, c, b, r),
                lambda t, c, b=binding, r=remove: enabled(t, c, b, r),
                divider=not remove,
                tip="Uses the exact property in the active scene keying set; built-in sets are read-only.",
            )
        )
    if source.index is not None:
        whole = source.component(None)
        rows.insert(
            1,
            Entry(
                "KEYING_ADD_ALL",
                "Add All to Keying Set",
                lambda t, c: execute(t, c, whole, False),
                lambda t, c: enabled(t, c, whole, False),
            ),
        )
    return rows
