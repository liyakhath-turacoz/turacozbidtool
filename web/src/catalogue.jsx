import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Download, Search, Trash2, Upload } from 'lucide-react';
import { api } from './api.js';
import { friendlyErrorMessage, plural } from './format.js';
import { Empty, Page, Panel, Section, Status } from './ui.jsx';

const BLANK = { name: '', brand: '', model: '', mpn: '', gtin: '', category: '', item: '', description: '' };

function label(product) {
  return [product.brand, product.model].filter(Boolean).join(' ');
}

/** What happened to one product, in words. */
function describe(result) {
  const name = result.product?.name || result.input?.name || 'This product';
  if (result.status === 'created') return `Added “${name}”. It is now in the common catalogue, and on your list.`;
  if (result.status === 'linked') return `“${name}” is already in the catalogue, so we added it to your list instead of creating a copy.`;
  if (result.status === 'already_listed') return `“${name}” was already on your list. Nothing was duplicated.`;
  return result.message || '';
}

/** Several products look similar. The shop decides whether its product is one of them. */
function ReviewCard({ item, busy, onChoose }) {
  const input = item.input || {};
  return (
    <div className="review-card">
      <p><strong>{input.name}</strong> {label(input) ? <span className="muted">({label(input)})</span> : null}</p>
      <p className="muted-small">This looks like {item.candidates.length > 1 ? 'products' : 'a product'} already in the catalogue. Is yours one of them?</p>
      <ul className="candidate-list">
        {item.candidates.map((candidate) => (
          <li key={candidate.id}>
            <span><strong>{candidate.name}</strong> <span className="muted">{label(candidate)}</span></span>
            <button type="button" className="small primary" disabled={busy} onClick={() => onChoose(item, { action: 'link', product_id: candidate.id })}>Yes, this one</button>
          </li>
        ))}
      </ul>
      <button type="button" className="small" disabled={busy} onClick={() => onChoose(item, { action: 'create' })}>No, mine is a different product</button>
    </div>
  );
}

