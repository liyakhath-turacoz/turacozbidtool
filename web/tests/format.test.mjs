import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  budgetComparison,
  expectationPhrases,
  formatDelivery,
  friendlyErrorMessage,
  isLive,
  money,
  plural,
  standingFor,
  timeLeftLabel,
  timeTone,
  titleCase,
  toTime,
} from '../src/format.js';

test('money groups digits the Indian way and drops empty paise', () => {
  assert.equal(money(150000), '₹1,50,000');
  assert.equal(money('15000.00'), '₹15,000');
  assert.equal(money(4200.5), '₹4,200.50');
  assert.equal(money(0), '₹0');
});

test('money shows a dash instead of inventing zero for missing values', () => {
  for (const missing of [null, undefined, '', 'abc', NaN]) assert.equal(money(missing), '—');
});

test('plural and titleCase read naturally', () => {
  assert.equal(plural(1, 'unit'), '1 unit');
  assert.equal(plural(3, 'unit'), '3 units');
  assert.equal(plural(2, 'subcategory', 'subcategories'), '2 subcategories');
  assert.equal(titleCase('in_review'), 'In review');
  assert.equal(titleCase(''), '');
});

test('timeLeftLabel counts down in the unit that matters', () => {
  const minute = 60 * 1000;
  assert.equal(timeLeftLabel(0), 'Ended');
  assert.equal(timeLeftLabel(-5000), 'Ended');
  assert.equal(timeLeftLabel(42 * 1000), '42s left');
  assert.equal(timeLeftLabel(9 * minute + 5000), '9m 05s left');
  assert.equal(timeLeftLabel(25 * minute), '25m left');
  assert.equal(timeLeftLabel(95 * minute), '1h 35m left');
  assert.equal(timeLeftLabel(26 * 60 * minute), '1d 2h left');
});

test('timeTone turns urgent in the last ten minutes', () => {
  const minute = 60 * 1000;
  assert.equal(timeTone(0), 'ended');
  assert.equal(timeTone(5 * minute), 'urgent');
  assert.equal(timeTone(30 * minute), 'soon');
  assert.equal(timeTone(3 * 60 * minute), 'calm');
});

test('toTime reads naive and offset timestamps', () => {
  assert.equal(toTime('2026-10-14T10:00:00+00:00'), Date.UTC(2026, 9, 14, 10));
  assert.ok(Number.isFinite(toTime('2026-10-14 10:00:00')));
  assert.ok(Number.isNaN(toTime('')));
});

test('formatDelivery adds a unit to legacy bare numbers only', () => {
  assert.equal(formatDelivery('1'), '1 day');
  assert.equal(formatDelivery('5'), '5 days');
  assert.equal(formatDelivery('Same day'), 'Same day');
  assert.equal(formatDelivery('24 hours'), '24 hours');
  assert.equal(formatDelivery(''), 'Not stated');
});

test('isLive covers active and revised offers only', () => {
  assert.equal(isLive({ status: 'active' }), true);
  assert.equal(isLive({ status: 'UPDATED' }), true);
  for (const status of ['won', 'lost', 'withdrawn', 'expired']) assert.equal(isLive({ status }), false);
});

test('standingFor ranks a dealer against live competing offers', () => {
  const mine = { id: 'm', bid_request_id: 'r1', amount: '9000', status: 'active', is_mine: true };
  const rival = (id, amount, extra = {}) => ({ id, bid_request_id: 'r1', amount: String(amount), status: 'active', is_mine: false, ...extra });

  assert.deepEqual(standingFor(mine, [mine]), { kind: 'solo', lowest: null, gap: 0, count: 0 });
  assert.equal(standingFor(mine, [mine, rival('a', 9500)]).kind, 'lead');
  assert.equal(standingFor(mine, [mine, rival('a', 9000)]).kind, 'lead');

  const behind = standingFor(mine, [mine, rival('a', 8500), rival('b', 8800)]);
  assert.equal(behind.kind, 'trail');
  assert.equal(behind.gap, 500);
  assert.equal(behind.lowest, 8500);

  // Offers that are withdrawn, lost, or on another request do not count.
  const ignored = [rival('c', 100, { status: 'withdrawn' }), rival('d', 100, { status: 'lost' }), rival('e', 100, { bid_request_id: 'r2' })];
  assert.equal(standingFor(mine, [mine, ...ignored]).kind, 'solo');
});

test('friendlyErrorMessage turns API errors into one plain sentence', () => {
  const api = (status, body) => new Error(`API error ${status}: ${JSON.stringify(body)}`);
  assert.equal(friendlyErrorMessage(api(409, { detail: 'Another product already matches this.' })), 'Another product already matches this.');
  // Rules written in the backend arrive as "Value error, <sentence>"; only the sentence is shown.
  assert.equal(
    friendlyErrorMessage(api(422, { detail: [{ type: 'value_error', loc: ['body', 'payment'], msg: 'Value error, Enter a valid UPI ID such as shopname@bank' }] })),
    'Enter a valid UPI ID such as shopname@bank',
  );
  assert.equal(friendlyErrorMessage(api(422, { detail: [{ type: 'missing', loc: ['body', 'full_name'], msg: 'Field required' }] })), 'Full Name is required.');
  assert.equal(friendlyErrorMessage(new Error('Network down')), 'Network down');
  assert.equal(friendlyErrorMessage(undefined), 'Something went wrong. Please try again.');
});

test('expectationPhrases lists only what the buyer asked for', () => {
  assert.deepEqual(expectationPhrases({}), []);
  assert.deepEqual(expectationPhrases({ budget_amount: null, want_warranty: '', want_installation: 0 }), []);
  const phrases = expectationPhrases({ budget_amount: '80000.00', want_warranty: '2 years', want_delivery: 'Within 3 days', want_installation: 1 }, 2);
  assert.deepEqual(phrases.map((item) => item.text), ['Budget ₹80,000 (₹40,000 each)', 'Warranty: 2 years', 'Delivery: Within 3 days', 'Installation needed']);
  assert.equal(expectationPhrases({ budget_amount: '5000' }, 1)[0].text, 'Budget ₹5,000');
});

test('budgetComparison says whether a price fits the budget', () => {
  assert.deepEqual(budgetComparison('80000', 70000), { within: true, gap: 10000 });
  assert.deepEqual(budgetComparison('80000', 80000), { within: true, gap: 0 });
  assert.deepEqual(budgetComparison('80000', '85500'), { within: false, gap: 5500 });
  assert.equal(budgetComparison(null, 70000), null);
  assert.equal(budgetComparison('80000', ''), null);
});
