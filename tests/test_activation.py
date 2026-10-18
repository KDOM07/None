import unittest
from datetime import date
from decimal import Decimal as D
from mudda_freedom.activation import check_activation
from mudda_freedom.cashflow import simulate, Event
from mudda_freedom.engine import allocate, daily_plan, Frequency as F, RoundingPolicy as R
from mudda_freedom.reserves import assess_reserve, DatedAmount


class ActivationTests(unittest.TestCase):
    def evidence(self, saved="1000"):
        start, end = date(2026,1,1), date(2027,1,1)
        plan = daily_plan(allocate("1000",F.BIWEEKLY,rounding=R.HALF_UP_EACH_STEP),
                          [allocate("250",F.MONTHLY,rounding=R.HALF_UP_EACH_STEP)])
        reserve = assess_reserve(start=start,through=end,
                                payments=[DatedAmount(start,"250")],already_saved=saved,
                                arrivals=[])
        simulation = simulate({"bills":saved},[Event(start,0,D(250),"bills",None)])
        return dict(plan=plan,reserve=reserve,simulation=simulation,projection_through=end,
                    banking_confirmed=True,schedule_complete=True,
                    base_reserve="500",personalized_buffer="100")

    def test_complete_funded_projection_passes(self):
        self.assertTrue(check_activation(**self.evidence()).allowed)

    def test_savings_alone_do_not_allow_activation(self):
        evidence=self.evidence()
        evidence.update(banking_confirmed=False,schedule_complete=False)
        decision=check_activation(**evidence)
        self.assertFalse(decision.allowed)
        self.assertEqual(len(decision.reasons),2)

    def test_base_reserve_and_buffer_are_enforced(self):
        decision=check_activation(**self.evidence(saved="550"))
        self.assertFalse(decision.allowed)
        self.assertIn("$50.00",decision.reasons[0])

    def test_short_projection_blocks_activation(self):
        evidence=self.evidence()
        evidence["projection_through"]=date(2026,2,1)
        self.assertFalse(check_activation(**evidence).allowed)

    def test_shortage_blocks_even_with_savings(self):
        evidence=self.evidence()
        evidence["simulation"]=simulate({"holding":"0"},[
            Event(date(2026,1,1),0,D(100),"holding",None)])
        self.assertFalse(check_activation(**evidence).allowed)

    def test_unsustainable_plan_blocks_activation(self):
        evidence=self.evidence()
        evidence["plan"]=daily_plan(evidence["plan"].income,[
            allocate("10000",F.MONTHLY,rounding=R.HALF_UP_EACH_STEP)])
        self.assertFalse(check_activation(**evidence).allowed)
