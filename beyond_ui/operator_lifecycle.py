"""Registration-only lifecycle policy; never inspect or poll live instances."""


def modal_registration_policy(operators):
    """Return in-place callback patches and protected nonmodal ancestors.

    RNA already registered the modal trampoline for existing modal classes, so
    Python methods can be replaced without freeing their RNA. A nonmodal base
    cannot gain that trampoline without also invalidating registered descendants.
    Include foreign descendants: ownership does not make their instances safe.
    """
    owned = set(operators)
    in_place = {cls for cls in owned if callable(getattr(cls, "modal", None))}
    protected, seen = set(), set()
    pending = list(owned)
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
        if getattr(cls, "is_registered", False) and callable(getattr(cls, "modal", None)):
            protected.update(parent for parent in cls.__mro__ if parent in owned)
    return in_place, protected - in_place
