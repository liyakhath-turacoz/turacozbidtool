import React, { useMemo, useState } from 'react';
import { Gift, MapPin, Navigation, Package, ShieldCheck, Truck, Wrench } from 'lucide-react';
import { Countdown, Modal, ProductImage, Status } from './ui.jsx';
import { dateTime, formatDelivery, isLive, money, plural, standingFor, text } from './format.js';

/* ------------------------------------------------------------------ */
/* Shared helpers                                                      */
/* ------------------------------------------------------------------ */

export { isLive, formatDelivery, standingFor };

export function Standing({ standing }) {
  if (standing.kind === 'lead') return <span className="standing lead">You are the lowest bid</span>;
  if (standing.kind === 'trail') return <span className="standing trail">{money(standing.gap)} above the lowest</span>;
  return <span className="standing solo">No other bids yet</span>;
}

export function BrandMark({ className = 'brand-mark' }) {
  return (
    <svg className={className} viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 8h26a2 2 0 0 1 2 2v7a3 3 0 0 0 0 6v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7a3 3 0 0 0 0-6v-7a2 2 0 0 1 2-2z" />
      <path d="M12 14h13" />
      <path d="M11 20h18" strokeDasharray="2.6 2.6" strokeWidth="1.8" />
      <path d="M12 27h8" />
    </svg>
  );
}

