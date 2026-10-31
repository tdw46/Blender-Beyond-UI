"""Native compatibility is opt-in and never conceals unexpected draw errors."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

from beyond_ui import AddonUI, UnsupportedControl
from beyond_ui.hosts.addon import Runtime
from beyond_ui.list_source import UnsafeListIdentity


class CompatibilityFallback(unittest.TestCase):
    def check_route(self, enabled, error):
        definition = type('Panel', (), {'draw': Mock()})
        runtime = Runtime(AddonUI('test_consumer', native_fallback=enabled), [definition], adopt=True)
        canvas, host, native = Mock(), Mock(), Mock()
        runtime.hosts[definition] = host
        runtime.canvases[definition] = {'key': ((), canvas)}
        instance, context = NS(), NS()
        runtime.draw_error(definition, 'key', native, error, context, instance)
        canvas.park.assert_called_once()
        host.invalidate.assert_called_once()
        self.assertFalse(runtime.canvases[definition])
        return runtime, definition

    def test_unsupported_only_routes_after_opt_in(self):
        runtime, definition = self.check_route(True, UnsafeListIdentity('stable keys required'))
        definition.draw.assert_called_once()
        self.assertEqual(runtime.fallbacks['Panel'], {'reason': 'stable keys required', 'custom': False})
        self.assertFalse(runtime.errors)

    def test_strict_default_keeps_unsupported_error(self):
        self.assertFalse(AddonUI('test_consumer').native_fallback)
        runtime, definition = self.check_route(False, UnsupportedControl('advanced curve'))
        definition.draw.assert_not_called()
        self.assertIn('Panel', runtime.errors)
        self.assertFalse(runtime.fallbacks)

    def test_unexpected_errors_are_never_hidden(self):
        runtime, definition = self.check_route(True, ValueError('bad consumer state'))
        definition.draw.assert_not_called()
        self.assertIn('bad consumer state', runtime.errors['Panel'])
        self.assertFalse(runtime.fallbacks)

    def test_dialog_failure_closes_host_and_respects_compatibility_policy(self):
        import sys
        from unittest.mock import patch
        from beyond_ui.invoke_routing import Router
        from beyond_ui.hosts.bridge import BridgeUnavailable

        operator_type = type('Operator', (), {})
        for enabled in (False, True):
            for error in (UnsupportedControl('brush curve'), ValueError('bad draw')):
                with self.subTest(enabled=enabled, error=type(error).__name__):
                    config = AddonUI('test_consumer', native_fallback=enabled)
                    router = Router(NS(owner='test_consumer', ui=config), [operator_type])
                    host = Mock()
                    router.host = lambda context: host
                    expected = BridgeUnavailable if enabled and isinstance(error, UnsupportedControl) else type(error)
                    with patch.dict(sys.modules, bpy=NS()), patch('beyond_ui.dialog.Dialog', side_effect=error):
                        with self.assertRaises(expected):
                            router.dialog(operator_type(), NS(), None, translate=False)
                    host.close.assert_called_once()
                    self.assertFalse(router.dialogs)
