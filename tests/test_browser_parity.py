"""Cross-check the offline browser's integer arithmetic against Python."""
import json
from pathlib import Path
import subprocess
import unittest
from datetime import date, timedelta

from mudda_freedom.engine import allocate, Frequency, RoundingPolicy
from mudda_freedom.engine import weekdays
from mudda_freedom.reserves import assess_reserve, DatedAmount

ROOT = Path(__file__).resolve().parents[1]


class BrowserParityTests(unittest.TestCase):
    def test_browser_reserves_match_python(self):
        inputs = [dict(income="1000",incomeFrequency="BIWEEKLY",saved="250",
                       start="2026-01-01",rule="following",delay=delay,holidays=[],
                       bills=[dict(name="Insurance",amount="1200",frequency="ANNUAL",
                                   due="2026-01-01")]) for delay in (0, 10)]
        source = """
          import {calculate} from './web/calculator.mjs';
          import fs from 'node:fs';
          console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(input=>{
            const result=calculate(input);
            return [result.required,result.remaining].map(String);
          })));
        """
        output=subprocess.run(["node","--input-type=module","-e",source],
                              input=json.dumps(inputs),text=True,capture_output=True,
                              cwd=ROOT,check=True)
        for case, actual in zip(inputs,json.loads(output.stdout),strict=True):
            arrivals=[]
            start,end=date(2026,1,1),date(2027,1,1)
            for scheduled in weekdays(start,end+timedelta(days=1)):
                day=scheduled
                remaining=case["delay"]
                while remaining:
                    day+=timedelta(days=1)
                    if day.weekday()<5:
                        remaining-=1
                if day<=end:
                    arrivals.append(DatedAmount(day,"4.62"))
            expected=assess_reserve(start=start,through=end,arrivals=arrivals,
                                   payments=[DatedAmount(start,"1200"),DatedAmount(end,"1200")],
                                   already_saved="250")
            self.assertEqual(actual,[str(int(expected.required*100)),str(int(expected.remaining*100))])

    def test_browser_allocation_matches_python(self):
        cases = [[amount, frequency.name] for amount in
                 ["0", "0.01", "1.17", "1.30", "250", "1200", "1234.56", "999999.99"]
                 for frequency in Frequency]
        source = """
          import {allocation} from './web/calculator.mjs';
          import fs from 'node:fs';
          const cases=JSON.parse(fs.readFileSync(0,'utf8'));
          console.log(JSON.stringify(cases.map(([value,frequency])=>{
            const a=allocation(value,frequency);
            return [a.annual,a.weekly,a.daily].map(String);
          })));
        """
        output = subprocess.run(["node", "--input-type=module", "-e", source],
                                input=json.dumps(cases), text=True, capture_output=True,
                                cwd=ROOT, check=True)
        for (amount, frequency), actual in zip(cases,json.loads(output.stdout),strict=True):
            expected = allocate(amount,Frequency[frequency],
                                rounding=RoundingPolicy.HALF_UP_EACH_STEP)
            with self.subTest(amount=amount,frequency=frequency):
                self.assertEqual(actual,[str(int(value*100)) for value in
                                         (expected.annual,expected.weekly,expected.daily)])
