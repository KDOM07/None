# Mudda Freedom calculation engine

Python 3.12+, standard library only for the financial engine. An offline browser
calculator is included; it has no bank connections and stores no customer data.

## Try it without a terminal

Download `Mudda-Freedom-Calculator.html`, open it in a current browser, and
click **Try sample numbers**. Change income, bills, next payment dates, or
savings, then click **Calculate my daily plan**. **Clear entries** starts over.
Closing or refreshing the page clears entries. If a device previews HTML as a
document, open the file in a browser on a computer to use its controls.

This is a browser prototype, not a deployed website. It projects recurring
bill payments for 12 months. The separate Python activation gate requires
complete account projections and an explicitly assessed base reserve/buffer;
the browser calculator does not approve activation.

## Development checks

## Publishing the test calculator

The `Test and publish calculator` GitHub Actions workflow tests the engine and
publishes only the bundled HTML as a GitHub Pages site on pushes to `master`.
Enable **Settings → Pages → Build and deployment → Source → GitHub Actions**
in the GitHub repository before running it. If the first deployment runs before
Pages is enabled, enable that setting and rerun the workflow from Actions.
The successful deployment reports the actual public URL. The published page
does not transmit or persist entered financial information.

## Running checks locally

Run from the checkout:

```sh
python -m unittest discover -s tests -v
node tests/browser.mjs
```

Parity tests require Node 24+. Browser checks use the cloud machine's
Playwright and Chromium; set `CHROMIUM_PATH` for another Chromium location.
Rebuild the standalone HTML after editing web sources with
`python scripts/build_calculator.py`. No external scripts or services are
needed to use the bundled HTML; it calculates with integer cents.

`mudda_freedom.engine` calculates annual → rounded weekly → rounded daily
allocations, supported/custom annual frequencies, customer-selected variable
pay, 12-month variable-bill averages, separate bill/free-money amounts, actual
weekday reconciliation, and confirmed migration savings progress.

`mudda_freedom.cashflow` shifts explicitly supplied dates using independently
chosen institution rules, groups colliding transfers, and simulates dated
deposits, internal transfers, and external expenses without double counting.
Supply bank-confirmed event ordering and processing/arrival dates. Holiday
calendars must be supplied; the engine does not guess a customer's jurisdiction.

## Confirmed rounding rule

The customer confirmed ordinary cent rounding (5 rounds up) at each step:
round the weekly amount first, then calculate and round the daily amount.
`HALF_UP_EACH_STEP` implements this rule. For $250 monthly, the results are
$3,000 annually, $57.69 weekly, and $11.54 daily.

## Due-date reserve calculation

`mudda_freedom.reserves.assess_reserve` calculates the largest cumulative
shortfall across supplied bill payments and actual funding arrival dates.
Annual bills are paid once per year; the daily allocation remains annual
amount ÷ 52 (rounded), then ÷ 5 (rounded). A closer due date can require a
larger starting reserve. Existing savings reduce the remaining amount needed.
Same-day arrivals are conservatively counted after bill payments.
The returned assessment horizon makes the projection's limits explicit.

## Decisions and work still needed

- “One full month” versus “30 days” needs an agreed reserve definition,
  particularly for quarterly bills and February. The caller must currently
  combine the base migration requirement with the dated shortfall assessment;
  progress alone never authorizes activation.
- Actual employer schedules (including extra paycheck years), banking delays,
  automated personalized reserve/buffer assessment, a multi-paycheck migration
  planner, and wiring complete evidence into the activation gate remain to be
  implemented. Nominal annual
  frequency calculations do not claim to model actual deposit calendars.

Annual reconciliation reports a surplus or shortfall without changing the
creator's 52-week/five-day calculation. Recalculation uses pure functions;
applying a changed plan and customer confirmation belong to a future service.
No transfer is executed by this code. No financial readiness claim should be
made from daily allocation arithmetic alone.

The two supplied DOCX documents are project references. The initial request
prioritized engine development and tests. The subsequent request authorized
this first browser calculator after those engine checks.
