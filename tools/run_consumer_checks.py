"""Portable, background-only consumer/admission checks using a fetched runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
record = Path(sys.argv[1]).resolve()
source = Path(os.environ['CAMKEYS_SOURCE']).resolve()
build = json.loads(record.read_text())
fixtures = [root/'tests/blender_portable_bridge.py',
            root/'tests/blender_transition_curves.py',
            root/'tests/blender_joystick_fit.py',
            source/'tests/blender_subject_size_ui.py',
            source/'tests/blender_subject_area.py',
            source/'tests/blender_asset_library.py']
for fixture in fixtures:
    subprocess.run([sys.executable, str(root/'tools/run_blender_tests.py'),
                    '--blender', build['blender'], '--fixture', str(fixture),
                    '--output', str(record.parent/'consumer'/fixture.stem)],
                   cwd=root, check=True)
