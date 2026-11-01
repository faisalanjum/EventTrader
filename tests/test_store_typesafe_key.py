import base64
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import stat
import tempfile
import unittest
from unittest.mock import patch

from dotenv import dotenv_values

from scripts import store_typesafe_key as setup


class StoreTypeSafeKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = Path(self.temp.name) / '.env'
        self.original = '# Keep this comment\nOTHER_API_KEY=existing-value\n'
        self.env.write_text(self.original)
        self.key = 'dummy-typesafe-key-not-a-real-credential'
        self.secrets = {ns: {'OTHER_API_KEY': 'ZXhpc3Rpbmc='}
                        for ns in setup.NAMESPACES}
        self.calls = []

    def fake_run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        self.assertNotIn(self.key, ' '.join(command))
        ns = command[command.index('-n') + 1]
        if 'patch' in command:
            self.assertIn('--patch-file=/dev/stdin', command)
            update = json.loads(kwargs['input'])
            self.assertEqual(set(update['data']), {'TYPESAFE_API_KEY'})
            self.secrets[ns].update(update['data'])
        result = type('Result', (), {})()
        result.returncode = 0
        result.stdout = json.dumps({'data': self.secrets[ns]})
        result.stderr = ''
        return result

    def test_saves_only_requested_key_and_does_not_print_it(self):
        output = io.StringIO()
        with patch.object(setup.subprocess, 'run', side_effect=self.fake_run):
            with contextlib.redirect_stdout(output):
                setup.store_key(self.key, self.env)
        self.assertTrue(self.env.read_text().startswith(self.original))
        self.assertEqual(dotenv_values(self.env)['TYPESAFE_API_KEY'], self.key)
        self.assertEqual(stat.S_IMODE(self.env.stat().st_mode), 0o600)
        encoded = base64.b64encode(self.key.encode()).decode()
        for values in self.secrets.values():
            self.assertEqual(values, {'OTHER_API_KEY': 'ZXhpc3Rpbmc=',
                                      'TYPESAFE_API_KEY': encoded})
        self.assertNotIn(self.key, output.getvalue())
        self.assertNotIn(encoded, output.getvalue())
        self.assertFalse(any('rollout' in command for command, _ in self.calls))

    def test_replaces_existing_value_without_duplicate_entries(self):
        self.env.write_text(self.original + 'TYPESAFE_API_KEY=old-value\n')
        with patch.object(setup.subprocess, 'run', side_effect=self.fake_run):
            with contextlib.redirect_stdout(io.StringIO()):
                setup.store_key(self.key, self.env)
        self.assertEqual(self.env.read_text().count('TYPESAFE_API_KEY='), 1)
        self.assertEqual(dotenv_values(self.env)['OTHER_API_KEY'], 'existing-value')

    def test_unreachable_cluster_leaves_local_file_unchanged(self):
        with patch.object(setup.subprocess, 'run', side_effect=OSError('offline')):
            with self.assertRaises(setup.SetupError):
                setup.store_key(self.key, self.env)
        self.assertEqual(self.env.read_text(), self.original)

    def test_cluster_error_does_not_repeat_sensitive_stderr(self):
        def fail_second_patch(command, **kwargs):
            if 'patch' in command and 'mcp-services' in command:
                return type('Result', (), {'returncode': 1, 'stdout': '',
                                          'stderr': self.key})()
            return self.fake_run(command, **kwargs)
        with patch.object(setup.subprocess, 'run', side_effect=fail_second_patch):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(setup.SetupError) as error:
                    setup.store_key(self.key, self.env)
        self.assertNotIn(self.key, str(error.exception))
        self.assertIn('mcp-services', str(error.exception))
        self.assertEqual(dotenv_values(self.env)['TYPESAFE_API_KEY'], self.key)
        self.assertNotIn('TYPESAFE_API_KEY', self.secrets['mcp-services'])

    def test_empty_or_multiline_values_are_rejected_before_any_write(self):
        for value in ['', ' ', 'abc\ndef', 'abc def']:
            with self.subTest(value=value), patch.object(setup.subprocess, 'run') as run:
                with self.assertRaises(setup.SetupError):
                    setup.store_key(value, self.env)
                run.assert_not_called()
                self.assertEqual(self.env.read_text(), self.original)

    def test_shared_key_loader_exposes_typesafe_environment_variable(self):
        with patch.dict(os.environ, {'TYPESAFE_API_KEY': self.key}):
            values = runpy.run_path(str(Path(__file__).resolve().parents[1]
                                       / 'eventtrader' / 'keys.py'))
        self.assertEqual(values['TYPESAFE_API_KEY'], self.key)


if __name__ == '__main__':
    unittest.main()