export function DealerProductsPage({ user, data, setTab }) {
  const token = user.access_token;
  const [categories, setCategories] = useState([]);
  const [list, setList] = useState({ total: 0, items: [] });
  const [filter, setFilter] = useState('');
  const [loadingList, setLoadingList] = useState(true);
  const [notice, setNotice] = useState({ kind: '', text: '' });
  const [busy, setBusy] = useState(false);

  // search the common catalogue
  const [query, setQuery] = useState('');
  const [found, setFound] = useState(null);
  const [searching, setSearching] = useState(false);

  // type a product in
  const [form, setForm] = useState(BLANK);
  const [review, setReview] = useState(null);

  // upload
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const fileInput = useRef(null);

  const say = (kind, text) => setNotice({ kind, text });
  const reload = useCallback(() => {
    setLoadingList(true);
    api.dealerProducts(token, { q: filter, limit: 50 })
      .then(setList)
      .catch((error) => say('error', friendlyErrorMessage(error)))
      .finally(() => setLoadingList(false));
  }, [token, filter]);

  useEffect(() => { api.dealerProductCategories(token).then(setCategories).catch(() => setCategories([])); }, [token]);
  useEffect(() => {
    const timer = window.setTimeout(reload, 250);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const listedIds = new Set(list.items.map((product) => product.id));

  const search = async (event) => {
    event?.preventDefault();
    if (query.trim().length < 2) return;
    setSearching(true);
    try {
      const result = await api.catalogSearch(token, { q: query.trim(), limit: 8, include_facets: false });
      setFound(result.items);
    } catch (error) {
      say('error', friendlyErrorMessage(error));
    } finally {
      setSearching(false);
    }
  };

  const send = async (payload) => {
    setBusy(true);
    try {
      return await api.addDealerProduct(token, payload);
    } catch (error) {
      say('error', friendlyErrorMessage(error));
      return null;
    } finally {
      setBusy(false);
    }
  };

  const listFromCatalogue = async (product) => {
    const result = await send({ resolution: { action: 'link', product_id: product.id } });
    if (result) {
      say('success', describe({ ...result, product }));
      reload();
    }
  };

  const submitForm = async (event) => {
    event.preventDefault();
    setReview(null);
    const result = await send(form);
    if (!result) return;
    if (result.status === 'review') {
      setReview(result);
      say('', '');
      return;
    }
    if (result.status === 'error') {
      say('error', result.message);
      return;
    }
    say('success', describe(result));
    setForm(BLANK);
    reload();
  };

  const decide = async (item, resolution) => {
    const result = await send({ ...item.input, resolution });
    if (!result) return;
    if (result.status === 'error') {
      say('error', result.message);
      return;
    }
    say('success', describe(result));
    setReview((current) => (current && current === item ? null : current));
    setReport((current) => (current ? { ...current, problems: current.problems.filter((problem) => problem !== item), review: Math.max(0, current.review - 1) } : current));
    reload();
  };

  const remove = async (product) => {
    try {
      await api.removeDealerProduct(token, product.id);
      say('success', `Removed “${product.name}” from your list. It stays in the catalogue for other shops.`);
      reload();
    } catch (error) {
      say('error', friendlyErrorMessage(error));
    }
  };

  const downloadTemplate = async () => {
    try {
      const blob = await api.dealerProductTemplate(token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'product-catalogue-template.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      say('error', friendlyErrorMessage(error));
    }
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setReport(null);
    try {
      const result = await api.uploadDealerCatalogue(token, file);
      setReport(result);
      say(result.error || result.review ? '' : 'success', '');
      setFile(null);
      if (fileInput.current) fileInput.current.value = '';
      reload();
    } catch (error) {
      say('error', friendlyErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const items = form.category ? categories.find((category) => category.name === form.category)?.items || [] : [];
  const reviewItems = (report?.problems || []).filter((problem) => problem.status === 'review');
  const errorItems = (report?.problems || []).filter((problem) => problem.status === 'error');

  return (
    <Page>
      <Section
        title="My products"
        subtitle="Tell us what you sell. Requests for these exact products reach you even outside the categories you ticked. Every product lives once in a shared catalogue, so nothing is entered twice."
      />
      {notice.text ? <div className={`notice ${notice.kind === 'success' ? 'success' : ''}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.text}</div> : null}

      <Panel title="Add from the catalogue">
        <form className="toolbar" onSubmit={search}>
          <div className="search-box wide-search">
            <Search size={17} aria-hidden="true" />
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by product, brand or model" aria-label="Search the catalogue" />
          </div>
          <button type="submit" className="primary" disabled={searching || query.trim().length < 2}>{searching ? 'Searching…' : 'Search'}</button>
        </form>
        {found ? (
          found.length ? (
            <ul className="result-list">
              {found.map((product) => (
                <li key={product.id}>
                  <span><strong>{product.name}</strong> <span className="muted">{label(product)}</span></span>
                  {listedIds.has(product.id) ? <Status text="active" /> : null}
                  <button type="button" className="small primary" disabled={busy || listedIds.has(product.id)} onClick={() => listFromCatalogue(product)}>{listedIds.has(product.id) ? 'On your list' : 'I sell this'}</button>
                </li>
              ))}
            </ul>
          ) : <p className="muted">Nothing matched. Add it below and we will check it against the catalogue first.</p>
        ) : null}
      </Panel>

      <Panel title="Add a product that is not listed">
        <form onSubmit={submitForm} className="bid-sheet">
          <div className="form-grid">
            <div className="field wide">
              <label htmlFor="np-name">Product name</label>
              <input id="np-name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="np-brand">Brand</label>
              <input id="np-brand" value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="np-model">Model number</label>
              <input id="np-model" value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} />
              <p className="hint">The model on the box helps us spot a product that is already in the catalogue.</p>
            </div>
            <div className="field">
              <label htmlFor="np-mpn">Part number (optional)</label>
              <input id="np-mpn" value={form.mpn} onChange={(event) => setForm({ ...form, mpn: event.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="np-gtin">Barcode (optional)</label>
              <input id="np-gtin" inputMode="numeric" value={form.gtin} onChange={(event) => setForm({ ...form, gtin: event.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="np-category">Category</label>
              <select id="np-category" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value, item: '' })}>
                <option value="">Choose a category</option>
                {categories.map((category) => <option key={category.id} value={category.name}>{category.name}</option>)}
              </select>
              <p className="hint">Only needed if the product is not already in the catalogue.</p>
            </div>
            <div className="field">
              <label htmlFor="np-item">Item type</label>
              <select id="np-item" value={form.item} disabled={!items.length} onChange={(event) => setForm({ ...form, item: event.target.value })}>
                <option value="">{items.length ? 'Choose an item type' : 'Choose a category first'}</option>
                {items.map((entry) => <option key={entry.id} value={entry.name}>{entry.name}</option>)}
              </select>
            </div>
            <div className="field wide">
              <label htmlFor="np-description">Description (optional)</label>
              <textarea id="np-description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            </div>
          </div>
          <div className="row-actions"><button type="submit" className="primary" disabled={busy}>{busy ? 'Checking…' : 'Add product'}</button></div>
        </form>
        {review ? <ReviewCard item={review} busy={busy} onChoose={decide} /> : null}
      </Panel>

      <Panel title="Upload your catalogue" actions={<button type="button" className="small" onClick={downloadTemplate}><Download size={14} aria-hidden="true" /> Download template</button>}>
        <p className="muted-small">Upload a CSV or Excel (.xlsx) file, up to 3,000 products and 5 MB. Every row is checked against the catalogue first: products we already have are linked to your list, and only new products are added.</p>
        <div className="toolbar">
          <label className="file-pick">
            <span className="sr-only">Choose a catalogue file</span>
            <input ref={fileInput} type="file" accept=".csv,.xlsx,.txt" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          </label>
          <button type="button" className="primary" disabled={!file || busy} onClick={upload}><Upload size={15} aria-hidden="true" /> {busy ? 'Reading your file…' : 'Upload and check'}</button>
        </div>
        {report ? (
          <div className="upload-report" role="status">
            <p><strong>{plural(report.total, 'product')} read.</strong> {report.created} added as new, {report.linked} matched to products already in the catalogue, {report.already_listed} already on your list{report.review ? `, ${report.review} need your decision` : ''}{report.error ? `, ${plural(report.error, 'problem')}` : ''}.</p>
            {reviewItems.length ? reviewItems.map((item) => <ReviewCard key={item.row} item={item} busy={busy} onChoose={decide} />) : null}
            {errorItems.length ? (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Row</th><th>Product</th><th>What to fix</th></tr></thead>
                  <tbody>{errorItems.map((item) => <tr key={item.row}><td data-label="Row">{item.row}</td><td data-label="Product">{item.input?.name || '—'}</td><td data-label="What to fix">{item.message}</td></tr>)}</tbody>
                </table>
              </div>
            ) : null}
            {report.problems_total > report.problems_shown ? <p className="muted-small">Showing the first {report.problems_shown} of {report.problems_total} rows that need attention.</p> : null}
          </div>
        ) : null}
      </Panel>

      <Panel title={`Products you sell (${list.total})`}>
        <div className="toolbar">
          <div className="search-box wide-search">
            <Search size={17} aria-hidden="true" />
            <input type="search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter your products" aria-label="Filter your products" />
          </div>
        </div>
        {list.items.length ? (
          <ul className="result-list">
            {list.items.map((product) => (
              <li key={product.id}>
                <span>
                  <strong>{product.name}</strong> <span className="muted">{label(product)}</span>
                  <small className="block muted-small">{[product.category, product.item].filter(Boolean).join(', ')}{product.sku ? `, your SKU ${product.sku}` : ''}</small>
                </span>
                <button type="button" className="small danger" aria-label={`Remove ${product.name} from my list`} onClick={() => remove(product)}><Trash2 size={14} aria-hidden="true" /> Remove</button>
              </li>
            ))}
          </ul>
        ) : loadingList ? <p role="status" className="muted">Loading…</p> : (
          <Empty
            title={filter ? 'No products match' : 'You have not listed any products yet'}
            hint={filter ? 'Try a shorter search.' : 'Search the catalogue above, type a product in, or upload your catalogue. You can also tick whole categories under My shop.'}
            action={!filter ? <button type="button" onClick={() => setTab(6)}>Choose categories in My shop</button> : null}
          />
        )}
        {list.total > list.items.length ? <p className="muted-small">Showing the newest {list.items.length} of {list.total}. Use the filter to find the rest.</p> : null}
      </Panel>
    </Page>
  );
}
