"""Interface translation for labels owned by Beyond UI, including standalone tests."""
try:
    from bpy.app.translations import pgettext_iface as iface
except ImportError:
    def iface(message, context="*"):
        return message