function QuickPicks({ options, value, onPick, label }) {
  return (
    <div className="quick-picks" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option} type="button" className="small" aria-pressed={value === option} onClick={() => onPick(option)}>{option}</button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Dealer: request slip                                                */
/* ------------------------------------------------------------------ */

export function RequestSlip({ request, onBid, blocked }) {
  const offers = Number(request.offers_count || 0);
  const hasBest = request.best_amount !== null && request.best_amount !== undefined && offers > 0;
  const distance = request.distance_km;
  return (
    <article className="slip" aria-label={`${request.product}, ${plural(Number(request.quantity || 1), 'unit')}`}>
      <div className="slip-top">
        <ProductImage product={request} className="slip-thumb" iconSize={22} />
        <div className="slip-title">
          {request.brand ? <small>{request.brand}</small> : null}
          <h3>{request.product}</h3>
        </div>
        <Countdown until={request.expires_at} />
      </div>
      <ul className="slip-meta">
        <li><Package size={14} aria-hidden="true" />{plural(Number(request.quantity || 1), 'unit')}</li>
        {request.buyer_area ? <li><MapPin size={14} aria-hidden="true" />{request.buyer_area}</li> : null}
        {distance !== null && distance !== undefined ? <li><Navigation size={14} aria-hidden="true" />{Number(distance) < 1 ? 'Under 1 km away' : `${distance} km away`}</li> : null}
      </ul>
      {request.buyer_notes ? <p className="slip-note">“{request.buyer_notes}”</p> : null}
      <hr className="slip-tear" />
      <div className="slip-foot">
        <div className="slip-price">
          {hasBest ? (
            <>
              <small>Lowest of {plural(offers, 'bid')} so far</small>
              <span className="price">{money(request.best_amount)}</span>
            </>
          ) : (
            <>
              <small>No bids yet</small>
              <span className="standing solo">Be the first to quote</span>
            </>
          )}
        </div>
        <div className="slip-actions">
          <button type="button" className="primary" disabled={Boolean(blocked)} onClick={() => onBid(request)}>Submit bid</button>
        </div>
        {blocked ? <p className="field-hint slip-blocked">{blocked}</p> : null}
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ */
/* Dealer: a bid I have placed                                         */
/* ------------------------------------------------------------------ */

export function MyBidSlip({ bid, standing, onRevise, onWithdraw, onDetails }) {
  const where = [bid.buyer_area, bid.buyer_city].filter(Boolean).join(', ');
  return (
    <article className={`slip ${standing.kind === 'lead' ? 'leading' : standing.kind === 'trail' ? 'behind' : ''}`} aria-label={`Your bid on ${bid.product}`}>
      <div className="slip-top plain">
        <div className="slip-title">
          <small>{plural(Number(bid.quantity || 1), 'unit')}{where ? `, ${where}` : ''}</small>
          <h3>{bid.product}</h3>
        </div>
        <Countdown until={bid.ends_at} />
      </div>
      <dl className="terms">
        <div><dt>Delivery</dt><dd>{formatDelivery(bid.delivery_time)}</dd></div>
        <div><dt>Warranty</dt><dd>{text(bid.warranty_text) || 'None'}</dd></div>
        {Number(bid.installation_included) ? <div><dt>Installation</dt><dd>Included</dd></div> : null}
      </dl>
      <hr className="slip-tear" />
      <div className="slip-foot">
        <div className="slip-price">
          <small>Your bid</small>
          <span className="price">{money(bid.amount)}</span>
          <Standing standing={standing} />
        </div>
        <div className="slip-actions">
          <button type="button" className="primary" onClick={() => onRevise(bid)}>Revise bid</button>
          <button type="button" onClick={() => onDetails(bid)}>Details</button>
          <button type="button" className="danger" onClick={() => onWithdraw(bid)}>Withdraw</button>
        </div>
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ */
/* Buyer: one dealer's offer                                           */
/* ------------------------------------------------------------------ */

export function OfferSlip({ offer, quantity, isLowest, canAccept, onAccept }) {
  const savings = Number(offer.discount_amount || 0);
  const units = Number(quantity || offer.quantity || 1);
  const live = isLive(offer);
  const gifts = text(offer.free_gifts);
  const services = text(offer.extra_services);
  return (
    <article className={`slip ${isLowest && live ? 'is-lowest' : ''}`} aria-label={`Offer from ${offer.dealer || 'dealer'}`}>
      <div className="slip-top plain">
        <div className="slip-title">
          {isLowest && live ? <span className="slip-flag">Lowest price</span> : <small>Offer from</small>}
          <h3>{offer.dealer || 'Dealer'}</h3>
        </div>
        {!live ? <Status text={offer.status} /> : null}
      </div>
      <div className="offer-price">
        <span className={`price price-lg ${isLowest && live ? 'price-hl' : ''}`}>{money(offer.amount)}</span>
        <small>
          for {plural(units, 'unit')}
          {units > 1 ? `, ${money(Number(offer.amount) / units)} each` : ''}
          {savings > 0 ? `, includes ${money(savings)} savings` : ''}
        </small>
      </div>
      <dl className="terms">
        <div><dt><Truck size={13} aria-hidden="true" /> Delivery</dt><dd>{formatDelivery(offer.delivery_time)}</dd></div>
        <div><dt><ShieldCheck size={13} aria-hidden="true" /> Warranty</dt><dd>{text(offer.warranty_text) || 'None'}</dd></div>
        <div><dt><Wrench size={13} aria-hidden="true" /> Installation</dt><dd>{Number(offer.installation_included) ? 'Included' : 'Not included'}</dd></div>
        {gifts ? <div><dt><Gift size={13} aria-hidden="true" /> Free gifts</dt><dd>{gifts}</dd></div> : null}
        {services ? <div><dt>Extra services</dt><dd>{services}</dd></div> : null}
      </dl>
      {text(offer.notes) ? <p className="slip-note">“{text(offer.notes)}”</p> : null}
      {live ? (
        <>
          <hr className="slip-tear" />
          <div className="slip-foot">
            <div className="slip-price">
              {!offer.selectable ? <small>This dealer can no longer be selected</small> : <small>Dealer contact details unlock after you accept</small>}
            </div>
            <div className="slip-actions">
              <button type="button" className="primary" disabled={!canAccept || !offer.selectable} onClick={() => onAccept(offer)}>Accept offer</button>
            </div>
          </div>
        </>
      ) : null}
    </article>
  );
}

/* ------------------------------------------------------------------ */
/* Buyer: one of my requests                                           */
/* ------------------------------------------------------------------ */

export function BuyerRequestSlip({ request, offers, onCompare, onCancel }) {
  const live = offers.filter(isLive);
  const lowest = live.length ? Math.min(...live.map((offer) => Number(offer.amount))) : null;
  const where = [request.buyer_area, request.buyer_city].filter(Boolean).join(', ');
  return (
    <article className="slip" aria-label={`Request for ${request.product}`}>
      <div className="slip-top">
        <ProductImage product={request} className="slip-thumb" iconSize={22} />
        <div className="slip-title">
          {request.brand ? <small>{request.brand}</small> : null}
          <h3>{request.product}</h3>
        </div>
        {request.status === 'active' ? <Countdown until={request.expires_at} /> : <Status text={request.status} />}
      </div>
      <ul className="slip-meta">
        <li><Package size={14} aria-hidden="true" />{plural(Number(request.quantity || 1), 'unit')}</li>
        {where ? <li><MapPin size={14} aria-hidden="true" />{where}</li> : null}
      </ul>
      <hr className="slip-tear" />
      <div className="slip-foot">
        <div className="slip-price">
          {lowest !== null ? (
            <>
              <small>Lowest of {plural(live.length, 'offer')}</small>
              <span className="price">{money(lowest)}</span>
            </>
          ) : (
            <>
              <small>Waiting for offers</small>
              <span className="muted-small">Nearby shops have been notified.</span>
            </>
          )}
        </div>
        <div className="slip-actions">
          {onCancel ? <button type="button" className="danger" onClick={() => onCancel(request)}>Cancel request</button> : null}
          <button type="button" className="primary" onClick={() => onCompare(request)}>{live.length ? `Compare ${plural(live.length, 'offer')}` : 'View request'}</button>
        </div>
      </div>
    </article>
  );
}

/* ------------------------------------------------------------------ */
/* Dealer: bid sheet                                                   */
/* ------------------------------------------------------------------ */

const DELIVERY_PICKS = ['Same day', 'Next day', '2-3 days', '1 week'];
const WARRANTY_PICKS = ['Manufacturer warranty', '6 months', '1 year', '2 years'];

export function BidSheet({ request, bid, allBids = [], subscribed = true, rules = {}, onClose, onSubmit }) {
  const editing = Boolean(bid);
  const quantity = Number(request.quantity || bid?.quantity || 1);
  const [form, setForm] = useState({
    amount: bid?.amount ? String(Number(bid.amount)) : '',
    discount_amount: Number(bid?.discount_amount) ? String(Number(bid.discount_amount)) : '',
    warranty_text: bid?.warranty_text || '',
    delivery_time: bid?.delivery_time ? formatDelivery(bid.delivery_time) : '',
    installation_included: Boolean(Number(bid?.installation_included)),
    free_gifts: bid?.free_gifts || '',
    extra_services: bid?.extra_services || '',
    notes: bid?.notes || '',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const update = (key, value) => {
    setForm((old) => ({ ...old, [key]: value }));
    setErrors((old) => (old[key] ? { ...old, [key]: undefined } : old));
  };

  const area = request.buyer_area || [bid?.buyer_area, bid?.buyer_city].filter(Boolean).join(', ');
  const closes = request.expires_at || bid?.ends_at;
  const requestId = request.id || bid?.bid_request_id;
  const competing = useMemo(() => allBids.filter((other) => (
    other.bid_request_id === requestId && !other.is_mine && isLive(other)
  )), [allBids, requestId]);
  const lowest = competing.length
    ? Math.min(...competing.map((other) => Number(other.amount)))
    : (request.best_amount !== null && request.best_amount !== undefined && Number(request.offers_count) > 0 ? Number(request.best_amount) : null);

  const amount = Number(form.amount);
  const amountValid = form.amount !== '' && Number.isFinite(amount) && amount > 0;
  const step = Number(rules.min_bidding_increment || 0);

  const validate = () => {
    const next = {};
    if (!amountValid) next.amount = 'Enter the final price as a number greater than 0.';
    if (form.discount_amount !== '' && (!Number.isFinite(Number(form.discount_amount)) || Number(form.discount_amount) < 0)) {
      next.discount_amount = 'Enter savings as a number, or leave it empty.';
    }
    if (!text(form.delivery_time)) next.delivery_time = 'Tell the buyer when they can expect delivery.';
    return next;
  };

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) {
      document.getElementById(`bid-${Object.keys(found)[0]}`)?.focus();
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({
        bid_request_id: requestId,
        amount,
        discount_amount: form.discount_amount === '' ? 0 : Number(form.discount_amount),
        warranty_text: form.warranty_text.trim(),
        delivery_time: form.delivery_time.trim(),
        installation_included: form.installation_included,
        free_gifts: form.free_gifts.trim(),
        extra_services: form.extra_services.trim(),
        notes: form.notes.trim(),
      });
    } finally {
      setSubmitting(false);
    }
  };

  let comparison = null;
  if (amountValid && lowest !== null) {
    comparison = amount < lowest
      ? { tone: 'lead', text: `You would be the lowest bid, ${money(lowest - amount)} under the current lowest.` }
      : amount === lowest
        ? { tone: 'solo', text: 'This matches the current lowest bid. Better terms can still win the buyer.' }
        : { tone: 'trail', text: `${money(amount - lowest)} above the current lowest. Better terms can still win the buyer.` };
  }

  return (
    <Modal title={editing ? 'Revise your bid' : 'Submit a bid'} onClose={onClose} persistent>
      <form className="bid-sheet" onSubmit={submit} noValidate>
        <div className="sheet-summary">
          <div className="sheet-summary-top">
            <ProductImage product={request.image_url ? request : { image_url: '' }} className="slip-thumb" iconSize={22} />
            <div>
              {request.brand ? <span className="muted-small">{request.brand}</span> : null}
              <h3>{request.product || bid?.product}</h3>
            </div>
          </div>
          <div className="sheet-facts">
            <span><Package size={14} aria-hidden="true" />{plural(quantity, 'unit')}</span>
            {area ? <span><MapPin size={14} aria-hidden="true" />{area}</span> : null}
            {request.distance_km !== null && request.distance_km !== undefined ? <span><Navigation size={14} aria-hidden="true" />{Number(request.distance_km) < 1 ? 'Under 1 km away' : `${request.distance_km} km away`}</span> : null}
            {closes ? <Countdown until={closes} /> : null}
          </div>
          {request.buyer_notes ? <p className="slip-note sheet-note">“{request.buyer_notes}”</p> : null}
          <div className="beat-line">
            <small>{lowest !== null ? `Lowest of ${plural(competing.length || Number(request.offers_count) || 1, 'other bid')}` : 'No other bids yet'}</small>
            {lowest !== null ? <span className="price price-sm">{money(lowest)}</span> : <span className="standing solo">You can set the pace</span>}
          </div>
        </div>

        {!subscribed ? <div className="notice" role="alert">Your subscription is not active, so you cannot submit bids yet. Close this window and subscribe from the banner at the top.</div> : null}

        <div className="form-grid">
          <div className="field">
            <label htmlFor="bid-amount">Final total (Rs.)</label>
            <input id="bid-amount" inputMode="decimal" autoComplete="off" value={form.amount} aria-invalid={Boolean(errors.amount)} aria-describedby="bid-amount-hint" onChange={(event) => update('amount', event.target.value)} />
            <p id="bid-amount-hint" className="hint">{quantity > 1 ? `The price for all ${quantity} units together, discount included.` : 'The price you will charge, discount included.'}</p>
            {errors.amount ? <p className="field-error" role="alert">{errors.amount}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="bid-discount_amount">Savings included (Rs.)</label>
            <input id="bid-discount_amount" inputMode="decimal" autoComplete="off" value={form.discount_amount} aria-invalid={Boolean(errors.discount_amount)} aria-describedby="bid-discount-hint" onChange={(event) => update('discount_amount', event.target.value)} />
            <p id="bid-discount-hint" className="hint">Optional. How much cheaper this is than the usual price. Do not subtract it again.</p>
            {errors.discount_amount ? <p className="field-error" role="alert">{errors.discount_amount}</p> : null}
          </div>
        </div>

        {amountValid ? (
          <div className="total-preview" aria-live="polite">
            <span>
              Buyer sees <strong>{money(amount)}</strong>
              {quantity > 1 ? <> for {plural(quantity, 'unit')}, or <strong>{money(amount / quantity)}</strong> each</> : null}.
            </span>
            {comparison ? <span className={`standing ${comparison.tone}`}>{comparison.text}</span> : null}
          </div>
        ) : null}
        {editing && step > 0 ? <p className="hint">Platform rule: a revised price must be at least {money(step)} lower than your current bid.</p> : null}

        <div className="form-grid">
          <div className="field">
            <label htmlFor="bid-delivery_time">Delivery time</label>
            <input id="bid-delivery_time" autoComplete="off" value={form.delivery_time} aria-invalid={Boolean(errors.delivery_time)} onChange={(event) => update('delivery_time', event.target.value)} />
            <QuickPicks label="Common delivery times" options={DELIVERY_PICKS} value={form.delivery_time} onPick={(value) => update('delivery_time', value)} />
            {errors.delivery_time ? <p className="field-error" role="alert">{errors.delivery_time}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="bid-warranty_text">Warranty</label>
            <input id="bid-warranty_text" autoComplete="off" value={form.warranty_text} onChange={(event) => update('warranty_text', event.target.value)} />
            <QuickPicks label="Common warranty terms" options={WARRANTY_PICKS} value={form.warranty_text} onPick={(value) => update('warranty_text', value)} />
          </div>
        </div>

        <label className="check"><input type="checkbox" checked={form.installation_included} onChange={(event) => update('installation_included', event.target.checked)} /> Installation included</label>

        <details className="more-details" open={Boolean(form.free_gifts || form.extra_services || form.notes)}>
          <summary>Add gifts, services or a note</summary>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="bid-free_gifts">Free gifts</label>
              <input id="bid-free_gifts" value={form.free_gifts} onChange={(event) => update('free_gifts', event.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="bid-extra_services">Extra services</label>
              <input id="bid-extra_services" value={form.extra_services} onChange={(event) => update('extra_services', event.target.value)} />
            </div>
            <div className="field wide">
              <label htmlFor="bid-notes">Note to the buyer</label>
              <textarea id="bid-notes" value={form.notes} onChange={(event) => update('notes', event.target.value)} />
            </div>
          </div>
        </details>

        <div className="dialog-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={`primary ${submitting ? 'busy' : ''}`} disabled={submitting || !subscribed}>{submitting ? 'Sending...' : editing ? 'Update bid' : 'Submit bid'}</button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Buyer: start a bid                                                  */
/* ------------------------------------------------------------------ */

const EXPIRY_PRESETS = [
  [30, '30 minutes'],
  [60, '1 hour'],
  [120, '2 hours'],
  [240, '4 hours'],
  [720, '12 hours'],
  [1440, '24 hours'],
  [2880, '2 days'],
  [4320, '3 days'],
];

export function BidSetupModal({ product, locations, rules = {}, onClose, onStart, onAddLocation }) {
  const defaultLocation = locations.find((loc) => loc.is_default === true || loc.is_default === 1) || locations[0];
  const defaultMinutes = Math.round(Number(rules.expiry_hours ?? 24) * 60);
  const [form, setForm] = useState({
    quantity: String(product.bidQuantity || 1),
    expiry_minutes: defaultMinutes,
    notes: '',
    location_id: defaultLocation ? String(defaultLocation.location_id || defaultLocation.id) : '',
    skip_flagged_dealers: true,
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const update = (key, value) => {
    setForm((old) => ({ ...old, [key]: value }));
    setErrors((old) => (old[key] ? { ...old, [key]: undefined } : old));
  };

  const minMinutes = Number(rules.min_time_hours ?? (1 / 60)) * 60 - 1e-9;
  const maxMinutes = Number(rules.max_time_hours ?? 72) * 60 + 1e-9;
  const presets = [
    ...(import.meta.env.DEV ? [[1, '1 minute (testing)']] : []),
    ...EXPIRY_PRESETS,
    ...(EXPIRY_PRESETS.some(([minutes]) => minutes === defaultMinutes) || defaultMinutes === 1 ? [] : [[defaultMinutes, `${defaultMinutes} minutes`]]),
  ].filter(([minutes]) => minutes >= minMinutes && minutes <= maxMinutes).sort((a, b) => a[0] - b[0]);

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    const quantity = Number(form.quantity);
    const found = {};
    if (!form.location_id) found.location_id = 'Choose where this should be delivered.';
    if (!Number.isInteger(quantity) || quantity <= 0 || quantity > 100000) found.quantity = 'Enter a whole number from 1 to 100000.';
    setErrors(found);
    if (Object.keys(found).length) {
      document.getElementById(`setup-${Object.keys(found)[0]}`)?.focus();
      return;
    }
    setSubmitting(true);
    try {
      await onStart({
        product_id: product.id,
        quantity,
        location_id: form.location_id,
        skip_flagged_dealers: form.skip_flagged_dealers,
        expiry_minutes: Number(form.expiry_minutes || 1440),
        fields: form.notes.trim() ? { Notes: form.notes.trim() } : {},
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Start a bid" onClose={onClose} persistent>
      <form className="bid-sheet" onSubmit={submit} noValidate>
        <div className="sheet-summary">
          <div className="sheet-summary-top">
            <ProductImage product={product} className="slip-thumb" iconSize={22} />
            <div>
              {product.brand ? <span className="muted-small">{product.brand}</span> : null}
              <h3>{product.name}</h3>
            </div>
          </div>
          <p className="muted-small">Nearby shops will see this request and send their best final price. You choose the offer you like.</p>
        </div>

        {!locations.length ? (
          <div className="page-banner warn">
            <div>
              <strong>Add a delivery location first.</strong>
              <p>Shops are matched by distance, so we need a pinned location on the map.</p>
            </div>
            {onAddLocation ? <button type="button" className="primary" onClick={onAddLocation}>Add location</button> : null}
          </div>
        ) : null}

        <div className="form-grid">
          <div className="field">
            <label htmlFor="setup-quantity">Quantity</label>
            <input id="setup-quantity" type="number" min="1" inputMode="numeric" value={form.quantity} aria-invalid={Boolean(errors.quantity)} onChange={(event) => update('quantity', event.target.value)} />
            {errors.quantity ? <p className="field-error" role="alert">{errors.quantity}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="setup-location_id">Deliver to</label>
            <select id="setup-location_id" value={form.location_id} aria-invalid={Boolean(errors.location_id)} onChange={(event) => update('location_id', event.target.value)}>
              <option value="">{locations.length ? 'Choose a saved location' : 'No saved locations'}</option>
              {locations.map((loc) => <option key={loc.id} value={loc.location_id || loc.id}>{loc.label || loc.city}</option>)}
            </select>
            {errors.location_id ? <p className="field-error" role="alert">{errors.location_id}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="setup-expiry">Close bidding after</label>
            <select id="setup-expiry" value={form.expiry_minutes} onChange={(event) => update('expiry_minutes', Number(event.target.value))}>
              {presets.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <p className="hint">Shops can bid until then. Longer windows usually bring more offers.</p>
          </div>
          <label className="check field-aligned">
            <input type="checkbox" checked={form.skip_flagged_dealers} onChange={(event) => update('skip_flagged_dealers', event.target.checked)} />
            <span>Only invite shops in good standing</span>
          </label>
          <div className="field wide">
            <label htmlFor="setup-notes">Anything shops should know? (optional)</label>
            <textarea id="setup-notes" value={form.notes} onChange={(event) => update('notes', event.target.value)} placeholder="Preferred colour, delivery floor, exchange of an old unit..." />
          </div>
        </div>

        <div className="dialog-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={`primary ${submitting ? 'busy' : ''}`} disabled={submitting || !locations.length}>{submitting ? 'Starting...' : 'Start bid'}</button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Buyer: compare offers                                               */
/* ------------------------------------------------------------------ */

export function CompareOffersModal({ request, offers, onClose, onAccept, onCancel, winnerContact }) {
  const sorted = [...offers].sort((a, b) => Number(a.amount) - Number(b.amount));
  const liveOffers = sorted.filter(isLive);
  // Only call a price "lowest" when there is something to compare it with.
  const lowest = liveOffers.length > 1 ? Number(liveOffers[0].amount) : null;
  const open = request.status === 'active';
  return (
    <Modal title={request.product || request.product_name || 'Your request'} onClose={onClose} wide>
      <div className="info-badge-row">
        <span><Package size={14} aria-hidden="true" />{plural(Number(request.quantity || 1), 'unit')}</span>
        <Status text={request.status || 'active'} />
        {open ? <Countdown until={request.expires_at} /> : null}
        {open && onCancel ? <button type="button" className="danger small" onClick={onCancel}>Cancel request</button> : null}
      </div>
      {winnerContact}
      {sorted.length ? (
        <>
          {open && liveOffers.length > 1 ? <p className="muted-small">Offers are listed from the lowest price. Compare delivery and warranty before you accept.</p> : null}
          <div className="slip-grid">
            {sorted.map((offer) => (
              <OfferSlip key={offer.id} offer={offer} quantity={request.quantity} isLowest={lowest !== null && Number(offer.amount) === lowest} canAccept={open} onAccept={onAccept} />
            ))}
          </div>
        </>
      ) : (
        <div className="empty">
          <strong>No offers yet</strong>
          <p>Nearby shops have been notified. Offers appear here the moment they arrive{open ? `, and bidding closes ${dateTime(request.expires_at)}` : ''}.</p>
        </div>
      )}
    </Modal>
  );
}
