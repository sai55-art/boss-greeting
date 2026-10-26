# -*- coding: utf-8 -*-
import datetime as dt
import unittest

from src.roster import match_date


def _rec(name, d, category="生日", gender="男"):
    y, m, dd = map(int, d.split("-"))
    return {"category": category, "company": "某公司", "project": "联科滨海智造港",
            "name": name, "title": "董事长", "gender": gender, "date": dt.date(y, m, dd)}


class TestMatch(unittest.TestCase):
    def test_match_birthday_and_anniversary(self):
        records = [
            _rec("张三", "1980-03-05"),
            _rec("李四公司", "2013-03-05", "成立周年"),
            _rec("王五", "1990-03-06"),
        ]
        events = match_date(records, dt.date(2025, 3, 5))
        self.assertEqual([(e["name"], e["category"]) for e in events],
                         [("张三", "生日"), ("李四公司", "成立周年")])
        self.assertEqual(events[1]["years"], 12)

    def test_founding_same_year_skipped(self):
        records = [_rec("新公司", "2025-03-05", "成立周年")]
        self.assertEqual(match_date(records, dt.date(2025, 3, 5)), [])

    def test_leap_day_feb29_matches_feb28(self):
        records = [_rec("闰日", "2000-02-29")]
        self.assertEqual(len(match_date(records, dt.date(2025, 2, 28))), 1)

    def test_leap_day_feb29_matches_feb29(self):
        records = [_rec("闰日", "2000-02-29")]
        self.assertEqual(len(match_date(records, dt.date(2028, 2, 29))), 1)


if __name__ == "__main__":
    unittest.main()
