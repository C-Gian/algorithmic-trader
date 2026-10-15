import unittest
from datetime import UTC, datetime, timedelta, timezone, tzinfo

from trading_primitives.time_intervals import interval_bounds, to_utc


class NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None


class IntervalTests(unittest.TestCase):
    origin = datetime(2025, 1, 1, tzinfo=UTC)

    def bounds(self, instant, minutes=45, origin=None):
        return interval_bounds(instant, minutes=minutes, origin=origin or self.origin)

    def test_45_minutes_cross_hour_and_exclusive_end(self):
        for timestamp, start, end in [
            ("2025-01-01T00:59:59+00:00", "2025-01-01T00:45:00+00:00", "2025-01-01T01:30:00+00:00"),
            ("2025-01-01T01:30:00+00:00", "2025-01-01T01:30:00+00:00", "2025-01-01T02:15:00+00:00"),
            ("2025-01-01T23:59:59+00:00", "2025-01-01T23:15:00+00:00", "2025-01-02T00:00:00+00:00"),
        ]:
            with self.subTest(timestamp=timestamp):
                self.assertEqual(self.bounds(datetime.fromisoformat(timestamp)),
                                 (datetime.fromisoformat(start), datetime.fromisoformat(end)))

    def test_before_origin_uses_floor_not_truncation(self):
        self.assertEqual(self.bounds(self.origin-timedelta(microseconds=1)),
                         (self.origin-timedelta(minutes=45), self.origin))

    def test_daily_leap_day(self):
        t = datetime(2024, 2, 29, 23, 30, tzinfo=UTC)
        self.assertEqual(self.bounds(t, 1440),
                         (datetime(2024, 2, 29, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)))

    def test_timezone_changes_representation_not_grid(self):
        instant = self.origin+timedelta(hours=1)
        self.assertEqual(self.bounds(instant), self.bounds(instant.astimezone(timezone(timedelta(hours=2)))))
        self.assertEqual(to_utc(instant), instant)

    def test_origin_is_explicit_and_affects_grid(self):
        self.assertEqual(self.bounds(self.origin+timedelta(minutes=30),
                                     origin=self.origin+timedelta(minutes=15)),
                         (self.origin+timedelta(minutes=15), self.origin+timedelta(minutes=60)))
        with self.assertRaises(TypeError):
            interval_bounds(self.origin, minutes=45)

    def test_invalid_times_and_widths_rejected(self):
        for value in [datetime(2025, 1, 1), datetime(2025, 1, 1, tzinfo=NoOffset())]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.bounds(value)
        for value in [True, 45.0, "45"]:
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.bounds(self.origin, value)
        for value in [0, -45]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.bounds(self.origin, value)
        with self.assertRaises(ValueError):
            self.bounds(self.origin, origin=self.origin+timedelta(seconds=1))

    def test_contiguous_intervals_and_membership(self):
        for offset in [-2000, -1, 0, 1, 44, 45, 46, 1440]:
            instant = self.origin+timedelta(minutes=offset)
            start, end = self.bounds(instant)
            self.assertLessEqual(start, instant)
            self.assertLess(instant, end)
            self.assertEqual(end-start, timedelta(minutes=45))
            self.assertEqual(self.bounds(end)[0], end)
