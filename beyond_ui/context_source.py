"""Developer source locations from explicit authoring callables, never guessed UI."""

import inspect
from pathlib import Path
from .context_menu import Entry


def location(subject):
    # Code-object metadata avoids reading source files while opening/polling menus.
    if inspect.isclass(subject):
        subject = getattr(subject, "execute", None) or getattr(subject, "draw", None)
    code = getattr(subject, "__code__", None)
    if code is None or code.co_filename.startswith("<"):
        return None
    return code.co_filename, code.co_firstlineno


def entry(subject):
    def allowed(target, context):
        return (
            context.area is not None
            and getattr(context.preferences.view, "show_developer_ui", False)
            and location(subject) is not None
        )

    def execute(target, context):
        import bpy

        if not allowed(target, context):
            raise RuntimeError("Source location is unavailable")
        filename, line = location(subject)
        filename = str(Path(filename).resolve(strict=True))
        text = next((t for t in bpy.data.texts if t.filepath == filename), None)
        if text is None:
            text = bpy.data.texts.load(filename)
        context.area.type = "TEXT_EDITOR"
        context.area.spaces.active.text = text
        text.current_line_index = max(0, line - 1)

    return Entry(
        "SOURCE",
        "Edit Source",
        execute,
        allowed,
        tip="Open the host-supplied Python authoring function in the Text Editor.",
    )


def operator_subject(idname):
    import bpy
    from .context_extensions import operator

    info = operator(idname).get_rna_type()
    return bpy.types.Operator.bl_rna_get_subclass_py(info.identifier)
