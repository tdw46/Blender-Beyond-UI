"""Owner-relative external file actions, resolved only on menu input."""

import os
from .context_menu import Entry


def resolve(source):
    import bpy

    owner = source.owner()
    meta = owner.bl_rna.properties[source.name]
    if meta.type != "STRING" or meta.subtype not in {"FILE_PATH", "DIR_PATH"}:
        return None
    value = source.read()
    library = getattr(owner.id_data, "library", None)
    if not value or (value.startswith("//") and not library and not bpy.data.filepath):
        return None
    path = os.path.normpath(bpy.path.abspath(value, library=library))
    if not os.path.isabs(path) or not os.path.exists(path):
        return None
    return value, path, library.as_pointer() if library else 0


def open_path(path):
    import bpy

    result = bpy.ops.wm.path_open(filepath=path)
    if "FINISHED" not in result:
        raise RuntimeError("Blender could not open this path")


def entries(source):
    snapshot = resolve(source)
    if snapshot is None:
        return ()
    _, path, _ = snapshot
    directory = os.path.isdir(path)

    def valid(t, c):
        return t.valid() and source.valid() and resolve(source) == snapshot

    def execute(t, c, location):
        if not valid(t, c):
            raise ReferenceError("File property or owning library changed")
        destination = path if directory or not location else os.path.dirname(path)
        if not os.path.exists(destination):
            raise FileNotFoundError(destination)
        open_path(destination)

    rows = []
    if not directory:
        rows.append(
            Entry(
                "OPEN_FILE",
                "Open File Externally",
                lambda t, c: execute(t, c, False),
                valid,
                divider=True,
            )
        )
    rows.append(
        Entry(
            "OPEN_LOCATION",
            "Open Location Externally",
            lambda t, c: execute(t, c, True),
            valid,
            divider=directory,
        )
    )
    return rows
