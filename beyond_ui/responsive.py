"""Retained host-width style breakpoints. No binding or draw-time mutations."""

_ALLOWED = {'padding','margin','gap','width','height','min_width','max_width','min_height','max_height',
 'align','flex_grow','flex_wrap','align_items','display','font_size','font_weight','icon_size','text_align',
 'label_width','label_position','wrap','line_height','text_inset'}
_MISSING=object()

def normalize_rules(rules):
    from .style_api import normalize
    if not isinstance(rules,(list,tuple)) or len(rules)>16:
        raise ValueError('responsive requires at most 16 breakpoint rules')
    result=[]
    for rule in rules:
        if not isinstance(rule,dict) or set(rule)-{'min_width','max_width','style','when'}:
            raise ValueError('Breakpoint uses min_width, max_width, when and style')
        low,high=rule.get('min_width',0),rule.get('max_width',4096)
        from math import isfinite
        if not all(isinstance(n,(float,int)) and isfinite(n) for n in (low,high)) or not 0<=low<=high<=4096:
            raise ValueError('Invalid breakpoint width range')
        when=rule.get('when')
        if when is not None and (not isinstance(when,str) or not when or '.' not in when):
            raise ValueError('when requires a named fit state, for example planes.compact')
        values=rule.get('style',{})
        if not isinstance(values,dict) or values.keys()-_ALLOWED:raise ValueError('Unsupported responsive presentation option')
        result.append({'min_width':low,'max_width':high,'style':normalize(values),'when':when})
    return tuple(result)

def restore(canvas):
    for target in reversed(getattr(canvas,'_responsive_targets',())):
        for node,values in reversed(target.options.pop('_responsive_restore',[])):
            for key,value in values.items():
                if value is _MISSING:node.options.pop(key,None)
                else:node.options[key]=value
        target.options.pop('_responsive_match',None)

def resolve(canvas,width,fit_states=None):
    from .style_api import _LAYOUT,_leaves,apply_control
    targets=getattr(canvas,'_responsive_targets',())
    states=getattr(canvas,'_responsive_fit_states',{}) if fit_states is None else fit_states
    canvas._responsive_fit_states=states
    matches=[tuple(i for i,r in enumerate(t.options.get('_responsive_rules',()))
                   if r['min_width']<=width<=r['max_width'] and
                   (r.get('when') is None or r['when'] in states)) for t in targets]
    if all(t.options.get('_responsive_match')==m for t,m in zip(targets,matches)):
        return False
    # Unwind child overrides before parents, then replay in author order.
    # This preserves both baselines when nested rules touch the same control.
    restore(canvas)
    for target,matched in zip(targets,matches):
        rules=target.options.get('_responsive_rules',())
        target.options['_responsive_match']=matched
        values={k:v for i in matched for k,v in rules[i]['style'].items()}
        geometry={k:v for k,v in values.items() if k in _LAYOUT}
        visual={k:v for k,v in values.items() if k not in _LAYOUT}
        saved=[]
        if geometry:
            keys=set(geometry)|{'_inline_geometry','alignment'}
            saved.append((target,{k:target.options.get(k,_MISSING) for k in keys}))
            target.options.update(geometry);target.options['_inline_geometry']=True
            if 'align' in geometry:target.options['alignment']=geometry['align']
        if visual:
            for control in _leaves(target):
                keys=set(visual)|{'_inline_style','_inline_sheet','numeric','text_alignment','wrap_text'}
                saved.append((control,{k:control.options.get(k,_MISSING) for k in keys}))
                apply_control(control,visual)
        target.options['_responsive_restore']=saved
        if values.get('display')=='none':
            hidden={id(c) for c in _leaves(target)}
            if any(c is not None and id(c) in hidden for c in (canvas.active,canvas.widget_capture,canvas.keyboard_focus,canvas.context_focus,(canvas.overlay or {}).get('owner'))):
                canvas.cancel()
    return True


def fit_states(canvas,plan):
    """Select stages from unwrapped minimum sizes at the actual nested width.

    Called once during layout preflight, never during painting. Shared names
    synchronize compact styling across several related control groups.
    """
    stages={}
    for profile in getattr(canvas,'_responsive_fit_profiles',()):
        row=profile['row']
        if row.options.get('display')=='none':continue
        _,right,_,left=plan.insets(row)
        available=max(0,row.rect[2]-left-right)
        pad,values,reset=profile['parts']
        gap=plan.gap(row)
        pair=plan.minimum(pad)+plan.minimum(values)+gap
        full=pair+plan.minimum(reset)+gap
        stage=2 if available+1e-6<pair else 1 if available+1e-6<full else 0
        name=profile['name'];stages[name]=max(stage,stages.get(name,0))
    return {name+'.'+('header' if stage==1 else 'compact'):True
            for name,stage in stages.items() if stage}
