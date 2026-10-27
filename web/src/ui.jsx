import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react';
import { Package, X } from 'lucide-react';
import { dateTime, timeLeftLabel, timeTone, titleCase, toTime } from './format.js';
import { productImageUrl } from './api.js';

/* Formatting lives in format.js so it can be tested without React. */
export { text, titleCase, money, toTime, dateTime, plural, timeLeftLabel, timeTone } from './format.js';

/* ------------------------------------------------------------------ */
/* Clock + countdown                                                   */
/* ------------------------------------------------------------------ */

const clockListeners = new Set();
let clockTimer = null;

function subscribeClock(listener) {
  clockListeners.add(listener);
  if (!clockTimer) clockTimer = window.setInterval(() => clockListeners.forEach((fn) => fn()), 1000);
  return () => {
    clockListeners.delete(listener);
    if (!clockListeners.size && clockTimer) {
      window.clearInterval(clockTimer);
      clockTimer = null;
    }
  };
}

const readClock = () => Math.floor(Date.now() / 1000) * 1000;

/** One shared one-second ticker for every countdown on screen. */
export function useNow() {
  return useSyncExternalStore(subscribeClock, readClock, readClock);
}

export function Countdown({ until, className = '' }) {
  const now = useNow();
  const end = toTime(until);
  if (Number.isNaN(end)) return null;
  const remaining = end - now;
  return (
    <time className={`countdown ${timeTone(remaining)} ${className}`} dateTime={new Date(end).toISOString()} title={`Closes ${dateTime(until)}`}>
      <span className="countdown-dot" aria-hidden="true" />
      {timeLeftLabel(remaining)}
    </time>
  );
}

/* ------------------------------------------------------------------ */
/* Errors surfaced inside dialogs                                      */
/* ------------------------------------------------------------------ */

export const DialogErrorContext = createContext({ error: '', clearError: () => {} });

/* ------------------------------------------------------------------ */
/* Modal                                                               */
/* ------------------------------------------------------------------ */

// Open dialogs, oldest first. Only the top-most one reacts to the keyboard.
const dialogStack = [];

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Accessible dialog: labelled, traps focus, closes on Escape and restores focus.
 * `persistent` dialogs (forms) ignore backdrop clicks so typed data is not lost by accident.
 */
export function Modal({ title, children, onClose, wide, persistent = false, tone = '' }) {
  const titleId = useId();
  const panel = useRef(null);
  const { error, clearError } = useContext(DialogErrorContext);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    clearError();
    const token = {};
    dialogStack.push(token);
    const previous = document.activeElement;
    const node = panel.current;
    const firstField = node?.querySelector('.modal-body input:not([type="hidden"]):not([disabled]), .modal-body select, .modal-body textarea');
    (firstField || node?.querySelector(FOCUSABLE) || node)?.focus({ preventScroll: true });
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (event) => {
      if (dialogStack[dialogStack.length - 1] !== token) return;
      if (event.key === 'Escape') {
        event.stopPropagation();
        closeRef.current?.();
        return;
      }
      if (event.key !== 'Tab' || !node) return;
      const items = [...node.querySelectorAll(FOCUSABLE)].filter((item) => item.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
      dialogStack.splice(dialogStack.indexOf(token), 1);
      document.body.style.overflow = dialogStack.length ? 'hidden' : overflow;
      if (previous instanceof HTMLElement && document.contains(previous)) previous.focus({ preventScroll: true });
    };
    // Mount-only: focus handling must not re-run when the parent re-renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="modal-layer" onMouseDown={(event) => { if (!persistent && event.target === event.currentTarget) onClose(); }}>
      <section ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={titleId} className={`modal ${wide ? 'wide' : ''} ${tone}`}>
        <header>
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-button" aria-label="Close" title="Close" onClick={onClose}><X size={18} aria-hidden="true" /></button>
        </header>
        <div className="modal-body">
          {error ? <div className="notice" role="alert">{error}</div> : null}
          {children}
        </div>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Confirm dialog                                                      */
/* ------------------------------------------------------------------ */

const ConfirmContext = createContext(() => Promise.resolve(false));

/** `const confirm = useConfirm(); if (await confirm({ title, body, confirmLabel, tone })) ...` */
export function useConfirm() {
  return useContext(ConfirmContext);
}

export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const [typed, setTyped] = useState('');
  const inputId = useId();
  const confirm = useCallback((options) => new Promise((resolve) => {
    setTyped(options.input?.initial || '');
    setRequest({ ...options, resolve });
  }), []);
  // With `input`, a confirmed dialog resolves to the typed text and a cancelled one to false.
  const settle = (answer) => {
    request?.resolve(answer && request.input ? typed.trim() : answer);
    setRequest(null);
  };
  const needsText = Boolean(request?.input?.required) && typed.trim().length < (request.input.minLength || 1);
  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {request ? (
        <Modal title={request.title} onClose={() => settle(false)} persistent tone="confirm">
          {request.body ? <div className="confirm-body">{request.body}</div> : null}
          {request.input ? (
            <div className="field">
              <label htmlFor={inputId}>{request.input.label}</label>
              <textarea id={inputId} value={typed} placeholder={request.input.placeholder} onChange={(event) => setTyped(event.target.value)} />
            </div>
          ) : null}
          <div className="dialog-actions">
            <button type="button" onClick={() => settle(false)}>{request.cancelLabel || 'Keep it'}</button>
            <button type="button" className={request.tone === 'danger' ? 'danger-solid' : 'primary'} disabled={needsText} onClick={() => settle(true)}>{request.confirmLabel || 'Confirm'}</button>
          </div>
        </Modal>
      ) : null}
    </ConfirmContext.Provider>
  );
}

