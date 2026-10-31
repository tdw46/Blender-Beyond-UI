"""No-op and component-owned rollback checks in a disposable scene."""

import bpy, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beyond_ui.bindings import rna_binding
from beyond_ui.context_menu import Target

try:
    owner = bpy.context.active_object
    receiver = bpy.data.objects.new("isolated receiver", None)
    bpy.context.collection.objects.link(receiver)
    receiver.select_set(True)
    owner.location = (3, 0, 5)
    receiver.location = (8, 0, 10)
    commits = []
    binding = rna_binding(
        lambda: owner, "location", index=1, commit=lambda a, b: commits.append((a, b))
    )
    source = binding.context
    target = Target("component", binding=binding)
    source.execute("RESET", target, bpy.context)
    source.execute("SELECTED", target, bpy.context)
    assert not commits and tuple(receiver.location) == (8, 0, 10)
    owner.location.y = 4

    def reject_reset(a, b):
        owner.location.x = 99
        raise RuntimeError("reject")

    source.commit = reject_reset
    try:
        source.execute("RESET", target, bpy.context)
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing failure")
    assert tuple(owner.location) == (99, 4, 5)

    def reject_selected(a, b):
        receiver.location.z = 77
        raise RuntimeError("reject")

    source.commit = reject_selected
    try:
        source.execute("SELECTED", target, bpy.context)
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing failure")
    assert tuple(receiver.location) == (8, 0, 77)
    source.commit = lambda a, b: commits.append((a, b))
    source.execute("SELECTED", target, bpy.context)
    assert tuple(receiver.location) == (8, 4, 77) and len(commits) == 1
    source.execute("SELECTED", target, bpy.context)
    assert len(commits) == 1
    result = dict(
        passed=True,
        version=bpy.app.version_string,
        checks=[
            "Unchanged component Reset/Copy to Selected skip host commits",
            "Failed transactions restore only the owned component",
            "Changed copy commits once and repeated copy is a no-op",
        ],
    )
except Exception:
    result = dict(passed=False, error=traceback.format_exc())
Path(os.environ["BEYOND_UI_TEST_RESULT"]).write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))
