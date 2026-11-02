# Billboard setup correction

Create Head / Body now repairs a body-only configuration. Enabling Separate
Billboards initializes missing mapped head/body groups before compiling assignments.
Existing authored branches remain intact; unmapped rigs retain manual bone selection.
The default remains off.

Actual custom-dialog confirmation, subsequent dialog cancellation, re-enable
idempotence and manual selection passed in disposable Uraraka copies on Blender
5.1.2 and 5.2.2. No focus activation was recorded. No separate full-application
hang was reproduced. The live body-only configuration was repaired without saving.

See [runtime and live evidence](report.json). No UI styling changed.
