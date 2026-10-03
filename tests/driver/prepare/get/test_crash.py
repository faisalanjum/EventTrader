"""Kill the actual writer at save boundaries, then reopen its durable evidence."""
import gzip
import hashlib
import select
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from driver.prepare.get.acquire import acquire, read_package
from driver.prepare.get.campaign import Campaign
from tests.driver.prepare.get.test_acquire import ACCESSION, CIK, FORM, package


CHILD = r'''
import sys, time
from pathlib import Path
from unittest.mock import patch
from driver.prepare.get.campaign import Campaign
from driver.prepare.get.acquire import acquire
root, phase, accession, cik, form, sha = sys.argv[1:]
root = Path(root)
def pause(*args):
    print('saving', flush=True)
    time.sleep(30)
with Campaign(root / 'http', live=True, sender=lambda *a: (200, {}, b'exact'),
              sleep=lambda delay: None) as run:
    run.fetch('https://www.sec.gov/Archives/saved')
    if phase == 'during_receipt':
        run.db.create_function('pause', 0, pause)
        run.db.executescript('CREATE TRIGGER interrupt AFTER INSERT ON responses BEGIN SELECT pause(); END;')
        run.fetch('https://www.sec.gov/Archives/new')
    elif phase == 'after_receipt':
        run.fetch('https://www.sec.gov/Archives/new')
        pause()
    else:
        with patch('driver.prepare.get.acquire.os.rename', side_effect=pause):
            acquire(accession, cik, form, root / 'versions', package=root / 'original.gz', sha256=sha)
'''


class CrashTests(unittest.TestCase):
    def test_sigkill_during_receipt_after_commit_and_before_package_publication(self):
        for phase in ('during_receipt', 'after_receipt', 'during_package'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                raw = package()
                sha = hashlib.sha256(raw).hexdigest()
                source = root / 'original.gz'
                source.write_bytes(gzip.compress(raw))
                process = subprocess.Popen([sys.executable, '-B', '-S', '-c', CHILD,
                    directory, phase, ACCESSION, CIK, FORM, sha], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                try:
                    self.assertTrue(select.select([process.stdout], [], [], 10)[0], 'writer did not reach save')
                    self.assertEqual(process.stdout.readline().strip(), 'saving')
                    process.kill()
                    self.assertEqual(process.wait(timeout=5), -signal.SIGKILL)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    process.stdout.close()
                    process.stderr.close()
                calls = []
                def sender(*args):
                    calls.append(args)
                    return 200, {}, b'exact'
                with Campaign(root / 'http', live=True, sender=sender, sleep=lambda delay: None) as run:
                    self.assertEqual(run.fetch('https://www.sec.gov/Archives/saved')[0], b'exact')
                    self.assertEqual(run.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                    if phase == 'during_receipt':
                        self.assertNotIn('https://www.sec.gov/Archives/new', run.records)
                        run.db.execute('DROP TRIGGER interrupt')
                        run.fetch('https://www.sec.gov/Archives/new')
                        self.assertEqual(len(calls), 1)  # Uncommitted work may be retried.
                    elif phase == 'after_receipt':
                        self.assertTrue(run.fetch('https://www.sec.gov/Archives/new')[1]['cache_hit'])
                        self.assertEqual(calls, [])
                    else:
                        self.assertFalse((root / 'versions' / ACCESSION / sha).exists())
                        version = acquire(ACCESSION, CIK, FORM, root / 'versions', package=source, sha256=sha)
                        self.assertEqual(read_package(version)[1]['dir/main.htm'], b'<html>hello</html>\n')
                        self.assertTrue((version / 'submission.txt.gz').samefile(source))
                        self.assertEqual(calls, [])
