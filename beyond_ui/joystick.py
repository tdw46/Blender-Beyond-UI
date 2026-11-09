"""Native-safe public 2D control; renderer-specific work lives in Layout."""
from .artwork import _custom


def joystick(layout,data,property=None,*,x=None,y=None,minimum=(-1.,-1.),maximum=(1.,1.),default=(0.,0.),size=104.,gap=14.,fields=True,label='',compact_below=None,compact_size=64.,compact_gap=10.,fit_group=None,fit_on_wrap=True,mode="POSITION",speed=.35,velocity_curve=(0.,0.),edge_speed_multiplier=1.,edge_start=.7, fine_speed_scale=.25,handle_radius=9.,base_radius=11.,stem_width=4.,show_stem=True):
    """Bind a size-2 FloatVectorProperty or x/y FloatProperty names on data."""
    if (property is not None and (not property or x is not None or y is not None)) or (property is None and (x is None or y is None)):
        raise ValueError('Supply a vector property OR both x and y properties')
    if _custom(layout):
        return layout.beyond_joystick(data,property,x=x,y=y,minimum=minimum,maximum=maximum,default=default,size=size,gap=gap,fields=fields,label=label,compact_below=compact_below,compact_size=compact_size,compact_gap=compact_gap,fit_group=fit_group,fit_on_wrap=fit_on_wrap,mode=mode,speed=speed,velocity_curve=velocity_curve,edge_speed_multiplier=edge_speed_multiplier,edge_start=edge_start,fine_speed_scale=fine_speed_scale,handle_radius=handle_radius,base_radius=base_radius,stem_width=stem_width,show_stem=show_stem)
    if label:layout.label(text=label)
    row=layout.row(align=True)
    if property:
        row.prop(data,property,index=0,text='X');row.prop(data,property,index=1,text='Y')
    else:
        row.prop(data,x,text='X');row.prop(data,y,text='Y')
    return row
