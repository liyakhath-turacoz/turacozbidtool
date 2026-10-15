import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Gift, MapPin, Pause, Pencil, Phone, Play, Plus, Tag, Trash2 } from 'lucide-react';
import { api } from './api.js';
import { dateTime, friendlyErrorMessage, plural } from './format.js';
import { CopyButton, Empty, Modal, Page, Section, Status, useConfirm } from './ui.jsx';

const KINDS = [
  { key: 'percent', label: 'Percentage off', hint: 'For example 10 for 10% off.', unit: '%' },
  { key: 'amount', label: 'Amount off', hint: 'Rupees taken off the price.', unit: 'Rs.' },
  { key: 'special_price', label: 'Special price', hint: 'The price a buyer pays during the offer.', unit: 'Rs.' },
  { key: 'gift', label: 'Free gift', hint: 'Something extra with the purchase.' },
  { key: 'other', label: 'Something else', hint: 'Describe it in the details, like free installation or an exchange bonus.' },
];

/** `datetime-local` wants local time without a zone; the server wants an exact moment. */
function toInputValue(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function inDays(days) {
  return toInputValue(new Date(Date.now() + days * 86400000).toISOString());
}

function productLabel(product) {
  return product.name || [product.brand, product.model].filter(Boolean).join(' ');
}

function ProductChips({ products, total }) {
  if (!products?.length) return null;
  const more = (total || products.length) - products.length;
  return (
    <ul className="offer-products" aria-label="Products this offer covers">
      {products.map((product) => <li key={product.id}>{productLabel(product)}</li>)}
      {more > 0 ? <li className="more">+{more} more</li> : null}
    </ul>
  );
}

/** A live offer as the buyer sees it: what you get, until when, from whom, and how to reach them. */
export function PromotionCard({ offer }) {
  const shop = offer.shop || {};
  return (
    <article className="offer-card">
      <header>
        <span className="offer-headline"><Gift size={16} aria-hidden="true" /> {offer.headline}</span>
        <span className="offer-ends">Ends {dateTime(offer.ends_at)}</span>
      </header>
      <h3>{offer.title}</h3>
      {offer.details ? <p className="offer-details">{offer.details}</p> : null}
      <ProductChips products={offer.products} total={offer.product_count} />
      {offer.promo_code ? (
        <p className="promo-code">
          <Tag size={14} aria-hidden="true" /> Promo code <strong>{offer.promo_code}</strong>
          <CopyButton value={offer.promo_code} label="promo code" />
        </p>
      ) : null}
      <footer>
        <strong>{shop.name}</strong>
        {shop.address ? <span><MapPin size={13} aria-hidden="true" /> {shop.address}</span> : null}
        {shop.phone ? <span><Phone size={13} aria-hidden="true" /> <a href={`tel:${shop.phone}`}>{shop.phone}</a></span> : null}
      </footer>
    </article>
  );
}

/** Offers on one product: shown while the buyer looks at it or sets up a request. Renders nothing when there are none. */
export function ProductDeals({ token, productId, compact = false }) {
  const [offers, setOffers] = useState([]);
  useEffect(() => {
    let current = true;
    setOffers([]);
    api.buyerPromotions(token, { scope: 'product', product_id: productId })
      .then((result) => { if (current) setOffers(result.offers || []); })
      .catch(() => { /* Deals are a bonus; the page works without them. */ });
    return () => { current = false; };
  }, [token, productId]);
  if (!offers.length) return null;
  return (
    <section className={`product-deals ${compact ? 'compact' : ''}`} aria-label="Offers on this product">
      <h3>{plural(offers.length, 'offer')} on this product</h3>
      <div className="offer-list">{offers.map((offer) => <PromotionCard key={offer.id} offer={offer} />)}</div>
    </section>
  );
}

/** How many live offers each product on screen has, for a small badge on the product card. */
export function useDealCounts(token, productIds) {
  const [counts, setCounts] = useState({});
  const key = productIds.join(',');
  useEffect(() => {
    if (!productIds.length) return undefined;
    let current = true;
    // Ask in groups the server accepts, and only for what is not known yet.
    const unknown = productIds.filter((id) => counts[id] === undefined);
    if (!unknown.length) return undefined;
    const groups = [];
    for (let index = 0; index < unknown.length; index += 60) groups.push(unknown.slice(index, index + 60));
    Promise.all(groups.map((group) => api.promotionSummary(token, group).then((found) => ({ group, found })).catch(() => ({ group, found: {} }))))
      .then((results) => {
        if (!current) return;
        setCounts((old) => {
          const next = { ...old };
          results.forEach(({ group, found }) => group.forEach((id) => { next[id] = found[id] || 0; }));
          return next;
        });
      });
    return () => { current = false; };
    // `counts` is read to skip known products; including it would refetch after every answer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, key]);
  return counts;
}

/** The buyer's own deals page: what is on offer for the products they chose, and for everything nearby. */
export function BuyerDealsPage({ user, setTab }) {
  const token = user.access_token;
  const [scope, setScope] = useState('selected');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let current = true;
    setResult(null);
    setError('');
    api.buyerPromotions(token, { scope })
      .then((found) => { if (current) setResult(found); })
      .catch((problem) => { if (current) setError(friendlyErrorMessage(problem)); });
    return () => { current = false; };
  }, [token, scope]);

  const offers = result?.offers || [];
  return (
    <Page>
      <Section title="Deals" subtitle="Offers from shops that sell what you are looking at, and that deliver to your area." />
      <div className="tab-row" role="group" aria-label="Which deals to show">
        <button type="button" className={scope === 'selected' ? 'active' : ''} aria-pressed={scope === 'selected'} onClick={() => setScope('selected')}>On my products</button>
        <button type="button" className={scope === 'nearby' ? 'active' : ''} aria-pressed={scope === 'nearby'} onClick={() => setScope('nearby')}>All near me</button>
      </div>
      {error ? <div className="notice" role="alert">{error}</div> : null}
      {!result && !error ? <p role="status" className="muted">Loading deals…</p> : null}
      {result?.needs_location ? (
        <Empty title="Add a location to see deals" hint="Offers depend on which shops reach you, so we need a pin on the map first." action={<button type="button" className="primary" onClick={() => setTab(6)}>Add location</button>} />
      ) : null}
      {result && !result.needs_location && !offers.length ? (
        <Empty
          title={scope === 'selected' ? 'No offers on your products right now' : 'No offers near you right now'}
          hint={scope === 'selected' ? 'Offers on products in your cart or in your open requests show up here. Add products to your cart to follow them.' : 'Shops publish offers from time to time. Check back soon.'}
          action={<button type="button" onClick={() => (scope === 'selected' ? setScope('nearby') : setTab(0))}>{scope === 'selected' ? 'See all deals near me' : 'Browse products'}</button>}
        />
      ) : null}
      <div className="offer-list">{offers.map((offer) => <PromotionCard key={offer.id} offer={offer} />)}</div>
    </Page>
  );
}

const BLANK = () => ({
  title: '',
  offer_type: 'percent',
  offer_value: '',
  gift_text: '',
  details: '',
  promo_code: '',
  starts_at: toInputValue(new Date().toISOString()),
  ends_at: inDays(14),
  product_ids: [],
});

function OfferForm({ token, offer, onClose, onSaved }) {
  const [form, setForm] = useState(() => (offer ? {
    title: offer.title,
    offer_type: offer.offer_type,
    offer_value: offer.offer_value ? String(Number(offer.offer_value)) : '',
    gift_text: offer.gift_text || '',
    details: offer.details || '',
    promo_code: offer.promo_code || '',
    starts_at: toInputValue(offer.starts_at),
    ends_at: toInputValue(offer.ends_at),
    product_ids: offer.product_ids || [],
  } : BLANK()));
  const [products, setProducts] = useState(null);
  const [filter, setFilter] = useState('');
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const kind = KINDS.find((item) => item.key === form.offer_type);
  const update = (key, value) => setForm((old) => ({ ...old, [key]: value }));

  useEffect(() => {
    api.dealerProducts(token, { limit: 200 }).then(setProducts).catch((problem) => setFailure(friendlyErrorMessage(problem)));
  }, [token]);

  const shown = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return (products?.items || []).filter((product) => !needle || `${productLabel(product)} ${product.brand || ''} ${product.model || ''}`.toLowerCase().includes(needle));
  }, [products, filter]);

  const toggle = (id) => update('product_ids', form.product_ids.includes(id) ? form.product_ids.filter((item) => item !== id) : [...form.product_ids, id]);
  const allShownChosen = shown.length > 0 && shown.every((product) => form.product_ids.includes(product.id));
  const toggleShown = () => update('product_ids', allShownChosen
    ? form.product_ids.filter((id) => !shown.some((product) => product.id === id))
    : [...new Set([...form.product_ids, ...shown.map((product) => product.id)])]);

  const validate = () => {
    const found = {};
    if (form.title.trim().length < 3) found.title = 'Give the offer a short title, at least 3 characters.';
    if (['percent', 'amount', 'special_price'].includes(form.offer_type)) {
      const value = Number(form.offer_value);
      if (!Number.isFinite(value) || value <= 0) found.offer_value = 'Enter a number greater than 0.';
      else if (form.offer_type === 'percent' && value > 90) found.offer_value = 'A percentage offer can be at most 90%.';
    }
    if (form.offer_type === 'gift' && form.gift_text.trim().length < 2) found.gift_text = 'Say what the free gift is.';
    if (form.offer_type === 'other' && form.details.trim().length < 10) found.details = 'Describe the offer so buyers know what they get.';
    if (!form.ends_at || !toIso(form.ends_at)) found.ends_at = 'Choose when the offer ends.';
    else if (new Date(form.ends_at) <= new Date()) found.ends_at = 'The end must be in the future.';
    else if (form.starts_at && new Date(form.ends_at) <= new Date(form.starts_at)) found.ends_at = 'The offer must end after it starts.';
    if (!form.product_ids.length) found.product_ids = 'Choose at least one product this offer applies to.';
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!validate()) return;
    setBusy(true);
    setFailure('');
    const payload = {
      title: form.title.trim(),
      offer_type: form.offer_type,
      offer_value: ['percent', 'amount', 'special_price'].includes(form.offer_type) ? Number(form.offer_value) : null,
      gift_text: form.offer_type === 'gift' ? form.gift_text.trim() : '',
      details: form.details.trim(),
      promo_code: form.promo_code.trim(),
      starts_at: toIso(form.starts_at),
      ends_at: toIso(form.ends_at),
      product_ids: form.product_ids,
    };
    try {
      if (offer) await api.updatePromotion(token, offer.id, payload);
      else await api.createPromotion(token, payload);
      onSaved(offer ? 'Offer updated.' : 'Offer published. Buyers who can be served by your shop will see it.');
    } catch (problem) {
      setFailure(friendlyErrorMessage(problem));
    } finally {
      setBusy(false);
    }
  };

  const noProducts = products && !products.items.length;
  return (
    <Modal title={offer ? 'Edit offer' : 'New offer'} onClose={onClose} wide>
      <form className="bid-sheet offer-form" onSubmit={submit} noValidate>
        {failure ? <div className="notice" role="alert">{failure}</div> : null}
        <div className="form-grid">
          <div className="field wide">
            <label htmlFor="offer-title">Offer title</label>
            <input id="offer-title" autoComplete="off" value={form.title} aria-invalid={Boolean(errors.title)} onChange={(event) => update('title', event.target.value)} />
            {errors.title ? <p className="field-error" role="alert">{errors.title}</p> : null}
          </div>
          <div className="field">
            <label htmlFor="offer-type">What buyers get</label>
            <select id="offer-type" value={form.offer_type} onChange={(event) => update('offer_type', event.target.value)}>
              {KINDS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
            </select>
            <p className="hint">{kind.hint}</p>
          </div>
          {kind.unit ? (
            <div className="field">
              <label htmlFor="offer-value">{kind.label} ({kind.unit})</label>
              <input id="offer-value" inputMode="decimal" autoComplete="off" value={form.offer_value} aria-invalid={Boolean(errors.offer_value)} onChange={(event) => update('offer_value', event.target.value)} />
              {errors.offer_value ? <p className="field-error" role="alert">{errors.offer_value}</p> : null}
            </div>
          ) : null}
          {form.offer_type === 'gift' ? (
            <div className="field">
              <label htmlFor="offer-gift">Free gift</label>
              <input id="offer-gift" autoComplete="off" value={form.gift_text} aria-invalid={Boolean(errors.gift_text)} onChange={(event) => update('gift_text', event.target.value)} />
              {errors.gift_text ? <p className="field-error" role="alert">{errors.gift_text}</p> : null}
            </div>
          ) : null}
          <div className="field">
            <label htmlFor="offer-starts">Starts</label>
            <input id="offer-starts" type="datetime-local" value={form.starts_at} onChange={(event) => update('starts_at', event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="offer-ends">Ends</label>
            <input id="offer-ends" type="datetime-local" value={form.ends_at} aria-invalid={Boolean(errors.ends_at)} onChange={(event) => update('ends_at', event.target.value)} />
            {errors.ends_at ? <p className="field-error" role="alert">{errors.ends_at}</p> : <p className="hint">An offer can run for up to 180 days.</p>}
          </div>
          <div className="field">
            <label htmlFor="offer-code">Promo code (optional)</label>
            <input id="offer-code" autoComplete="off" value={form.promo_code} onChange={(event) => update('promo_code', event.target.value.toUpperCase())} />
            <p className="hint">Buyers show this at your shop to claim the offer.</p>
          </div>
          <div className="field wide">
            <label htmlFor="offer-details">Terms and details {form.offer_type === 'other' ? '' : '(optional)'}</label>
            <textarea id="offer-details" value={form.details} aria-invalid={Boolean(errors.details)} onChange={(event) => update('details', event.target.value)} />
            {errors.details ? <p className="field-error" role="alert">{errors.details}</p> : <p className="hint">Conditions buyers should know, like payment mode or stock limits.</p>}
          </div>
        </div>

        <fieldset className="field wide offer-picker">
          <legend>Products this offer applies to</legend>
          {noProducts ? (
            <p className="muted">You have not listed any products yet. Add them under My products first, then come back to publish an offer.</p>
          ) : (
            <>
              <div className="toolbar">
                <input type="search" aria-label="Filter your products" placeholder="Filter your products" value={filter} onChange={(event) => setFilter(event.target.value)} />
                <button type="button" className="small" disabled={!shown.length} onClick={toggleShown}>{allShownChosen ? 'Clear these' : 'Choose all shown'}</button>
              </div>
              <p className="hint" role="status">{plural(form.product_ids.length, 'product')} chosen{products && products.total > products.items.length ? `. Showing your newest ${products.items.length} of ${products.total}.` : '.'}</p>
              <ul className="pick-list">
                {!products ? <li className="muted">Loading your products…</li> : null}
                {shown.map((product) => (
                  <li key={product.id}>
                    <label className="check">
                      <input type="checkbox" checked={form.product_ids.includes(product.id)} onChange={() => toggle(product.id)} />
                      <span>{productLabel(product)} <span className="muted">{[product.brand, product.model].filter(Boolean).join(' ')}</span></span>
                    </label>
                  </li>
                ))}
              </ul>
            </>
          )}
          {errors.product_ids ? <p className="field-error" role="alert">{errors.product_ids}</p> : null}
        </fieldset>

        <div className="dialog-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary" disabled={busy || noProducts}>{busy ? 'Saving…' : offer ? 'Save changes' : 'Publish offer'}</button>
        </div>
      </form>
    </Modal>
  );
}

const PHASE_NOTE = {
  live: 'Buyers can see this now.',
  scheduled: 'Starts on its date. Buyers cannot see it yet.',
  ended: 'This offer has ended.',
  paused: 'Hidden from buyers until you resume it.',
};

/** The shop's own page for promotional offers: publish, edit, pause and delete. */
export function DealerOffersPage({ user, data, subscribe, setTab }) {
  const token = user.access_token;
  const confirm = useConfirm();
  const [offers, setOffers] = useState(null);
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState({ kind: '', text: '' });
  const subscribed = Boolean(data?.dealerSubscribed ?? true);

  const reload = useCallback(() => api.dealerPromotions(token).then(setOffers).catch((problem) => setNotice({ kind: 'error', text: friendlyErrorMessage(problem) })), [token]);
  useEffect(() => { reload(); }, [reload]);

  const act = async (work, success) => {
    try {
      await work();
      setNotice({ kind: 'success', text: success });
      reload();
    } catch (problem) {
      setNotice({ kind: 'error', text: friendlyErrorMessage(problem) });
    }
  };
  const remove = async (offer) => {
    const ok = await confirm({
      title: `Delete “${offer.title}”?`,
      body: <p>Buyers will no longer see it. This cannot be undone.</p>,
      confirmLabel: 'Delete offer',
      cancelLabel: 'Keep it',
      tone: 'danger',
    });
    if (ok) act(() => api.deletePromotion(token, offer.id), 'Offer deleted.');
  };

  const live = (offers || []).filter((offer) => offer.phase === 'live').length;
  return (
    <Page>
      <Section
        title="My offers"
        subtitle="Publish a deal on the products you sell. Buyers see it when they look at those products, as long as your shop serves their area."
        actions={<button type="button" className="primary" onClick={() => setEditing({})}><Plus size={16} aria-hidden="true" /> New offer</button>}
      />
      {notice.text ? <div className={`notice ${notice.kind === 'success' ? 'success' : ''}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.text}</div> : null}
      {!subscribed ? (
        <div className="page-banner warn">
          <div><strong>Your subscription has ended.</strong><p>Buyers cannot see your offers until you renew.</p></div>
          <button type="button" className="primary" onClick={subscribe}>Renew</button>
        </div>
      ) : null}
      {offers === null ? <p role="status" className="muted">Loading your offers…</p> : null}
      {offers && !offers.length ? (
        <Empty
          title="You have not published any offers"
          hint="Offers apply to products on your list. Add products first if you have not, then publish a festival sale, a special price or a free gift."
          action={<div className="row-actions"><button type="button" className="primary" onClick={() => setEditing({})}>Create an offer</button><button type="button" onClick={() => setTab(4)}>My products</button></div>}
        />
      ) : null}
      {offers?.length ? <p className="muted-small">{plural(live, 'offer')} live now, {offers.length} in total.</p> : null}
      <div className="offer-list">
        {(offers || []).map((offer) => (
          <article key={offer.id} className={`offer-card mine ${offer.phase}`}>
            <header>
              <span className="offer-headline"><Gift size={16} aria-hidden="true" /> {offer.headline}</span>
              <Status text={offer.phase} />
            </header>
            <h3>{offer.title}</h3>
            <p className="muted-small">{dateTime(offer.starts_at)} to {dateTime(offer.ends_at)}. {PHASE_NOTE[offer.phase]}</p>
            {offer.details ? <p className="offer-details">{offer.details}</p> : null}
            <ProductChips products={offer.products} total={offer.product_count} />
            {offer.promo_code ? <p className="promo-code"><Tag size={14} aria-hidden="true" /> Promo code <strong>{offer.promo_code}</strong></p> : null}
            <footer className="offer-actions">
              <button type="button" className="small" onClick={() => setEditing(offer)}><Pencil size={14} aria-hidden="true" /> Edit</button>
              {offer.phase !== 'ended' ? (
                offer.status === 'paused'
                  ? <button type="button" className="small" onClick={() => act(() => api.setPromotionStatus(token, offer.id, 'active'), 'Offer resumed.')}><Play size={14} aria-hidden="true" /> Resume</button>
                  : <button type="button" className="small" onClick={() => act(() => api.setPromotionStatus(token, offer.id, 'paused'), 'Offer paused. Buyers cannot see it.')}><Pause size={14} aria-hidden="true" /> Pause</button>
              ) : null}
              <button type="button" className="small danger" aria-label={`Delete ${offer.title}`} onClick={() => remove(offer)}><Trash2 size={14} aria-hidden="true" /> Delete</button>
            </footer>
          </article>
        ))}
      </div>
      {editing ? (
        <OfferForm
          token={token}
          offer={editing.id ? editing : null}
          onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); setNotice({ kind: 'success', text }); reload(); }}
        />
      ) : null}
    </Page>
  );
}
