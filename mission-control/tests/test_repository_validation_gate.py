"""Execute the actual required-gate script against upstream job outcomes."""
import os
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/repository-validation-gate.sh'


class RepositoryGateTests(unittest.TestCase):
    def run_gate(self, result):
        env = dict(os.environ)
        env.pop('VALIDATION_RESULT', None)
        if result is not None:
            env['VALIDATION_RESULT'] = result
        return subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True)

    def test_only_success_permits_gate(self):
        result = self.run_gate('success')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_nonpassing_or_missing_upstream_result_denies_gate(self):
        for value in ('failure', 'cancelled', 'skipped', 'neutral', 'pending', '', None,
                      'success\n', 'success; exit 0'):
            with self.subTest(value=value):
                result = self.run_gate(value)
                self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
