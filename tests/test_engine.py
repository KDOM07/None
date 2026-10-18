import unittest
from datetime import date
from decimal import Decimal as D

from mudda_freedom.engine import (
    Frequency as F, RoundingPolicy as R, PaycheckMethod as P,
    allocate, money, daily_plan, representative_paycheck, variable_monthly_bill,
    reconcile_year, weekdays, migration_progress,
)


def allocation(amount, frequency):
    return allocate(amount, frequency, rounding=R.HALF_UP_EACH_STEP)


class CalculationTests(unittest.TestCase):
    def test_creator_monthly_example(self):
        result = allocation("250", F.MONTHLY)
        self.assertEqual((result.annual, result.weekly, result.daily),
                         (D("3000"), D("57.69"), D("11.54")))

    def test_creator_income_and_eight_bills(self):
        income = allocation("1000", F.BIWEEKLY)
        self.assertEqual(income.daily, D("100"))
        # The document's eight daily values actually sum to 65.06.
        self.assertEqual(sum(map(D, ["11.54", "8.20", "5.25", "7.88",
                                    "20.10", "8.75", "1.12", "2.22"])), D("65.06"))

    def test_all_frequencies_annualize(self):
        for frequency, count in [(F.WEEKLY,52),(F.BIWEEKLY,26),
                (F.SEMIMONTHLY,24),(F.MONTHLY,12),(F.QUARTERLY,4),
                (F.SEMIANNUAL,2),(F.ANNUAL,1),(13,13)]:
            with self.subTest(frequency=frequency):
                self.assertEqual(allocation("100", frequency).annual, D(100*count))

    def test_weekly_rounding_before_daily(self):
        result = allocation("1.17", F.ANNUAL)
        self.assertEqual(result.weekly, D("0.02"))
        self.assertEqual(result.daily, D("0.00"))
        self.assertEqual(allocation("1.30", F.ANNUAL).weekly, D("0.03"))

    def test_rounding_requires_explicit_selection(self):
        with self.assertRaises(TypeError):
            allocate("250", F.MONTHLY)

    def test_invalid_inputs(self):
        for value in ["-1", "NaN", "Infinity"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)
        with self.assertRaises(TypeError):
            money(0.1)
        for frequency in [0, -1, True, 2.5]:
            with self.subTest(frequency=frequency), self.assertRaises(ValueError):
                allocation("10", frequency)

    def test_variable_pay_customer_choice(self):
        history = ["900", "1000", "1100"]
        self.assertEqual(representative_paycheck(history, method=P.AVERAGE), D(1000))
        self.assertEqual(representative_paycheck(history, method=P.LOWEST_TYPICAL), D(900))
        with self.assertRaises(ValueError):
            representative_paycheck(history, method=None)
        with self.assertRaises(ValueError):
            representative_paycheck([], method=P.AVERAGE)

    def test_variable_bill_uses_latest_year_average(self):
        self.assertEqual(variable_monthly_bill(["9999"]+["100"]*11+["220"]), D(110))
        with self.assertRaises(ValueError):
            variable_monthly_bill(["100"]*11)

    def test_separate_free_money_and_shortage(self):
        income = allocation("1000", F.BIWEEKLY)
        result = daily_plan(income, [allocation("250", F.MONTHLY)])
        self.assertEqual(result.free_daily, D("88.46"))
        self.assertTrue(result.sustainable_allocation)
        shortage = daily_plan(income, [allocation("3000", F.MONTHLY)])
        self.assertFalse(shortage.sustainable_allocation)
        self.assertLess(shortage.free_daily, 0)

    def test_actual_years_and_explicit_reconciliation(self):
        bill = allocation("250", F.MONTHLY)
        for year, count in [(2022,260),(2023,260),(2024,262),(2025,261)]:
            with self.subTest(year=year):
                result = reconcile_year(bill, year)
                self.assertEqual(result.weekday_count, count)
                self.assertEqual(result.difference, D("11.54")*count-D(3000))
                self.assertEqual(bill.daily, D("11.54"))

    def test_february_semimonthly_intervals(self):
        self.assertEqual(len(weekdays(date(2026,2,13),date(2026,2,27))),10)
        self.assertEqual(len(weekdays(date(2026,2,27),date(2026,3,13))),10)
        with self.assertRaises(ValueError):
            weekdays(date(2026,3,1),date(2026,2,1))

    def test_savings_jump_start_and_progress(self):
        partial = migration_progress(required="1000",saved="250",additional="250")
        self.assertEqual(partial.remaining,D(500))
        self.assertEqual(partial.percent,D(50))
        self.assertFalse(partial.reserve_funded)
        funded = migration_progress(required="1000",saved="250",additional="800")
        self.assertEqual(funded.remaining,0)
        self.assertEqual(funded.percent,100)
        self.assertTrue(funded.reserve_funded)
        self.assertFalse(funded.activation_allowed)

    def test_recalculation_after_life_changes(self):
        income = allocation("1000",F.BIWEEKLY)
        old = daily_plan(income,[allocation("250",F.MONTHLY)])
        paid_off = daily_plan(income,[])
        raised = daily_plan(allocation("1100",F.BIWEEKLY),[])
        self.assertGreater(paid_off.free_daily,old.free_daily)
        self.assertGreater(raised.free_daily,paid_off.free_daily)
        self.assertEqual(old.bill_daily,D("11.54"))


if __name__ == "__main__":
    unittest.main()
