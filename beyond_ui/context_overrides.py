"""Reversible property override rules; never create or destroy ID hierarchies."""

from .context_menu import Entry


def state(source):
    owner = source.owner()
    data = owner.id_data
    override = getattr(data, "override_library", None)
    if (
        override is None
        or override.reference is None
        or override.is_system_override
        or not data.is_editable
        or not source.editable()
        or not owner.is_property_overridable_library(source.name)
        or source.metadata().type not in {"FLOAT", "INT", "BOOLEAN", "ENUM", "STRING"}
    ):
        return None
    props = override.properties
    if not all(callable(getattr(props, n, None)) for n in ("add", "remove")):
        return None
    path = source.property_path()
    prop = next((p for p in props if p.rna_path == path), None)
    rules = []
    for op in prop.operations if prop else ():
        # Public RNA cannot reproduce mandatory flags or arbitrary collection
        # rules. Leave those to the host, rather than corrupting their meaning.
        if (
            op.operation != "REPLACE"
            or op.flag
            or op.subitem_local_name
            or op.subitem_reference_name
            or op.subitem_local_id
            or op.subitem_reference_id
            or op.subitem_local_index != op.subitem_reference_index
        ):
            return None
        rules.append(op.subitem_local_index)
    meta = source.metadata()
    size = meta.array_length if getattr(meta, "is_array", False) else 0
    if any(i < -1 or i >= size for i in rules if i != -1):
        return None
    reference = override.reference.path_resolve(path)
    reference = tuple(reference) if getattr(meta, "is_array", False) else reference
    signature = (
        override.as_pointer(),
        override.reference.as_pointer(),
        path,
        tuple(rules),
    )
    return props, prop, tuple(rules), reference, size, signature


def write_rules(props, path, rules):
    prop = next((p for p in props if p.rna_path == path), None)
    if prop is not None:
        props.remove(prop)
    if rules:
        prop = props.add(path)
        for index in rules:
            prop.operations.add(
                "REPLACE", subitem_reference_index=index, subitem_local_index=index
            )


def entries(source):
    try:
        initial = state(source)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return ()
    if initial is None:
        return ()
    signature = initial[-1]

    def available(t, binding, remove):
        if not t.valid() or not t.editable() or t.commit is None or not binding.valid():
            return False
        current = state(binding)
        if current is None or current[-1] != signature:
            return False
        index = -1 if binding.index is None else binding.index
        exists = (
            bool(current[2])
            if index == -1
            else (-1 in current[2] or index in current[2])
        )
        if remove:
            return exists
        if index == -1 and current[4]:
            return -1 not in current[2] and set(current[2]) != set(range(current[4]))
        return not exists

    def execute(t, c, binding, remove):
        if not available(t, binding, remove):
            raise ReferenceError("Library override property changed or is unavailable")
        props, prop, rules, reference, size, current_signature = state(binding)
        path = current_signature[2]
        index = -1 if binding.index is None else binding.index
        new_rules = list(rules)
        if remove:
            if index == -1:
                new_rules = []
            elif -1 in new_rules:
                new_rules = [i for i in range(size) if i != index]
            else:
                new_rules.remove(index)
        else:
            new_rules = [-1] if index == -1 else [*new_rules, index]
        owner = binding.owner()
        before = binding.read()
        try:
            write_rules(props, path, new_rules)
            if remove:
                binding.assign(owner, reference)
            binding.update()
            t.commit("OVERRIDE_REMOVE" if remove else "OVERRIDE_ADD")
        except Exception:
            write_rules(props, path, rules)
            if remove and binding.valid():
                binding.assign(owner, before)
            binding.update()
            raise

    rows = []
    choices = [(source, "", "")]
    if source.index is not None:
        choices.append((source.component(None), "_ALL", " (All Components)"))
    for binding, suffix, label_suffix in choices:
        for remove, key, label in (
            (False, "OVERRIDE_ADD", "Define Library Override"),
            (True, "OVERRIDE_REMOVE", "Remove Library Override"),
        ):
            rows.append(
                Entry(
                    key + suffix,
                    label + label_suffix,
                    lambda t, c, b=binding, r=remove: execute(t, c, b, r),
                    lambda t, c, b=binding, r=remove: available(t, b, r),
                    divider=not rows,
                    tip="Exact property rule; removing restores its linked value. Requires host undo.",
                )
            )
    return rows
