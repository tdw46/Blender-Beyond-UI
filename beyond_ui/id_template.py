"""Custom data-block controls with input-time snapshots and host-owned undo."""

from dataclasses import dataclass, replace
from .bindings import Binding, rna_binding
from .context_menu import Entry, default_entries
from .pointer import PointerField
from .rna_owner import readonly


@dataclass(frozen=True)
class IDAction:
    """Host dispatcher request. Revalidate before a delayed/modal assignment."""

    operation: str
    operator: str
    context: object
    owner: object
    property: str
    selected: object
    valid: object
    assign: object


class IDTemplate:
    tab_limit = 256

    def __init__(self, layout, data, name, *, filter="ALL", operators=None):
        if filter not in {"ALL", "AVAILABLE"}:
            raise ValueError("ID filter must be ALL or AVAILABLE")
        self.layout, self.context = layout, layout.context
        self.canvas = layout.canvas
        binding = layout._binding(data, name)
        # Keep the original ID wrapper: an embedded PropertyGroup wrapper can
        # outlive ID removal. Reject the deleted ID before touching that RNA.
        resolve = binding.context.resolve
        owner_id = getattr(binding.context.owner(), "id_data", None)
        owner_key = owner_id.as_pointer() if owner_id is not None else None

        def owner():
            if owner_id is not None and owner_id.as_pointer() != owner_key:
                raise ReferenceError("Data-block template owner was removed")
            return resolve()

        binding = rna_binding(owner, name, commit=layout.commit, source=layout.source)
        policy = layout.pointer_sources(data, name) if layout.pointer_sources else None
        self.field = PointerField(binding, policy)
        if not self.field.stable_ids:
            raise ValueError("ID templates require a data-block pointer")
        original = self.field.policy
        self.operators = dict(operators or {})
        self.operator_classes = {}
        import bpy

        for action, idname in self.operators.items():
            category, op = idname.split(".", 1)
            self.operator_classes[action] = bpy.types.Operator.bl_rna_get_subclass_py(
                category.upper() + "_OT_" + op
            )
        self.scene = self.context.scene if self.context is not None else None
        self.scene_id = self.scene.as_pointer() if self.scene is not None else None

        def poll(owner, candidate):
            if not original.poll(owner, candidate):
                return False
            if filter == "AVAILABLE" and isinstance(candidate, bpy.types.Object):
                if (
                    self.scene is None
                    or self.context.scene.as_pointer() != self.scene_id
                ):
                    return False
                return any(
                    o.as_pointer() == candidate.as_pointer() for o in self.scene.objects
                )
            return True

        def revision():
            return (
                original.revision() if original.revision else None,
                self.context.scene.as_pointer()
                if self.context is not None and self.context.scene
                else None,
            )

        self.field.policy = replace(original, poll=poll, revision=revision)
        self.source = binding.context

        def freeze_link():
            token = self.token()

            def owner():
                if not self.matches(token):
                    raise ReferenceError("Selected data-block changed")
                return self.source.owner()

            return rna_binding(owner, name, commit=layout.commit, source=layout.source)

        self.binding = replace(binding, snapshot=freeze_link)

    def current(self):
        return getattr(self.source.owner(), self.source.name)

    def token(self):
        return self.field.identity(self.current()), self.field.revision()

    def matches(self, token):
        try:
            return self.source.valid() and self.token() == token
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def editable(self):
        try:
            return (
                self.layout.group._effective_enabled
                and self.binding.valid()
                and self.source.editable()
            )
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def field_binding(self, name):
        def valid():
            try:
                value = self.current()
                return (
                    self.editable()
                    and value is not None
                    and getattr(value, "is_editable", True)
                    and name in value.bl_rna.properties
                    and not readonly(value, name)
                )
            except (ReferenceError, RuntimeError, AttributeError):
                return False

        def freeze():
            token = self.token()

            def owner():
                if not self.matches(token):
                    raise ReferenceError("Selected data-block changed")
                return self.current()

            binding = rna_binding(
                owner, name, commit=self.layout.commit, source=self.layout.source
            )
            original_valid = binding.valid
            binding.valid = lambda: valid() and original_valid()
            return binding

        return Binding(
            lambda: getattr(self.current(), name),
            lambda v: freeze().write(v),
            valid,
            self.layout.commit,
            snapshot=freeze,
        )

    def users(self):
        try:
            value = self.current()
            return (
                max(0, value.users - int(value.use_fake_user))
                if value is not None
                else 0
            )
        except (ReferenceError, RuntimeError):
            return 0

    def fake_user_allowed(self):
        try:
            value = self.current()
            import bpy

            excluded = tuple(
                getattr(bpy.types, n)
                for n in ("Object", "Collection", "Scene", "Screen", "WorkSpace")
                if hasattr(bpy.types, n)
            )
            return (
                value is not None
                and not isinstance(value, excluded)
                and value.library is None
                and getattr(value, "asset_data", None) is None
            )
        except (ReferenceError, RuntimeError):
            return False

    def can_copy(self):
        try:
            import bpy

            value = self.current()
            return (
                self.editable()
                and value is not None
                and value.library is None
                and getattr(value, "override_library", None) is None
                and not getattr(value, "is_embedded_data", False)
                and not isinstance(
                    value,
                    (
                        bpy.types.Object,
                        bpy.types.Scene,
                        bpy.types.Screen,
                        bpy.types.WorkSpace,
                    ),
                )
                and callable(getattr(value, "copy", None))
                and callable(getattr(bpy.data, "batch_remove", None))
            )
        except (ReferenceError, RuntimeError, AttributeError):
            return False

    def duplicate(self, token):
        if not self.matches(token) or not self.can_copy():
            raise ReferenceError("Data-block is no longer eligible for copying")
        import bpy

        before = self.current()
        copied = before.copy()
        try:
            copied.use_fake_user = False
            if not self.matches(token):
                raise ReferenceError("Selected data-block changed while copying")
            self.field.assign(before, copied)
        except Exception:
            if copied.users == 0:
                bpy.data.batch_remove(ids=(copied,))
            raise

    def clear(self, token):
        if not self.matches(token):
            raise ReferenceError("Selected data-block changed")
        self.field.assign(self.current(), None)

    def operator_available(self, action):
        return self.editable() and bool(
            self.layout.id_actions or self.operator_classes.get(action)
        )

    def invoke(self, action, token):
        if not self.matches(token) or not self.operator_available(action):
            raise ReferenceError(
                "ID action requires a valid owner and an admitted dispatcher"
            )
        before = self.current()

        def valid():
            return self.matches(token) and self.editable()

        def assign(value):
            if not valid():
                raise ReferenceError("ID action owner or selection changed")
            self.field.assign(before, value)

        request = IDAction(
            action,
            self.operators[action],
            self.context,
            self.source.owner(),
            self.source.name,
            before,
            valid,
            assign,
        )
        if self.layout.id_actions is not None:
            return self.layout.id_actions(request)
        # Native active-button operators can target unrelated data in a custom UI.
        # Only registered Python operators receive this portable context route.
        import bpy

        category, name = request.operator.split(".", 1)
        cls = bpy.types.Operator.bl_rna_get_subclass_py(
            category.upper() + "_OT_" + name
        )
        if cls is not self.operator_classes[action]:
            raise ReferenceError("ID operator registration changed")
        from .hosts.menu_context import override
        from .context_extensions import operator

        values = {
            **self.layout._context_pointers,
            **self.layout._context_strings,
            "id": before,
            "template_id_ptr": request.owner,
            "template_id_prop": request.property,
        }
        with override(self.context, values):
            op = operator(request.operator)
            if not op.poll() or not valid():
                raise ReferenceError("ID operator poll or owner changed")
            return op(self.layout.operator_context)

    def attempt(self, action):
        try:
            result = action()
            self.canvas.menu_error = None
            return result
        except (ReferenceError, RuntimeError, ValueError, TypeError) as error:
            self.canvas.menu_error = str(error)
            return False

    def picker(self, canvas, control):
        widget = self.field.picker(canvas, control)
        show_hidden = bool(
            getattr(
                getattr(getattr(self.context, "preferences", None), "filepaths", None),
                "show_hidden_files_datablocks",
                False,
            )
        )
        widget.filter_item = (
            lambda item, query: show_hidden
            or query.startswith(".")
            or not item[1].startswith(".")
        )
        widget._filter()
        widget.title = control.label or "Data-blocks"
        return widget

    def label(self):
        return self.field.label()

    def property_entries(self, target, context):
        if callable(target.payload):
            rows = target.payload(target, context)
            provider = self.canvas.context_provider
            return (*rows, *(provider(target, context) if provider else ()))
        token = self.token()
        provider = self.canvas.context_provider or default_entries
        entries = list(provider(target, context))
        entries.insert(
            0,
            Entry(
                "ID_COPY",
                "Make Single User",
                lambda t, c: self.duplicate(token),
                lambda t, c: t.editable()
                and self.matches(token)
                and self.can_copy()
                and self.users() > 1,
            ),
        )
        if self.field.allow_none:
            entries.insert(1, self.field.clear_entry())
        return entries

    def button(self, group, key, label, action, enabled, *, label_get=None, width=80):
        def rows(target, context):
            token = self.token()
            provider = self.canvas.context_provider
            return (
                Entry(
                    key,
                    label,
                    lambda t, c: action(token),
                    lambda t, c: t.editable() and self.matches(token) and enabled(),
                ),
                *(provider(target, context) if provider else ()),
            )

        return group.button(
            key,
            label,
            lambda: self.attempt(lambda: action(self.token())),
            binding=self.binding,
            enabled=enabled,
            context_menu=rows,
            label_get=label_get,
            width=width,
        )

    def candidate(self, value, key, revision):
        if (
            not self.editable()
            or self.field.revision() != revision
            or self.field.identity(value) != key
        ):
            raise ReferenceError("ID tab owner or candidate changed")
        if not any(
            self.field.identity(v) == key for v in self.field.policy.items()
        ) or not self.field.policy.poll(self.source.owner(), value):
            raise ReferenceError("ID tab candidate is no longer eligible")
        return value

    def add_tabs(self, group):
        from itertools import islice

        values = tuple(islice(self.field.policy.items(), self.tab_limit + 1))
        if len(values) > self.tab_limit:
            raise ValueError(
                "ID tabs are limited to 256 candidates; use a searchable ID selector"
            )
        revision = self.field.revision()
        for value in values:
            if not isinstance(value, self.field.type) or not self.field.policy.poll(
                self.source.owner(), value
            ):
                continue
            key = value.as_pointer()

            def select(value=value, key=key):
                chosen = self.candidate(value, key, revision)
                self.field.assign(self.current(), chosen)

            def label(value=value):
                try:
                    return value.name
                except ReferenceError:
                    return "Unavailable"

            def valid(value=value, key=key):
                try:
                    return self.editable() and value.as_pointer() == key
                except (ReferenceError, RuntimeError):
                    return False

            def selected(key=key):
                try:
                    return self.field.identity(self.current()) == key
                except (ReferenceError, RuntimeError, AttributeError):
                    return False

            def rows(
                target,
                context,
                select=select,
                label=label,
                valid=valid,
                value=value,
                key=key,
            ):
                token = self.token()

                def current(t, c):
                    return t.editable() and self.matches(token) and valid()

                def copy(t, c):
                    if not current(t, c):
                        raise ReferenceError("ID tab selection changed")
                    self.candidate(value, key, revision)
                    c.window_manager.clipboard = label()

                def choose(t, c):
                    if not current(t, c):
                        raise ReferenceError("ID tab selection changed")
                    select()

                provider = self.canvas.context_provider
                return (
                    Entry("SELECT_ID", "Select Data-block", choose, current),
                    Entry("COPY_NAME", "Copy Name", copy, current),
                    *(provider(target, context) if provider else ()),
                )

            group.button(
                self.layout._key("id-tab"),
                label(),
                lambda select=select: self.attempt(select),
                binding=self.binding,
                enabled=valid,
                label_get=label,
                context_menu=rows,
                selected=selected,
            )