/* ------------------------------------------------------------------ */
/* Layout primitives                                                   */
/* ------------------------------------------------------------------ */

export function Page({ children }) {
  return <div className="page">{children}</div>;
}

/** Page heading. `icon` is accepted for older call sites but no longer drawn. */
export function Section({ title, subtitle, actions }) {
  return (
    <header className="section-header">
      <div className="section-heading">
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {actions ? <div className="section-actions">{actions}</div> : null}
    </header>
  );
}

export function Panel({ title, children, actions, className = '' }) {
  return (
    <section className={`panel ${className}`}>
      {title || actions ? (
        <div className="panel-head">
          {title ? <h2>{title}</h2> : <span />}
          {actions ? <div className="panel-actions">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Metric({ label, value, hint, tone = '' }) {
  return (
    <div className={`metric ${tone}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

const STATUS_TONE = {
  active: 'live', updated: 'live', open: 'warn', notified: 'live', viewed: 'live', submitted: 'live', awarded: 'good',
  won: 'good', completed: 'good', paid: 'good', resolved: 'good', verified: 'good', approved: 'good', subscribed: 'good', delivered: 'good',
  lost: 'quiet', expired: 'quiet', withdrawn: 'quiet', closed: 'quiet', cancelled: 'quiet', inactive: 'quiet', archived: 'quiet', deleted: 'quiet', not_due: 'quiet',
  pending: 'warn', held: 'warn', flagged: 'warn', in_review: 'warn', investigating: 'warn', escalated: 'warn', unpaid: 'warn', requested: 'warn',
  live: 'live', scheduled: 'warn', ended: 'quiet', paused: 'warn',
  banned: 'bad', suspended: 'bad', failed: 'bad', rejected: 'bad', refunded: 'bad',
};

export function Status({ text: value = 'active' }) {
  const key = String(value || 'active').toLowerCase();
  return <span className={`status status-${STATUS_TONE[key] || 'quiet'} ${key}`}>{titleCase(key)}</span>;
}

export function Empty({ title, hint, action }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {hint ? <p>{hint}</p> : null}
      {action || null}
    </div>
  );
}

export function KV({ label, value }) {
  return (
    <div className="kv">
      <span>{label}</span>
      <strong>{String(value ?? '') || '—'}</strong>
    </div>
  );
}

export function ProductImage({ product, className = 'product-art', iconSize = 42, loading }) {
  const placeholder = '/catalog-placeholder.svg';
  const source = product.image_url ? productImageUrl(product.image_url) : placeholder;
  const [imageState, setImageState] = useState({ source: '', status: 'loading' });
  const status = imageState.source === source ? imageState.status : 'loading';
  const displaySource = source === placeholder || status === 'fallback' || status === 'missing' ? placeholder : source;
  const loaded = status === 'loaded' || status === 'placeholder';
  return (
    <div className={className}>
      {!loaded ? <Package size={iconSize} aria-hidden="true" /> : null}
      <img
        key={displaySource}
        src={displaySource}
        alt=""
        loading={loading || (className === 'product-detail-art' ? 'eager' : 'lazy')}
        className="catalog-product-photo"
        style={{ opacity: loaded ? 1 : 0 }}
        onLoad={() => setImageState({ source, status: displaySource === placeholder ? 'placeholder' : 'loaded' })}
        onError={() => setImageState({ source, status: displaySource === placeholder ? 'missing' : 'fallback' })}
      />
    </div>
  );
}

/** Placeholder slips shown while a list loads, so an empty state never flashes by mistake. */
export function SlipSkeletons({ count = 2 }) {
  return (
    <div className="slip-grid" role="status" aria-label="Loading">
      {Array.from({ length: count }, (_, index) => (
        <div className="slip skeleton" key={index} aria-hidden="true">
          <div className="skeleton-line wide" />
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>
      ))}
      <span className="sr-only">Loading</span>
    </div>
  );
}

export function CopyButton({ value, label }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard access can be blocked; the value is still on screen to copy by hand.
    }
  };
  return <button type="button" className="copy-button" aria-label={`Copy ${label}`} onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>;
}
