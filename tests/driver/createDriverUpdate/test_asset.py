from datetime import datetime
import unittest

from driver.createDriverUpdate.asset import Asset, Unit

PUBLIC = datetime.fromisoformat('2023-08-31T17:18:57-04:00')
UNIT = dict(text='Fourth quarter revenue guidance of approximately $9.27 billion', file='ex991.htm', start=10, end=72)
ASSET = dict(source_id='0001730168-23-000074', source_type='8-K', date=PUBLIC, units=(Unit(**UNIT),))


class AssetTests(unittest.TestCase):
    def test_one_unit_and_a_whole_document_are_both_accepted(self):
        one = Asset(**ASSET)
        many = Asset(**{**ASSET, 'units': tuple(Unit(**{**UNIT, 'start': i, 'end': i + 5}) for i in range(0, 500, 5))})
        self.assertEqual(len(one.units), 1)
        self.assertEqual(len(many.units), 100)

    def test_any_kind_of_source_is_accepted(self):
        for kind in ('8-K', '10-Q', '425', 'SCHEDULE 13D/A', 'transcript', 'news'):
            self.assertEqual(Asset(**{**ASSET, 'source_type': kind}).source_type, kind)

    def test_accepted_units_cannot_change_or_run_out(self):
        units = [Unit(**UNIT)]
        from_list = Asset(**{**ASSET, 'units': units})
        units.clear()
        from_iterator = Asset(**{**ASSET, 'units': (unit for unit in [Unit(**UNIT)])})
        self.assertEqual((len(from_list.units), len(from_iterator.units), len(from_iterator.units)), (1, 1, 1))

    def test_an_incomplete_unit_is_refused(self):
        for change, reason in (({'text': ''}, 'unit has no text'), ({'file': ''}, 'unit has no file'),
                               ({'text': 5}, 'unit has no text'), ({'file': 5}, 'unit has no file'),
                               ({'start': None}, 'unit has no span'), ({'end': None}, 'unit has no span'),
                               ({'start': False}, 'unit has no span'), ({'start': 0, 'end': True}, 'unit has no span'),
                               ({'start': 72}, 'unit has no span'), ({'start': -1}, 'unit has no span')):
            with self.subTest(change), self.assertRaisesRegex(ValueError, reason):
                Unit(**{**UNIT, **change})

    def test_an_incomplete_asset_is_refused(self):
        for change, reason in (({'source_id': ''}, 'asset has no source_id'),
                               ({'source_type': ''}, 'asset has no source_type'),
                               ({'source_id': 5}, 'asset has no source_id'),
                               ({'source_type': 5}, 'asset has no source_type'),
                               ({'units': None}, 'asset has no units'),
                               ({'units': iter(())}, 'asset has no units'),
                               ({'date': None}, 'asset has no date with a time zone'),
                               ({'date': '2023-08-31T17:18:57-04:00'}, 'asset has no date with a time zone'),
                               ({'date': PUBLIC.replace(tzinfo=None)}, 'asset has no date with a time zone'),
                               ({'units': ()}, 'asset has no units'),
                               ({'units': (UNIT,)}, 'asset has no units')):
            with self.subTest(change), self.assertRaisesRegex(ValueError, reason):
                Asset(**{**ASSET, **change})


if __name__ == '__main__':
    unittest.main()
