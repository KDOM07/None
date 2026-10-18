// Integer cents preserve Python's confirmed half-up-at-each-step rule.
export const frequencies = {WEEKLY:52, BIWEEKLY:26, SEMIMONTHLY:24,
  MONTHLY:12, QUARTERLY:4, SEMIANNUAL:2, ANNUAL:1};
export function cents(value) {
  if (typeof value !== 'string' || !/^\d{1,10}(\.\d{1,2})?$/.test(value))
    throw new Error('Enter a nonnegative dollar amount with at most two decimal places.');
  const [whole, fraction=''] = value.split('.');
  return BigInt(whole)*100n + BigInt(fraction.padEnd(2,'0'));
}
export function dollars(value) {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  return `${negative?'-':''}$${(absolute/100n).toLocaleString('en-US')}.${String(absolute%100n).padStart(2,'0')}`;
}
function divide(value, divisor) {return (value + divisor/2n)/divisor;}
export function allocation(value, frequency) {
  if (!Object.hasOwn(frequencies,frequency)) throw new Error('Choose a supported frequency.');
  const annual = cents(value)*BigInt(frequencies[frequency]);
  const weekly = divide(annual,52n);
  return {annual,weekly,daily:divide(weekly,5n)};
}
export function parseDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Enter a valid date.');
  const result=new Date(`${value}T00:00:00Z`);
  if (!Number.isFinite(result.getTime()) || result.toISOString().slice(0,10)!==value)
    throw new Error('Enter a valid calendar date.');
  return result;
}
const iso = day => day.toISOString().slice(0,10);
const addDays = (day,count) => new Date(day.getTime()+count*86400000);
function addMonths(day,count) {
  const first=new Date(Date.UTC(day.getUTCFullYear(),day.getUTCMonth()+count,1));
  const last=new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth()+1,0)).getUTCDate();
  first.setUTCDate(Math.min(day.getUTCDate(),last));
  return first;
}
function business(day,holidays) {return ![0,6].includes(day.getUTCDay()) && !holidays.has(iso(day));}
function arrival(day,holidays,rule,delay) {
  if (rule==='unknown') return null; // No uncertain arrivals credited to reserves.
  while (!business(day,holidays)) {
    if (rule==='skip') return null;
    day=addDays(day,rule==='previous'?-1:1);
  }
  while (delay>0) {
    day=addDays(day,1);
    if (business(day,holidays)) delay--;
  }
  return day;
}
function paymentDates(first,frequency,end) {
  if (!['MONTHLY','QUARTERLY','SEMIANNUAL','ANNUAL','WEEKLY','BIWEEKLY'].includes(frequency))
    throw new Error('Choose a supported bill frequency.');
  const dates=[];
  for (let i=0;i<800;i++) {
    const day=frequency==='WEEKLY'||frequency==='BIWEEKLY'
      ? addDays(first,i*(frequency==='WEEKLY'?7:14))
      : addMonths(first,i*({MONTHLY:1,QUARTERLY:3,SEMIANNUAL:6,ANNUAL:12}[frequency]));
    if (day>end) break;
    dates.push(day);
  }
  return dates;
}
export function calculate(input) {
  const start=parseDate(input.start), end=addMonths(start,12);
  const income=allocation(input.income,input.incomeFrequency);
  const saved=cents(input.saved);
  const holidays=new Set((input.holidays||[]).map(value=>iso(parseDate(value))));
  if (!['unknown','previous','following','skip'].includes(input.rule)) throw new Error('Choose a transfer rule.');
  if (!Number.isInteger(input.delay)||input.delay<0||input.delay>10) throw new Error('Transfer delay must be 0–10 business days.');
  if (!Array.isArray(input.bills)||input.bills.length===0||input.bills.length>100) throw new Error('Add between 1 and 100 bills.');
  const events=[], bills=[];
  let billDaily=0n;
  for (const bill of input.bills) {
    const due=parseDate(bill.due);
    if (due<start||due>end) throw new Error('Each next bill date must fall within the next 12 months.');
    const allocated=allocation(bill.amount,bill.frequency);
    billDaily+=allocated.daily;
    bills.push({...bill,...allocated});
    for (const day of paymentDates(due,bill.frequency,end))
      events.push({day:iso(day),order:0,delta:-cents(bill.amount)});
  }
  // Five separately scheduled weekdays; shifted collisions retain each amount.
  for (let scheduled=start;scheduled<=end;scheduled=addDays(scheduled,1)) {
    if ([0,6].includes(scheduled.getUTCDay())) continue;
    const day=arrival(scheduled,holidays,input.rule,input.delay);
    if (day && day>=start && day<=end) events.push({day:iso(day),order:1,delta:billDaily});
  }
  events.sort((a,b)=>a.day.localeCompare(b.day)||a.order-b.order);
  let balance=0n, required=0n;
  for (const event of events) {
    balance+=event.delta;
    if (-balance>required) required=-balance;
  }
  return {income,bills,billDaily,freeDaily:income.daily-billDaily,required,saved,
    remaining:required>saved?required-saved:0n,through:iso(end),
    bankingKnown:input.rule!=='unknown'};
}
