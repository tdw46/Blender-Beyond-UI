"""Consumer action exceptions cannot kill a shared panel input service."""
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from beyond_ui.hosts.addon import Runtime


class InputRecovery(TestCase):
    def runtime(self):
        definition = type('TestPanel', (), {})
        host = NS(event=Mock(), invalidate=Mock(), records={1: object()})
        runtime = Runtime(NS(owner='test.recovery'), ())
        runtime.hosts = {definition: host}
        runtime.canvases = {definition: {1: object()}}
        runtime.redraw = Mock()
        runtime.running.add(123)
        return runtime, definition, host

    def test_refused_action_is_consumed_then_input_continues(self):
        runtime, definition, host = self.runtime()
        host.event.side_effect = [RuntimeError('Body cannot be removed'), False, True]
        operator = NS(report=Mock())
        with patch('traceback.print_exc'):
            self.assertEqual(runtime.dispatch_event(operator, None, NS(type='LEFTMOUSE')), {'RUNNING_MODAL'})
        host.invalidate.assert_called_once()
        self.assertFalse(runtime.canvases[definition])
        self.assertIn('Body cannot be removed', runtime.input_errors['TestPanel']['error'])
        self.assertEqual(runtime.running, {123})
        self.assertEqual(runtime.dispatch_event(operator, None, NS(type='MOUSEMOVE')), {'PASS_THROUGH'})
        self.assertEqual(runtime.dispatch_event(operator, None, NS(type='LEFTMOUSE')), {'RUNNING_MODAL'})
        operator.report.assert_called_once()

    def test_stale_cleanup_and_report_failure_do_not_escape(self):
        runtime, _, host = self.runtime()
        host.event.side_effect = ReferenceError('Owner removed')
        host.invalidate.side_effect = ReferenceError('Edit owner removed')
        operator = NS(report=Mock(side_effect=RuntimeError('Report failed')))
        with patch('traceback.print_exc'):
            self.assertEqual(runtime.dispatch_event(operator, None, NS(type='LEFTMOUSE')), {'RUNNING_MODAL'})
        self.assertFalse(host.records)
        self.assertIn('cleanup_error', runtime.input_errors['TestPanel'])
