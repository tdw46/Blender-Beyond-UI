"""Public-RNA identities for structs and collection-owned properties."""


def identity(owner):
    if owner is None:
        raise ReferenceError("Property owner is unavailable")
    data = getattr(owner, "id_data", None)
    data_id = data.as_pointer() if data is not None else None
    pointer = getattr(owner, "as_pointer", None)
    if callable(pointer):
        return data_id, pointer()
    # Collection wrappers (e.g. Armature.bones.active) have no as_pointer.
    # Their containing ID and RNA path are the public stable owner identity.
    if data is None:
        raise ReferenceError("Collection property requires an owning ID")
    path = owner.path_from_id()
    try:
        current = data.path_resolve(path)
    except ValueError as error:
        raise ReferenceError("Collection property owner is unavailable") from error
    if current.bl_rna.identifier != owner.bl_rna.identifier:
        raise ReferenceError("Collection property owner changed")
    return data_id, path, owner.bl_rna.identifier


def readonly(owner, name):
    query = getattr(owner, "is_property_readonly", None)
    return query(name) if callable(query) else owner.bl_rna.properties[name].is_readonly
