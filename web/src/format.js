/* Pure formatting and bidding helpers. No React here, so they can be unit tested with plain Node. */

export function text(value) {
  return String(value ?? '').trim();
}

export function titleCase(value) {
  const spaced = text(value).replaceAll('_', ' ');
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : '';
}

/** Rupees with Indian digit grouping. Whole amounts drop the paise. Missing values show a dash. */
export function money(value) {
  if (value === null || value === undefined || value === '') return '—';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '—';
  const whole = Math.abs(amount % 1) < 0.005;
  return `₹${amount.toLocaleString('en-IN', {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  })}`;
}

/** Backend timestamps may be naive ("2026-10-14 10:00:00") or carry an offset. */
export function toTime(value) {
  if (!value) return NaN;
  return new Date(String(value).replace(' ', 'T')).getTime();
}

export function dateTime(value) {
  if (!value) return '';
  const stamp = toTime(value);
  if (Number.isNaN(stamp)) return String(value);
  const date = new Date(stamp);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function plural(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

export function timeLeftLabel(ms) {
  if (ms <= 0) return 'Ended';
  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (days) return `${days}d ${hours}h left`;
  if (hours) return `${hours}h ${String(minutes).padStart(2, '0')}m left`;
  if (minutes >= 10) return `${minutes}m left`;
  if (minutes) return `${minutes}m ${String(seconds).padStart(2, '0')}s left`;
  return `${seconds}s left`;
}

export function timeTone(ms) {
  if (ms <= 0) return 'ended';
  if (ms < 10 * 60 * 1000) return 'urgent';
  if (ms < 60 * 60 * 1000) return 'soon';
  return 'calm';
}

/* ------------------------------------------------------------------ */
/* Bidding helpers                                                     */
/* ------------------------------------------------------------------ */

const LIVE_STATUSES = ['active', 'updated'];

export const isLive = (bid) => LIVE_STATUSES.includes(String(bid?.status || '').toLowerCase());

/** Older offers stored delivery as a bare number of days. */
export function formatDelivery(value) {
  const raw = text(value);
  if (!raw) return 'Not stated';
  if (/^\d+(\.\d+)?$/.test(raw)) return `${raw} ${Number(raw) === 1 ? 'day' : 'days'}`;
  return raw;
}

/** Where a dealer's live offer stands against the other live offers on the same request. */
export function standingFor(bid, allBids) {
  const others = allBids.filter((other) => (
    other.bid_request_id === bid.bid_request_id && other.id !== bid.id && !other.is_mine && isLive(other)
  ));
  if (!others.length) return { kind: 'solo', lowest: null, gap: 0, count: 0 };
  const lowest = Math.min(...others.map((other) => Number(other.amount)));
  const mine = Number(bid.amount);
  return mine <= lowest
    ? { kind: 'lead', lowest, gap: 0, count: others.length }
    : { kind: 'trail', lowest, gap: mine - lowest, count: others.length };
}

/* ------------------------------------------------------------------ */
/* Errors                                                              */
/* ------------------------------------------------------------------ */

function fieldLabel(field) {
  return text(field).replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

/** Turns an API error (status, JSON detail, validation list) into one sentence a person can act on. */
export function friendlyErrorMessage(err) {
  const message = String(err?.message || err || '');
  const jsonStart = message.indexOf('{');
  if (jsonStart >= 0) {
    try {
      const parsed = JSON.parse(message.slice(jsonStart));
      const detail = parsed.detail;
      if (Array.isArray(detail) && detail[0]) {
        const field = detail[0].loc?.[detail[0].loc.length - 1] || 'field';
        if (detail[0].type === 'greater_than') return `${fieldLabel(field)} must be greater than 0.`;
        if (detail[0].type?.includes('missing')) return `${fieldLabel(field)} is required.`;
        if (detail[0].type?.includes('float') || detail[0].type?.includes('int')) return `${fieldLabel(field)} must be a valid number.`;
        // Rules written in the backend arrive as "Value error, <our sentence>"; show only our sentence.
        return String(detail[0].msg || 'Please check the highlighted form fields.').replace(/^Value error,\s*/, '');
      }
      if (typeof detail === 'string') return detail;
    } catch {
      // Fall through to text matching.
    }
  }
  if (message.includes('Duplicate entry') && message.includes('uq_buyer_location')) return 'This location is already saved. Update the existing saved location instead.';
  return message.replace(/^API error \d+:\s*/, '') || 'Something went wrong. Please try again.';
}
