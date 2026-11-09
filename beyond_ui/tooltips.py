"""Lazy native descriptions with the shared menu tooltip glass and spring policy."""
from .context_menu import Entry, Menu, Target


def developer_details(context):
    view = getattr(getattr(context, 'preferences', None), 'view', None)
    return bool(getattr(view, 'show_tooltips_python', False)
                or getattr(view, 'show_developer_ui', False))


def property_details(source, context):
    if not developer_details(context):
        return ''
    owner = source.owner()
    suffix = f'[{source.index}]' if getattr(source, 'index', None) is not None else ''
    join = '' if source.name.startswith('[') else '.'
    text = f'Python: {owner.bl_rna.identifier}{join}{source.name}{suffix}'
    try:
        text += '\nData Path: ' + source.paths()[1]
    except (AttributeError, ReferenceError, TypeError, ValueError):
        pass  # Operator properties can have RNA help without a persistent ID path.
    return text


def property_description(source, context, text=None):
    if text is None:
        meta = source.metadata()
        text = getattr(meta, 'description', '') or getattr(meta, 'name', '')
    return '\n'.join(part for part in (str(text or ''), property_details(source, context)) if part)


def operator_command(idname, properties):
    values = properties if isinstance(properties, dict) else vars(properties)
    return f"bpy.ops.{idname}({', '.join(f'{k}={v!r}' for k, v in values.items())})"


def operator_description(idname, properties, pointers, context):
    from .context_extensions import operator
    from .hosts.menu_context import override
    from types import SimpleNamespace
    import bpy

    info = operator(idname).get_rna_type()
    cls = bpy.types.Operator.bl_rna_get_subclass_py(info.identifier)
    description = getattr(cls, 'description', None)
    text = info.description or info.name
    if callable(description):
        defaults = {p.identifier: p.default for p in info.properties
                    if p.identifier != 'rna_type' and hasattr(p, 'default')}
        try:
            with override(context, pointers):
                text = description(context, SimpleNamespace(**{**defaults, **vars(properties)}))
            text = text or info.description or info.name
        except (AttributeError, TypeError, RuntimeError):
            pass  # A native-only OperatorProperties callback still has RNA help.
    if developer_details(context):
        text += '\nPython: ' + operator_command(idname, properties)
    return text


def description(control, context):
    value = control.options.get('tooltip')
    if value is not None:
        text = value(context) if callable(value) else value
    else:
        source = getattr(control.binding, 'context', None)
        if source is not None:
            meta = source.metadata()
            text = getattr(meta, 'description', '') or getattr(meta, 'name', '')
            if getattr(meta, 'type', '') == 'ENUM':
                current = getattr(source.owner(), source.name)
                item = meta.enum_items.get(current) if isinstance(current, str) else None
                if item and item.description:
                    text += '\n' + item.description
        else:
            model = (control.options.get('panel_model') or control.options.get('menu_model')
                     or control.options.get('operator_enum'))
            text = (getattr(getattr(model, 'cls', None), 'bl_description', '')
                    or getattr(model, 'description', '') or getattr(model, 'label', '')
                    or control.label)
    source = getattr(control.binding, 'context', None)
    if source is not None:
        text = property_description(source, context, text)
    elif value is None and developer_details(context):
        model = control.options.get('panel_model') or control.options.get('menu_model')
        if model is not None:
            text = str(text or '') + '\nPython: ' + model.name
    try:
        import bpy
        return bpy.app.translations.pgettext_tip(str(text or ''))
    except (ImportError, AttributeError):
        return str(text or '')


class ControlTip(Menu):
    def __init__(self, canvas, control, text, point, clip, context, measure):
        def valid():
            source = getattr(control.binding, 'context', None)
            return (canvas.visible and canvas.controls.get(control.key) is control
                    and (source.valid() if source is not None
                         else control.binding is None or control.binding.valid()))
        super().__init__(Target(control.key, valid=valid),
                         [Entry(control.key, control.label, tip=text)], point, clip,
                         context=context, measure=measure, on_tip=canvas._tooltip_wake)
        self.control = control
        self.developer_details = developer_details(context)
        self.visible_rows = lambda: ((0, control.rect, self.page.rows[0]),)
        canvas._bind_motion(self.motion, control)
        self.hover_tip(0, *point, context)


def hover(canvas, event, x, y, clip, context, measure):
    tip = getattr(canvas, '_control_tip', None)
    if event.type != 'MOUSEMOVE':
        if event.value in {'PRESS', 'DOUBLE_CLICK'} or event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE','TRACKPADPAN'}:
            hide(canvas)
        return
    if canvas.overlay or canvas.context_menu or canvas.edit or not canvas.visible:
        hide(canvas)
        return
    control = canvas.hit(x, y, clip, include_disabled=True)
    for composite in canvas._composites.values():
        if composite is not control:
            child = getattr(composite.options['widget'], 'active_child', None)
            if child is not None:
                hide(child)
    if control is not None and hasattr(control.options.get('widget'), 'route'):
        hide(canvas)
        return
    if control is None or control.kind in {'label', 'title', 'separator'}:
        hide(canvas)
        return
    clip = canvas._popup_clip or clip
    if (tip is not None and tip.control is control and tip.clip == clip
            and tip.developer_details == developer_details(context)):
        tip.hover_tip(0, x, y, context)
        return
    hide(canvas)
    try:
        text = description(control, context)
        if text:
            canvas._control_tip = ControlTip(canvas, control, text, (x, y), clip, context, measure)
    except (ReferenceError, RuntimeError, AttributeError, TypeError, ValueError):
        pass  # Removed RNA must never be read to show an obsolete description.


def hide(canvas):
    tip = getattr(canvas, '_control_tip', None)
    if tip is not None:
        canvas._control_tip = None
        tip.hide_tip()
        tip.motion.clear()


def hide_all(canvas):
    hide(canvas)
    widget = (canvas.overlay or {}).get('widget')
    if hasattr(widget, 'canvas'):
        hide_all(widget.canvas)
    for control in canvas._composites.values():
        child = getattr(control.options['widget'], 'active_child', None)
        if child is not None:
            hide_all(child)


def active(canvas):
    tip = getattr(canvas, '_control_tip', None)
    if tip is not None:
        return tip
    widget = (canvas.overlay or {}).get('widget')
    if hasattr(widget, 'canvas'):
        return active(widget.canvas)
    for control in canvas._composites.values():
        child = getattr(control.options['widget'], 'active_child', None)
        if child is not None:
            tip = active(child)
            if tip is not None:
                return tip
    return None
