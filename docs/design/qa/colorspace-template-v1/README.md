# Input color-space template

`Layout.template_colorspace_settings(data, property)` resolves the input settings
pointer and draws its name through the shared custom enum selector. It does not
require the settings pointer itself to be writable. The settings identity and
original owner remain guarded; deleting the image invalidates controls and menus.

Both installed Blender versions passed in disposable background processes.
No new renderer, resource allocation path, animation implementation or timer was
introduced. Existing enum glass, theme, search and context interactions are reused.
New template visual/reference acceptance and wider owner/version coverage remain
open; this is partial coverage, not a completed visual parity claim.

Exact 4.2/5.1/5.2 API and 5.2 Manual pages were requested but unavailable.
The archived official 4.2 interface_templates.cc implements this template by
resolving the pointer and drawing its name property; current behavior was checked
against real RNA in installed 5.1.2 and 5.2.2 runtimes.
