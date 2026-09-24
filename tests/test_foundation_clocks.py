# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestFoundationClocks(LdmCase):
    """Iraqi time: Sunday to Thursday, public holidays, and statutory periods
    counted in calendar days with only the last day moved off a holiday."""

    def test_weekend_is_friday_and_saturday(self):
        self.assertTrue(self.company.ldm_is_working_day(self.d("2026-10-01")))   # Thursday
        self.assertFalse(self.company.ldm_is_working_day(self.d("2026-10-02")))  # Friday
        self.assertFalse(self.company.ldm_is_working_day(self.d("2026-10-03")))  # Saturday
        self.assertTrue(self.company.ldm_is_working_day(self.d("2026-10-04")))   # Sunday

    def test_working_days_skip_the_weekend(self):
        # Thursday + 1 working day = Sunday; + 3 = Tuesday
        self.assertEqual(self.company.ldm_add_working_days(self.d("2026-10-01"), 1), self.d("2026-10-04"))
        self.assertEqual(self.company.ldm_add_working_days(self.d("2026-10-01"), 3), self.d("2026-10-06"))

    def test_working_days_skip_a_public_holiday(self):
        # New Year's Day 2026 is a Thursday holiday: Wednesday 31 Dec + 1 = Sunday 4 Jan
        self.assertFalse(self.company.ldm_is_working_day(self.d("2026-01-01")))
        self.assertEqual(self.company.ldm_add_working_days(self.d("2025-12-31"), 1), self.d("2026-01-04"))

    def test_appeal_period_is_calendar_days(self):
        # Service on Thu 1 Oct 2026, 15-day appeal (CCP Arts. 25, 187): the period
        # ends Fri 16 Oct, a weekend day, so the legal last day is Sun 18 Oct.
        safe, legal = self.company.ldm_statutory_dates(self.d("2026-10-01"), 15)
        self.assertEqual(safe, self.d("2026-10-16"))
        self.assertEqual(legal, self.d("2026-10-18"))

    def test_period_ending_on_a_working_day_does_not_move(self):
        safe, legal = self.company.ldm_statutory_dates(self.d("2026-10-01"), 30)  # Sat 31 Oct -> Sun 1 Nov
        self.assertEqual(safe, self.d("2026-10-31"))
        self.assertEqual(legal, self.d("2026-11-01"))
        safe, legal = self.company.ldm_statutory_dates(self.d("2026-10-05"), 10)  # Thu 15 Oct
        self.assertEqual(safe, legal)

    def test_period_ending_in_eid_moves_after_it(self):
        # Eid al-Adha 2026 (estimated) 27-30 May; the 30th is a Saturday -> Sunday 31 May
        safe, legal = self.company.ldm_statutory_dates(self.d("2026-05-12"), 15)
        self.assertEqual(safe, self.d("2026-05-27"))
        self.assertEqual(legal, self.d("2026-05-31"))

    def test_month_periods_and_caps(self):
        safe, legal = self.company.ldm_statutory_dates(self.d("2026-01-15"), 3, unit="months")
        self.assertEqual(safe, self.d("2026-04-15"))
        # correction of a cassation decision: 7 days but never after 6 months from the decision
        safe, _legal = self.company.ldm_statutory_dates(self.d("2026-07-10"), 7, max_months=6,
                                                         cap_from=self.d("2026-01-12"))
        self.assertEqual(safe, self.d("2026-07-12"))
