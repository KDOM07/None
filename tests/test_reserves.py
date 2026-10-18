import unittest
from datetime import date, timedelta
from decimal import Decimal as D

from mudda_freedom.engine import allocate, Frequency, RoundingPolicy
from mudda_freedom.reserves import DatedAmount as A, assess_reserve
from mudda_freedom.cashflow import grouped_transfers, HolidayRule


class ReserveTests(unittest.TestCase):
    def assess(self, payments, arrivals=(), saved="0", start=date(2026,1,1),
               through=date(2027,1,1)):
        return assess_reserve(start=start,through=through,payments=payments,
                              arrivals=arrivals,already_saved=saved)

    def test_annual_bill_with_100_available_allocations(self):
        daily = allocate("1200",Frequency.ANNUAL,
                         rounding=RoundingPolicy.HALF_UP_EACH_STEP).daily
        start = date(2026,1,1)
        arrivals = [A(start+timedelta(days=i),daily) for i in range(100)]
        result = self.assess([A(date(2026,6,1),"1200")],arrivals)
        self.assertEqual(result.required,D("738.00"))
        self.assertEqual(result.funding_before_next_payment,D("462.00"))

    def test_due_today_requires_full_payment(self):
        result = self.assess([A(date(2026,1,1),"1200")],
                             [A(date(2026,1,1),"4.62")])
        self.assertEqual(result.required,D(1200))

    def test_closer_due_date_needs_more_reserve(self):
        arrivals = [A(date(2026,1,2),"100"), A(date(2026,2,2),"100")]
        near = self.assess([A(date(2026,1,15),"1200")],arrivals)
        far = self.assess([A(date(2026,3,15),"1200")],arrivals)
        self.assertEqual(near.required,D(1100))
        self.assertEqual(far.required,D(1000))

    def test_existing_savings_count_once(self):
        result = self.assess([A(date(2026,2,1),"1200")],
                             [A(date(2026,1,5),"462")],saved="250")
        self.assertEqual(result.required,D(738))
        self.assertEqual(result.remaining,D(488))

    def test_surplus_never_produces_negative_goal(self):
        result = self.assess([A(date(2026,2,1),"100")],
                             [A(date(2026,1,5),"150")],saved="250")
        self.assertEqual(result.required,0)
        self.assertEqual(result.remaining,0)

    def test_later_payment_shortage_not_hidden_by_first_payment(self):
        result = self.assess([A(date(2026,2,1),"100"),A(date(2026,3,1),"500")],
                             [A(date(2026,1,5),"100"),A(date(2026,2,5),"100")])
        self.assertEqual(result.required,D(400))

    def test_same_day_payments_combined(self):
        result = self.assess([A(date(2026,2,1),"100"),A(date(2026,2,1),"200")])
        self.assertEqual(result.required,D(300))
        self.assertEqual(result.next_payment,D(300))

    def test_february_and_leap_day_use_real_dates(self):
        result = self.assess([A(date(2028,2,29),"300")],
                             [A(date(2028,2,28),"100")],
                             start=date(2028,2,1),through=date(2028,3,1))
        self.assertEqual(result.required,D(200))

    def test_holiday_shift_past_due_date_cannot_fund_bill(self):
        holiday = date(2026,1,1)
        shifted = grouped_transfers([holiday],"100",holidays=frozenset([holiday]),
                                    rule=HolidayRule.FOLLOWING)
        result = self.assess([A(holiday,"100")],
                             [A(day,amount) for day,amount in shifted.items()])
        self.assertEqual(result.required,D(100))

    def test_reject_incomplete_or_out_of_horizon_input(self):
        with self.assertRaises(ValueError):
            self.assess([])
        with self.assertRaises(ValueError):
            self.assess([A(date(2025,1,1),"100")])
        with self.assertRaises(ValueError):
            self.assess([A(date(2026,2,1),"-1")])


if __name__ == "__main__":
    unittest.main()
