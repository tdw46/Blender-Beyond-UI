"""Native-safe wizard composition. Consumers own validation, state and actions."""
from .artwork import _custom, header
from .style_api import style


def wizard(layout, token, *, title, subtitle='', icon=None, step=1, steps=3,
           direction=1, padding=8, gap=7, title_size=20, brand='',
           title_align='left', help_operator=None, help_properties=None, completed=False):
    if not 1 <= step <= steps:
        raise ValueError('Wizard progress must be within its steps')
    if _custom(layout):
        layout.beyond_page(token, direction=direction)
    body = layout.column(align=True)
    style(body, scope='group', padding=padding, gap=gap)
    if brand:
        brand_row = body.row(align=True)
        style(brand_row, scope='group', gap=6, align_items='center')
        brand_content = brand_row.column(align=True)
        style(brand_content, scope='group', flex_grow=1)
        header(brand_content, brand, icon=icon, size=24, gap=6, padding=0,
               title_style={'font_size':15,'line_height':20})
        if help_operator:
            help_cell = brand_row.column(align=True)
            style(help_cell, scope='group', width=24)
            help_button(help_cell, help_operator, **(help_properties or {}))
    if _custom(body):
        body.beyond_progress(step, steps)
    else:
        body.label(text=f"{step} / {steps}", translate=False)
    if completed:
        status = body.row(align=True)
        style(status, scope='group', align='CENTER')
        badge(status, '', icon='CHECKMARK', width=28, height=28, radius=14,
              fill_alpha=.95, text_role='input', padding=6, icon_size=18)
    header(body, title, subtitle=subtitle, icon=None if brand else icon,
           size=24, gap=10, padding=0,
           title_style={'font_size':title_size,'line_height':24,'text_align':title_align},
           subtitle_style={'font_size':11,'line_height':17})
    return body


def help_button(layout, operator, *, text='', icon='QUESTION', size=24, icon_size=18, **properties):
    """Compact help accessory with native operator metadata/context support."""
    button = layout.operator(operator, text=text, icon=icon, emboss=bool(text))
    for name, value in properties.items():
        setattr(button, name, value)
    style(layout, **({'width':size, 'height':size, 'icon_size':icon_size} if not text else {'height':28}))
    return button


def help_row(layout, operator, *, text, icon='INFO', artwork=None, height=30,
             radius=9, font_size=12.5, icon_size=18, help_size=24, **properties):
    """A leading feature action and trailing help accessory on one shared surface.

    Both buttons retain the consumer operator metadata and context actions.
    Geometry is logical and configurable; ordinary native layouts remain usable.
    """
    box = layout.column(align=True) if _custom(layout) else layout.box()
    style(box, scope='group', padding=(0, 6), surface='field', surface_radius=radius, gap=0)
    row = box.row(align=True)
    style(row, scope='group', gap=4, align_items='center')
    action = row.column(align=True)
    style(action, scope='group', flex_grow=1)
    button = action.operator(operator, text=text, icon=icon, emboss=False)
    for name, value in properties.items():
        setattr(button, name, value)
    style(action, height=height, font_size=font_size, icon_size=icon_size,
          text_align='left', text_inset=6, **({'icon': artwork} if artwork else {}))
    accessory = row.column(align=True)
    style(accessory, scope='group', width=help_size)
    help_button(accessory, operator, size=help_size, icon_size=18, **properties)
    return button


def badge(layout, text, **options):
    """Semantic, read-only status chip; uses active host theme roles."""
    if _custom(layout):
        layout.beyond_badge(text, **options)
    else:
        layout.label(text=text, icon=options.get('icon','CHECKMARK'), translate=options.get('translate',True), text_ctxt=options.get('text_ctxt',''))


def choice(layout, data, property, value, *, library=None, media_key=None,
           title='', description='', **options):
    """Entire card is an enum button, preserving its exact RNA context menu."""
    if _custom(layout):
        layout.beyond_choice(data, property, value, library=library, media_key=media_key,
                            title=title, description=description, **options)
        style(layout,height=options.get('height',94))
    else:
        box=layout.box()
        box.prop_enum(data,property,value,text=title)
        box.label(text=description)


def segmented(layout, data, property, *, icons=None, height=28):
    """Compact enum segments, using native expanded properties outside BUI."""
    if _custom(layout):
        return layout.beyond_segments(data, property, icons=icons, height=height)
    return layout.prop(data, property, text='', expand=True)
