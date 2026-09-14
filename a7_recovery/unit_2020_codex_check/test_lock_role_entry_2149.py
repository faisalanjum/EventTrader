"""The real entry must check admission before entering the candidate role."""
import ast
import types
import unittest
from pathlib import Path


class RoleEntry(unittest.TestCase):
    def entry(self, allowed=True):
        calls = []
        role = {'current': 'tested'}

        def problems():
            calls.append(('admission', role['current']))
            return [] if allowed and role['current'] == 'tested' else ['not independent']

        def scoped(action):
            role['current'] = 'key'
            try:
                return action(None, None)
            finally:
                role['current'] = 'tested'

        def lock(*_):
            calls.append(('lock', role['current']))
            return 'done'

        path = Path(__file__).with_name('lock_current_key_2149.py')
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'main')
        ns = {'E': types.SimpleNamespace(SK=types.SimpleNamespace(role_problems=problems),
                                        with_prepared_inputs=scoped), 'lock': lock}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
        return ns['main'], calls, role

    def test_admit_then_bind(self):
        main, calls, role = self.entry()
        self.assertEqual(main(), 'done')
        self.assertEqual(calls, [('admission', 'tested'), ('lock', 'key')])
        self.assertEqual(role['current'], 'tested')

    def test_disallowed_role_never_enters_lock(self):
        positive, _, _ = self.entry()
        self.assertEqual(positive(), 'done')
        main, calls, role = self.entry(False)
        with self.assertRaisesRegex(AssertionError, 'not independent'):
            main()
        self.assertEqual(calls, [('admission', 'tested')])
        self.assertEqual(role['current'], 'tested')


if __name__ == '__main__':
    unittest.main(verbosity=2)
