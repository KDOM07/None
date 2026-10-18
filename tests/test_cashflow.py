import unittest
from datetime import date
from decimal import Decimal as D
from mudda_freedom.cashflow import (
    HolidayRule as H, processing_date, grouped_transfers, Event, simulate,
)


class CashFlowTests(unittest.TestCase):
    def test_holidays_in_both_directions_and_collisions(self):
        holiday = date(2026,1,1)
        holidays = frozenset([holiday])
        self.assertEqual(processing_date(holiday,holidays,H.PREVIOUS),date(2025,12,31))
        self.assertEqual(processing_date(holiday,holidays,H.FOLLOWING),date(2026,1,2))
        self.assertIsNone(processing_date(holiday,holidays,H.SKIP))
        result = grouped_transfers([holiday,date(2026,1,2)],"11.54",
                                   holidays=holidays,rule=H.FOLLOWING)
        self.assertEqual(result,{date(2026,1,2):D("23.08")})

    def test_weekend_and_unknown_rule(self):
        self.assertEqual(processing_date(date(2026,1,3),frozenset(),H.FOLLOWING),date(2026,1,5))
        with self.assertRaises(ValueError):
            processing_date(date(2026,1,1),frozenset(),None)

    def test_internal_transfers_do_not_double_count(self):
        day = date(2026,1,2)
        result = simulate({"holding":"0","bills":"0","free":"0"},[
            Event(day,0,D(1000),None,"holding"),
            Event(day,1,D(200),"holding","bills"),
            Event(day,2,D(50),"holding","free"),
            Event(day,3,D(150),"bills",None),
        ])
        self.assertEqual(result.income,D(1000))
        self.assertEqual(result.expenses,D(150))
        self.assertEqual(sum(result.balances.values()),D(850))
        self.assertEqual(result.shortages,())

    def test_shortage_before_later_deposit_is_preserved(self):
        day = date(2026,1,2)
        result = simulate({"holding":"0","bills":"0"},[
            Event(day,0,D(100),"holding","bills"),
            Event(day,1,D(100),None,"holding"),
        ])
        self.assertEqual(result.shortages,((day,"holding",D(100)),))
        self.assertEqual(result.balances["holding"],0)

    def test_ambiguous_order_and_unknown_accounts_rejected(self):
        event = Event(date(2026,1,2),0,D(10),None,"holding")
        with self.assertRaises(ValueError):
            simulate({"holding":"0"},[event,event])
        with self.assertRaises(ValueError):
            simulate({},[event])
