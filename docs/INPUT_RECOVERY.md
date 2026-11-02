# Panel input recovery

On 2026-11-02, Uraraka's CamKeys panels still painted but no longer accepted
input. The live log showed a consumer operator refusing removal of the body
billboard group, because that group contains the remaining bones. Its ERROR
report became a Python RuntimeError through `bpy.ops` and escaped BUI's shared
modal callback. Blender removed that input operator while BUI's running-window
set still contained the window. This was not a theme rendering failure.

The shared Runtime now contains panel event exceptions, records the latest error
and traceback per panel in `AddonUI.status['input_errors']`, reports the failure,
revokes the failed panel's interactions, and consumes the failed event without
replaying it elsewhere. The input service stays alive. It does not retry the
consumer operation or bypass its validation. Cleanup/report failures are also
contained. There is no polling watchdog or new idle timer.

Validation: 395 unit tests; Blender 5.2.2 windowed test
`tests/blender_input_recovery.py` invoked a real rejecting operator through the
custom button, then successfully toggled another property. The no-focus runner
recorded no activation or restoration. Uraraka's missing input handler was
restarted once after verifying its absence, without unregistering RNA or
interrupting BVT/CamKeys engines. Readback confirmed one BUI input handler and
no new input/draw errors. The dirty scene was not saved.

The lifecycle fix uses the existing modal/report APIs, without a new version-only
API dependency. This batch's execution evidence is 5.2.2; it is not a claim of a
fresh 4.2 or cross-platform runtime qualification.
