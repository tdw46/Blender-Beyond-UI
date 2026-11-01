"""Preserve macro child RNA types while adopting an already registered add-on.

Macro definitions retain pointers to their children's OperatorProperties types.
Unregister/re-register frees those types without rebuilding the macro definition.
This audit is registration-only and never accesses live operator instances.
"""


def protected_operators(operators):
    import bpy

    base = getattr(bpy.types, "Macro", None)
    if base is None:
        return set(), []
    by_name = {cls.bl_rna.identifier: cls for cls in operators}
    protected, references, seen = set(), [], set()
    pending = list(base.__subclasses__())
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
        # Macro lacks Operator.is_registered; registration installs its own RNA.
        if "bl_rna" not in cls.__dict__:
            continue
        name = cls.bl_idname
        if "_OT_" in name:
            prefix, suffix = name.split("_OT_", 1)
            name = prefix.lower() + "." + suffix
        try:
            prefix, suffix = name.split(".", 1)
            metadata = getattr(getattr(bpy.ops, prefix), suffix).get_rna_type()
            for prop in metadata.properties:
                child = by_name.get(prop.identifier)
                if child is not None and prop.type == "POINTER":
                    protected.add(child)
                    references.append(dict(macro=name, operator=child.bl_idname))
        except (AttributeError, ReferenceError, RuntimeError, ValueError) as error:
            # If a registered macro cannot be audited, keep RNA intact rather
            # than guessing that its pointers are independent of these types.
            protected.update(operators)
            references.append(dict(macro=name, reason=str(error), audit_failed=True))
    # Re-registering a base underneath a protected descendant is unsafe too.
    protected.update(
        parent
        for cls in tuple(protected)
        for parent in cls.__mro__
        if parent in operators
    )
    return protected, references
