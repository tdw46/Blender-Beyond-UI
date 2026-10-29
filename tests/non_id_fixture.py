"""Consumer-owned rollback example for the fixture's Bone and Value-node policies."""

from contextlib import contextmanager


@contextmanager
def selection_transaction(owner, before, after):
    # These fixtures admit Bone/ShaderNodeValue only. Other native setters need
    # their own audited snapshot (e.g. output-node state is deliberately excluded).
    selected = [
        (item, name, getattr(item, name))
        for item in owner
        for name in ("select", "use_deform")
        if hasattr(item, name)
    ]
    try:
        yield
    except Exception:
        for item, name, value in selected:
            setattr(item, name, value)
        raise
