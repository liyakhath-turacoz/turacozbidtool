import React, { useCallback, useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { api } from './api.js';
import { dateTime, friendlyErrorMessage, money, plural } from './format.js';
import { loadRazorpay, openRazorpay } from './payments.js';
import { Modal, Panel, Status } from './ui.jsx';

const PERKS = [
  'See every buyer request for products you sell, as soon as it is posted',
  'Send bids and revise them until the timer ends',
  'Buyers see your shop details and payment details on your bids',
];

function validityLine(info) {
  if (!info?.subscribed) return null;
  if (!info.valid_until) return 'Your subscription is active.';
  if (info.days_left === 0) return `Your subscription ends today, ${dateTime(info.valid_until)}.`;
  return `Your subscription is active until ${dateTime(info.valid_until)} (${plural(info.days_left, 'day')} left).`;
}

/** Pay for (or renew) the shop subscription. The server fixes the price; the browser only opens the payment window. */
export function SubscribeModal({ user, onClose, onPaid }) {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [paidUntil, setPaidUntil] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.subscription(user.access_token)
      .then((result) => { if (!cancelled) setInfo(result); })
      .catch((err) => { if (!cancelled) setError(friendlyErrorMessage(err)); });
    return () => { cancelled = true; };
  }, [user.access_token]);

  const pay = async () => {
    if (busy || !info) return;
    setBusy(true);
    setError('');
    try {
      const token = user.access_token;
      if (info.mode === 'demo') {
        await api.activateDealerSubscription(token);
      } else {
        const order = await api.subscriptionOrder(token);
        let proof;
        if (order.mode === 'test') {
          const result = await api.subscriptionTestPay(token, order.order_id);
          proof = { order_id: order.order_id, payment_id: result.payment_id, signature: result.signature };
        } else {
          await loadRazorpay();
          proof = await openRazorpay(order);
        }
        await api.subscriptionVerify(token, proof);
      }
      const fresh = await api.subscription(user.access_token).catch(() => null);
      setPaidUntil(fresh?.valid_until ? dateTime(fresh.valid_until) : 'now');
      onPaid();
    } catch (err) {
      setError(err.cancelled ? 'The payment was cancelled and you have not been charged.' : friendlyErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const renewing = Boolean(info?.subscribed);
  const buttonLabel = busy
    ? 'Working...'
    : info?.mode === 'demo'
      ? 'Activate (demo, no payment)'
      : `Pay ${money(info?.price)} and ${renewing ? 'renew' : 'subscribe'}`;

  if (paidUntil) {
    return (
      <Modal title="You are subscribed" onClose={onClose}>
        <div className="subscribe-done">
          <span className="check-mark done-mark" aria-hidden="true"><Check size={18} /></span>
          <p>{paidUntil === 'now' ? 'Your subscription is active.' : `Your subscription is active until ${paidUntil}.`} New requests for your products will appear under Open requests.</p>
        </div>
        <div className="dialog-actions"><button type="button" className="primary" onClick={onClose}>Done</button></div>
      </Modal>
    );
  }

  return (
    <Modal title={renewing ? 'Renew your subscription' : 'Subscribe to receive requests'} onClose={onClose} persistent>
      {!info && !error ? <p role="status" className="muted">Loading the plan…</p> : null}
      {info ? (
        <>
          <div className="plan">
            <span className="price price-lg">{money(info.price)}</span>
            <span className="muted">for {plural(info.period_days, 'day')}</span>
          </div>
          {renewing ? <p className="page-note">{validityLine(info)} Renewing adds {plural(info.period_days, 'day')} to what you have left.</p> : null}
          <ul className="perks">{PERKS.map((perk) => <li key={perk}><Check size={15} aria-hidden="true" />{perk}</li>)}</ul>
          {info.mode === 'test' ? <p className="hint">This is the built-in test gateway. No money moves.</p> : null}
          {info.mode === 'demo' ? <p className="hint">Demo mode: the subscription is activated without a payment and never ends.</p> : null}
          {info.mode === 'razorpay' ? <p className="hint">You pay securely on Razorpay with UPI, card or netbanking. Your card or bank details never reach us.</p> : null}
          {!info.configured ? <div className="notice" role="alert">Online payments are not set up yet. Please contact support.</div> : null}
        </>
      ) : null}
      {error ? <div className="notice" role="alert">{error}</div> : null}
      <div className="dialog-actions">
        <button type="button" onClick={onClose}>Not now</button>
        <button type="button" className={`primary ${busy ? 'busy' : ''}`} disabled={busy || !info || !info.configured} onClick={pay}>{buttonLabel}</button>
      </div>
    </Modal>
  );
}

/** Subscription status and payment history, shown on the My shop page. */
export function SubscriptionPanel({ user, refreshKey, onSubscribe }) {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    api.subscription(user.access_token).then(setInfo).catch((err) => setError(friendlyErrorMessage(err)));
  }, [user.access_token]);
  useEffect(load, [load, refreshKey]);

  return (
    <Panel
      title="Subscription"
      actions={info ? <button type="button" className="primary small" onClick={onSubscribe}>{info.subscribed ? 'Renew' : info.mode === 'demo' ? 'Activate' : 'Subscribe'}</button> : null}
    >
      {error ? <div className="notice" role="alert">{error}</div> : null}
      {info ? (
        <>
          <p className="subscription-state">
            <Status text={info.subscribed ? 'active' : 'expired'} />
            <span>{info.subscribed ? validityLine(info) : `Not subscribed. ${money(info.price)} for ${plural(info.period_days, 'day')} switches on requests and bidding.`}</span>
          </p>
          {info.history.length ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Paid on</th><th>Amount</th><th>Valid until</th><th>Reference</th></tr></thead>
                <tbody>
                  {info.history.map((row) => (
                    <tr key={row.id}>
                      <td data-label="Paid on">{dateTime(row.paid_at)}</td>
                      <td data-label="Amount">{money(row.amount)}</td>
                      <td data-label="Valid until">{dateTime(row.valid_until)}</td>
                      <td data-label="Reference">{row.reference || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="muted-small">No payments yet.</p>}
        </>
      ) : !error ? <p role="status" className="muted">Loading…</p> : null}
    </Panel>
  );
}
