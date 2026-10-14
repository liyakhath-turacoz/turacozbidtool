import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Bell,
  Bolt,
  Check,
  ChevronRight,
  ClipboardList,
  Download,
  Eye,
  FileText,
  Filter,
  Flag,
  Gavel,
  Home,
  Inbox,
  IndianRupee,
  Layers,
  LogOut,
  MapPin,
  Menu,
  Package,
  Pencil,
  Plus,
  ReceiptText,
  RefreshCw,
  Search,
  Send,
  Settings,
  Shield,
  ShoppingCart,
  Store,
  Trash2,
  User,
  Users,
  X,
} from 'lucide-react';
import { api, apiBaseUrl } from './api.js';
import MapCoordinatePicker from './MapCoordinatePicker.jsx';
import BidConversation, { mergeMessages } from './BidConversation.jsx';
import CatalogFilters, {emptyCatalogFilters, catalogParams} from './CatalogFilters.jsx';
import ProductSourcesPage from './ProductSourcesPage.jsx';

const sessionKey = 'turacoz_bid_tool_web_session';

function friendlyErrorMessage(err) {
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
        return detail[0].msg || 'Please check the highlighted form fields.';
      }
      if (typeof detail === 'string') {
        if (detail.toLowerCase().includes('no matching dealers')) return 'No dealers found for your selected location and product. Try another saved location, radius, category, or dealer coverage area.';
        if (detail.toLowerCase().includes('saved location')) return detail;
        return detail;
      }
    } catch {
      // Fall through to text matching.
    }
  }
  if (message.includes('No matching dealers') || message.includes('No subscribed dealers')) return 'No subscribed dealers match this location and product. Try another saved location or category, or check dealer subscriptions and service coverage.';
  if (message.includes('Duplicate entry') && message.includes('uq_buyer_location')) return 'This location is already saved. Update the existing saved location instead.';
  return message.replace(/^API error \d+:\s*/, '') || 'Something went wrong. Please try again.';
}

function fieldLabel(field) {
  return text(field).replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

const adminNav = [
  ['Dashboard', Home],
  ['Dealer Management', Store],
  ['Buyer Management', Users],
  ['Products / Catalog', Package],
  ['Bid History', Gavel],
  ['Reports', FileText],
  ['Platform Rules & Categories', Settings],
  ['Product Fetch & Reports', Download],
];

const buyerNav = [
  ['Home', Home],
  ['Bid Page', Bolt],
  ['Orders / History', ClipboardList],
  ['Cart', ShoppingCart],
  ['Notifications', Bell],
  ['Profile', User],
  ['Reports / Support', FileText],
];

const dealerNav = [
  ['Dealer Dashboard', Home],
  ['Incoming Bid Requests', Inbox],
  ['Active Bids', Pencil],
  ['Bid History / Orders', ClipboardList],
  ['Business Profile', Store],
  ['Notifications', Bell],
  ['Reports / Support', FileText],
];

const statusOptions = ['active', 'held', 'suspended', 'banned', 'flagged'];
const reportStatuses = ['open', 'in_review', 'resolved', 'cancelled'];

function money(value) {
  const amount = Number(value || 0);
  return `Rs. ${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function dateTime(value) {
  if (!value) return '';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function list(value) {
  return Array.isArray(value) ? value : [];
}

function HubIcon({ size = 46 }) {
  const nodes = [
    [12, 3.5],
    [20, 7.7],
    [20, 16.3],
    [12, 20.5],
    [4, 16.3],
    [4, 7.7],
  ];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
        {nodes.map(([x, y]) => <path key={`${x}-${y}`} d={`M12 12 L${x} ${y}`} />)}
        <circle cx="12" cy="12" r="2.1" />
        {nodes.map(([x, y]) => <circle key={`c-${x}-${y}`} cx={x} cy={y} r="2.05" />)}
      </g>
    </svg>
  );
}

function metricEntries(dashboard) {
  const source = dashboard?.metrics || dashboard || {};
  const labels = {
    total_dealers: 'Total Dealers',
    total_buyers: 'Total Buyers',
    active_bids: 'Active Bids',
    completed_bids: 'Completed Bids',
    pending_reports: 'Pending Reports',
    revenue: 'Revenue',
    total_revenue: 'Total Revenue',
    held_dealers: 'Held Dealers',
    banned_dealers: 'Banned Dealers',
    subscription_status: 'Subscription',
    open_requests: 'Open Requests',
    won_bids: 'Won Bids',
    lost_bids: 'Lost Bids',
    cart_items: 'Cart Items',
  };
  const ignored = new Set(['recent_activity', 'recent_reports', 'charts', 'alerts']);
  return Object.entries(source)
    .filter(([key, value]) => !ignored.has(key) && ['string', 'number', 'boolean'].includes(typeof value))
    .slice(0, 10)
    .map(([key, value]) => ({
      key,
      label: labels[key] || key.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      value: key.includes('revenue') || key.includes('amount') ? money(value) : String(value),
    }));
}

function normalizeUser(user) {
  return {
    id: String(user.id || ''),
    name: String(user.name || user.full_name || ''),
    email: String(user.email || ''),
    role: String(user.role || 'buyer').toLowerCase(),
    status: String(user.status || 'active'),
    access_token: String(user.access_token || user.accessToken || ''),
  };
}

function productSpecs(product) {
  const specs = product?.specifications;
  if (!specs || typeof specs !== 'object') return '';
  return Object.entries(specs)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${value}`)
    .join(' | ');
}

function text(value) {
  return String(value ?? '').trim();
}

function lower(value) {
  return text(value).toLowerCase();
}

function firstText(row, keys, fallback = '') {
  for (const key of keys) {
    const value = text(row?.[key]);
    if (value) return value;
  }
  return fallback;
}

function distinct(rows, keys) {
  return [...new Set(rows.map((row) => firstText(row, keys)).filter(Boolean))].sort();
}

function titleCase(value) {
  return text(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function parseSpecText(value) {
  if (!value || typeof value !== 'string') return {};
  return Object.fromEntries(
    text(value)
      .split('\n')
      .map((line) => { const colon = line.indexOf(':'); return colon < 0 ? [] : [line.slice(0,colon).trim(),line.slice(colon+1).trim()]; })
      .filter(([key, val]) => key && val),
  );
}

function toSpecText(specifications) {
  if (!specifications || typeof specifications !== 'object') return '';
  return Object.entries(specifications || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n');
}

function App() {
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [registering, setRegistering] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [dismissSubscriptionBanner, setDismissSubscriptionBanner] = useState(false);
  const [toast, setToast] = useState('');
  const [data, setData] = useState({
    dashboard: {},
    products: [],
    bids: [],
    notifications: [],
    dealers: [],
    buyers: [],
    payments: [],
    logs: [],
    reports: [],
    settings: {},
    cart: {},
    dealerRequests: [],
    buyerRequests: [],
    categories: [],
    dealerSubscribed: false,
    profile: null,
    buyerLocations: [],
    liveMessages: {},
    liveBidMessages: {},
  });
  const [details, setDetails] = useState(null);
  const [bidProduct, setBidProduct] = useState(null);
  const [dealerOffer, setDealerOffer] = useState(null);
  const [reportBid, setReportBid] = useState(null);
  const wsRef = useRef(null);
  const wsReconnectRef = useRef(null);
  const expiryTimersRef = useRef([]);
  const actionInFlightRef = useRef(null);
  const bucketVersionsRef = useRef({});
  const snapshotVersionsRef = useRef({});
  const activeTabRef = useRef(tab);
  activeTabRef.current = tab;
  const sessionTokenRef = useRef(user?.access_token);
  sessionTokenRef.current = user?.access_token;
  const expiryRefreshSeenRef = useRef(new Set());

  const nav = user?.role === 'admin' ? adminNav : user?.role === 'dealer' ? dealerNav : buyerNav;
  const unread = list(data.notifications).filter((item) => !item.is_read && !item.isRead).length;

  const loadBuckets = useCallback(async (activeUser = user, buckets = [], options = {}) => {
    if (!activeUser?.access_token || !buckets.length) return;
    if (!options.silent) setLoading(true);
    if (!options.silent) setError('');
    try {
      const token = activeUser.access_token;
      const next = {};
      const failures = [];
      const versions = {};
      await Promise.all([...new Set(buckets)].map(async (bucket) => {
        versions[bucket] = (bucketVersionsRef.current[bucket] || 0) + 1;
        bucketVersionsRef.current[bucket] = versions[bucket];
        try {
          if (bucket === 'dashboard') next.dashboard = await api.dashboard(activeUser);
          if (bucket === 'products') next.products = await api.products(token, '');
          if (bucket === 'bids') next.bids = await api.bids(token);
          if (bucket === 'notifications') next.notifications = await api.notifications(token);
          if (bucket === 'dealers') next.dealers = await api.dealers(token, '');
          if (bucket === 'buyers') next.buyers = await api.buyers(token, '');
          if (bucket === 'payments') next.payments = await api.payments(token);
          if (bucket === 'logs') next.logs = await api.logs(token);
          if (bucket === 'reports') next.reports = await api.reports(token);
          if (bucket === 'categories') next.categories = await api.categories(token);
          if (bucket === 'settings') next.settings = await api.settings(token);
          if (bucket === 'cart') next.cart = await api.cart(token);
          if (bucket === 'buyerRequests') next.buyerRequests = await api.buyerRequests(token);
          if (bucket === 'dealerRequests') next.dealerRequests = await api.dealerRequests(token);
          if (bucket === 'buyerLocations') next.buyerLocations = await api.buyerLocations(token);
          if (bucket === 'profile') {
            const profile = await api.profile(token);
            next.profile = profile;
            if (activeUser.role === 'dealer') {
              next.dealerSubscribed = profile?.subscribed === true || profile?.subscribed === 1;
            }
          }
        } catch (err) {
          failures.push(err);
        }
      }));
      if (sessionTokenRef.current !== token) return false;
      const current = Object.fromEntries(Object.entries(next).filter(([key]) => {
        const bucket = key === 'dealerSubscribed' ? 'profile' : key;
        return versions[bucket] === bucketVersionsRef.current[bucket];
      }));
      setData((old) => ({ ...old, ...current }));
      if (failures.length) throw failures.find((err) => String(err.message).includes('401')) || failures[0];
      return true;
    } catch (err) {
      if (sessionTokenRef.current !== activeUser.access_token) return false;
      if (String(err.message).includes('401')) {
        sessionStorage.removeItem(sessionKey);
        setUser(null);
        setError('Session expired. Please log in again.');
      } else {
        setError(`Could not load live data: ${friendlyErrorMessage(err)}`);
      }
      return false;
    } finally {
      if (!options.silent && sessionTokenRef.current === activeUser.access_token) setLoading(false);
    }
  }, [user]);

  const bucketsForPage = useCallback((activeUser = user, activeTab = tab) => {
    if (!activeUser) return [];
    if (activeUser.role === 'admin') {
      return [
        ['dashboard', 'dealers', 'buyers'],
        ['dealers'],
        ['buyers'],
        ['products', 'categories'],
        ['bids', 'payments', 'logs'],
        ['reports'],
        ['categories', 'settings'],
      ][activeTab] || [];
    }
    if (activeUser.role === 'dealer') {
      return [
        ['dashboard', 'bids', 'dealerRequests', 'profile', 'notifications', 'settings'],
        ['dealerRequests', 'bids'],
        ['bids', 'dealerRequests'],
        ['bids'],
        ['profile', 'categories', 'settings'],
        ['notifications'],
        ['reports'],
      ][activeTab] || [];
    }
    return [
      ['products', 'buyerLocations', 'notifications', 'settings'],
      ['products', 'bids', 'buyerRequests', 'buyerLocations', 'settings'],
      ['products', 'bids', 'buyerRequests'],
      ['cart', 'products', 'buyerLocations', 'settings'],
      ['notifications'],
      ['profile', 'buyerLocations', 'reports'],
      ['reports'],
    ][activeTab] || [];
  }, [tab, user]);

  const loadPageData = useCallback((activeUser = user, activeTab = tab, options = {}) => (
    loadBuckets(activeUser, bucketsForPage(activeUser, activeTab), options)
  ), [bucketsForPage, loadBuckets, tab, user]);

  useEffect(() => {
    localStorage.removeItem(sessionKey);
    const raw = sessionStorage.getItem(sessionKey);
    if (!raw) return;
    try {
      const restored = normalizeUser(JSON.parse(raw));
      setUser(restored);
    } catch {
      sessionStorage.removeItem(sessionKey);
    }
  }, []);

  useEffect(() => {
    if (!user?.access_token) return;
    loadPageData(user, tab);
  }, [user?.id, tab]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(''), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!user?.id || !user?.access_token) return undefined;
    const wsBase = apiBaseUrl.replace(/^http/, 'ws');
    let closedByEffect = false;
    let reconnectAttempts = 0;
    let heartbeat;
    let refreshTimer;
    const pendingBuckets = new Set();
    const queueRefresh = (buckets) => {
      buckets.forEach((bucket) => pendingBuckets.add(bucket));
      window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(() => {
        const queued = [...pendingBuckets];
        pendingBuckets.clear();
        loadBuckets(user, queued, { silent: true });
      }, 100);
    };
    const bidEvents = [
      'new_request',
      'new_bid',
      'bid_created',
      'bid_updated',
      'bid_withdrawn',
      'bid_accepted',
      'bid_won',
      'bid_lost',
      'bid_cancelled',
      'bid_expired',
      'request_expired',
      'commission_paid',
    ];
    const reportEvents = ['new_message', 'report_created', 'report_updated', 'report_cancelled', 'report_reply', 'report_private_message'];
    const bidBuckets = () => (user.role === 'buyer'
      ? ['bids', 'buyerRequests', 'notifications']
      : user.role === 'dealer'
        ? ['bids', 'dealerRequests', 'notifications']
        : ['dashboard', 'bids', 'payments', 'logs', 'notifications']);
    const connect = () => {
      const socket = new WebSocket(`${wsBase}/ws/${user.id}?token=${encodeURIComponent(user.access_token)}`);
      wsRef.current = socket;
      socket.onopen = () => {
        if (reconnectAttempts) {
          queueRefresh([...bidBuckets(), 'profile', 'reports']);
          window.dispatchEvent(new Event('bid-chat-reconnected'));
        }
        reconnectAttempts = 0;
        window.clearInterval(heartbeat);
        heartbeat = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send('ping');
        }, 30000);
      };
      socket.onmessage = (event) => {
        let message = {};
        try {
          message = JSON.parse(event.data || '{}');
        } catch {
          message = {};
        }
        const type = message.type || '';
        if (type === 'pong') return;
        if (type === 'bid_message' && message.message) {
          setData((old) => ({ ...old, liveBidMessages: { ...old.liveBidMessages, [message.bid_id]: mergeMessages(old.liveBidMessages[message.bid_id] || [], [message.message]) } }));
          return;
        }
        if (type === 'bid_snapshot') {
          const requestId = message.request_id;
          const previous = snapshotVersionsRef.current[requestId] || '0';
          if (BigInt(message.version) <= BigInt(previous)) return;
          snapshotVersionsRef.current[requestId] = message.version;
          ['bids', 'buyerRequests', 'dealerRequests'].forEach((bucket) => { bucketVersionsRef.current[bucket] = (bucketVersionsRef.current[bucket] || 0) + 1; });
          setData((old) => ({ ...old,
            bids: [...message.bids, ...old.bids.filter((bid) => bid.bid_request_id !== requestId)],
            buyerRequests: user.role === 'buyer' ? [message.request, ...old.buyerRequests.filter((request) => request.id !== requestId)] : old.buyerRequests,
            dealerRequests: user.role === 'dealer' ? [...(message.dealer_request ? [message.dealer_request] : []), ...old.dealerRequests.filter((request) => request.id !== requestId)] : old.dealerRequests,
          }));
          queueRefresh(['notifications', ...(activeTabRef.current === 0 ? ['dashboard'] : [])]);
          return;
        }
        if (type === 'new_message' && message.message) {
          setData((old) => ({ ...old, liveMessages: { ...old.liveMessages, [message.report_id]: mergeMessages(old.liveMessages[message.report_id] || [], [message.message]) } }));
        }
        if (bidEvents.includes(type)) {
          const requestId = message.request_id || message.bid_request_id;
          queueRefresh(requestId && snapshotVersionsRef.current[requestId] && !message.refresh_required ? ['notifications'] : bidBuckets());
        } else if (reportEvents.includes(type)) {
          queueRefresh(['reports', 'notifications']);
        } else if (type === 'subscription_activated') {
          queueRefresh(['profile', 'dashboard', 'dealerRequests', 'notifications']);
        } else if (type === 'profile_updated') {
          queueRefresh(['profile', 'dealerRequests']);
        } else {
          queueRefresh(['notifications']);
        }
      };
      socket.onclose = (event) => {
        window.clearInterval(heartbeat);
        if (wsRef.current === socket) wsRef.current = null;
        if (closedByEffect) return;
        if (event.code === 4401 || event.code === 4403) {
          sessionStorage.removeItem(sessionKey);
          setUser(null);
          setError('Session expired or account blocked. Please log in again.');
          return;
        }
        if (!closedByEffect) {
          window.clearTimeout(wsReconnectRef.current);
          const delay = Math.min(30000, 1000 * (2 ** reconnectAttempts++));
          wsReconnectRef.current = window.setTimeout(connect, delay);
        }
      };
      socket.onerror = () => socket.close();
    };
    connect();
    return () => {
      closedByEffect = true;
      window.clearInterval(heartbeat);
      window.clearTimeout(refreshTimer);
      window.clearTimeout(wsReconnectRef.current);
      wsReconnectRef.current = null;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [user, loadBuckets]);

  useEffect(() => {
    expiryTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    expiryTimersRef.current = [];
    if (!user?.access_token) return undefined;

    const buckets = user.role === 'buyer'
      ? ['bids', 'buyerRequests', 'notifications']
      : user.role === 'dealer'
        ? ['bids', 'dealerRequests', 'notifications']
        : ['dashboard', 'bids', 'payments', 'logs', 'notifications'];
    const activeRows = [
      ...list(data.buyerRequests).filter((request) => request.status === 'active'),
      ...list(data.dealerRequests),
      ...list(data.bids).filter((bid) => ['active', 'updated'].includes(String(bid.status || '').toLowerCase())),
    ];

    const scheduleExpiryRefresh = (row) => {
      const rawExpiry = row.expires_at || row.ends_at || row.expiresAt || row.endsAt;
      if (!rawExpiry) return;
      const expiryTime = new Date(String(rawExpiry).replace(' ', 'T')).getTime();
      if (Number.isNaN(expiryTime)) return;
      const key = row.bid_request_id || row.id || `${rawExpiry}-${row.product || row.product_name || ''}`;
      const delay = expiryTime - Date.now() + 750;
      if (delay <= 0) {
        if (!expiryRefreshSeenRef.current.has(key)) {
          expiryRefreshSeenRef.current.add(key);
          const timer = window.setTimeout(() => loadBuckets(user, buckets, { silent: true }), 250);
          expiryTimersRef.current.push(timer);
        }
        return;
      }
      if (delay < 2147483647) {
        const timer = window.setTimeout(() => {
          expiryRefreshSeenRef.current.add(key);
          loadBuckets(user, buckets, { silent: true });
        }, delay);
        expiryTimersRef.current.push(timer);
      }
    };

    [...new Map(activeRows.map((row) => [row.bid_request_id || row.id, row])).values()].forEach(scheduleExpiryRefresh);
    return () => {
      expiryTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      expiryTimersRef.current = [];
    };
  }, [user, data.buyerRequests, data.dealerRequests, data.bids, loadBuckets]);

  async function handleLogin(username, password) {
    setLoading(true);
    setError('');
    try {
      const loggedIn = normalizeUser(await api.login(username.trim(), password));
      sessionStorage.setItem(sessionKey, JSON.stringify(loggedIn));
      setUser(loggedIn);
      setTab(0);
      setDismissSubscriptionBanner(false);
    } catch {
      setError('Login failed or backend is unavailable. Start FastAPI and MariaDB, then retry.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(payload) {
    setLoading(true);
    setError('');
    try {
      await api.register(payload);
      setRegistering(false);
      setError('Registration successful. Please login.');
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    sessionTokenRef.current = null;
    actionInFlightRef.current = null;
    wsRef.current?.close();
    sessionStorage.removeItem(sessionKey);
    setUser(null);
    setTab(0);
    setDismissSubscriptionBanner(false);
    setError('');
    setLoading(false);
    setData((old) => Object.fromEntries(Object.entries(old).map(([key, value]) => [key, Array.isArray(value) ? [] : typeof value === 'boolean' ? false : value === null ? null : {}])));
    setDetails(null);
    setBidProduct(null);
    setDealerOffer(null);
    setReportBid(null);
    expiryRefreshSeenRef.current.clear();
    snapshotVersionsRef.current = {};
  }

  async function run(action, successMessage) {
    if (!user || actionInFlightRef.current) return false;
    actionInFlightRef.current = user.access_token;
    setLoading(true);
    setError('');
    try {
      await action(user.access_token);
      if (sessionTokenRef.current !== user.access_token) return false;
      const refreshed = await loadPageData(user, tab);
      if (successMessage) {
        setToast(successMessage);
        if (refreshed !== false) setError('');
      }
      return true;
    } catch (err) {
      setError(friendlyErrorMessage(err));
      return false;
    } finally {
      if (actionInFlightRef.current === user.access_token) {
        actionInFlightRef.current = null;
        setLoading(false);
      }
    }
  }

  async function handleExport(kind) {
    if (!user?.access_token) return;
    setLoading(true);
    setError('');
    try {
      const blob = await api.exportCsv(user.access_token, kind);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `turacoz-${kind}-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setToast('CSV downloaded.');
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const page = user
    ? renderPage({
        user,
        tab,
        setTab,
        data,
        loading,
        setBidProduct,
        setDealerOffer,
        setReportBid,
        setDetails,
        refresh: () => loadPageData(user, tab),
        run,
        onExport: handleExport,
        onDeleteAccount: () => run((token) => api.deleteOwnAccount(token)).then((ok) => ok && logout()),
      })
    : registering
      ? <RegisterPage loading={loading} error={error} onRegister={handleRegister} onCancel={() => setRegistering(false)} />
      : <LoginPage loading={loading} error={error} onLogin={handleLogin} onRegister={() => setRegistering(true)} />;

  if (!user) return page;

  const isBuyer = user.role === 'buyer';

  return (
    <div className={`app-shell ${isBuyer ? 'buyer-shell' : ''}`}>
      <aside className={`side-nav ${isBuyer ? 'buyer-drawer' : ''} ${drawerOpen ? 'open' : ''}`}>
        <div className="brand-block">
          <div className="brand-icon"><Bolt size={22} /></div>
          <div>
            <strong>Turacoz</strong>
            <span>Bidding Tool</span>
          </div>
          <button className="icon-button mobile-only" onClick={() => setDrawerOpen(false)}><X size={18} /></button>
        </div>
        <nav>
          {nav.map(([label, Icon], index) => (
            <button
              key={label}
              className={`nav-item ${tab === index ? 'active' : ''}`}
              onClick={() => {
                setTab(index);
                setDrawerOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === 'Notifications' && unread > 0 ? <b>{unread}</b> : null}
            </button>
          ))}
        </nav>
      </aside>
      <div className="main-area">
        <header className="top-bar">
          {isBuyer ? (
            <button className="icon-button" onClick={() => setDrawerOpen(true)} title="Menu"><Menu size={20} /></button>
          ) : (
            <button className="icon-button mobile-only" onClick={() => setDrawerOpen(true)} title="Menu"><Menu size={20} /></button>
          )}
          <div>
            <h1>{isBuyer ? 'Turacoz Bid Tool Marketplace' : nav[tab]?.[0]}</h1>
            <p>{user.name} | live API</p>
          </div>
          <div className="top-actions">
            {isBuyer ? (
              <>
                <button className="icon-button" onClick={() => setTab(3)} title="Cart"><ShoppingCart size={19} /></button>
                <button className="icon-button badge-wrap" onClick={() => setTab(4)} title="Notifications">
                  <Bell size={19} />
                  {unread > 0 ? <span className="badge">{unread}</span> : null}
                </button>
                <button className="icon-button" onClick={() => setTab(5)} title="Profile"><User size={19} /></button>
              </>
            ) : null}
            <button className="icon-button" onClick={() => loadPageData(user, tab)} title="Refresh"><RefreshCw size={19} /></button>
            <button className="icon-button" onClick={logout} title="Logout"><LogOut size={19} /></button>
          </div>
        </header>
        {error ? <div className={`notice ${error.includes('successful') ? 'success' : ''}`}>{error}</div> : null}
        {toast ? <div className="toast-pop">{toast}</div> : null}
        {loading ? <div className="loading-strip" /> : null}
        {user.role === 'dealer' && data.profile && !data.dealerSubscribed && !dismissSubscriptionBanner ? (
          <SubscriptionBanner
            onSubscribe={() => run((token) => api.activateDealerSubscription(token), 'Subscription activated.')}
            onDismiss={() => setDismissSubscriptionBanner(true)}
          />
        ) : null}
        <main>{page}</main>
      </div>
      {drawerOpen ? <button className="scrim" onClick={() => setDrawerOpen(false)} /> : null}
      {bidProduct ? (
        <BidSetupModal
          product={bidProduct}
          locations={data.buyerLocations}
          rules={data.settings?.bid_rules}
          onClose={() => setBidProduct(null)}
          onStart={(payload) => run((token) => api.startBid(token, payload), 'Bid request started.').then((ok) => ok && setBidProduct(null))}
        />
      ) : null}
      {dealerOffer ? (
        <DealerOfferModal
          request={dealerOffer.request}
          bid={dealerOffer.bid}
          onClose={() => setDealerOffer(null)}
          onSubmit={(payload) => run((token) => api.submitDealerBid(token, payload), 'Bid submitted successfully.').then((ok) => ok && setDealerOffer(null))}
        />
      ) : null}
      {reportBid ? (
        <ReportModal
          bid={reportBid}
          onClose={() => setReportBid(null)}
          onSubmit={(payload) => run((token) => api.createReport(token, payload), 'Dispute report submitted successfully.').then((ok) => ok && setReportBid(null))}
        />
      ) : null}
      {details ? <DetailsModal details={details} user={user} refresh={() => loadPageData(user, tab)} run={run} onClose={() => setDetails(null)} /> : null}
    </div>
  );
}

function renderPage(ctx) {
  const { user, tab } = ctx;
  if (user.role === 'admin') {
    return [
      <DashboardPage title="Admin Dashboard" subtitle="Live control room for platform health, revenue, bids, and alerts." {...ctx} />,
      <AdminUsersPage key="admin-dealers" title="Dealer Management" role="dealer" rows={ctx.data.dealers} {...ctx} />,
      <AdminUsersPage key="admin-buyers" title="Buyer Management" role="buyer" rows={ctx.data.buyers} {...ctx} />,
      <ProductAdminPage {...ctx} />,
      <BidHistoryPage admin {...ctx} />,
      <ReportsPage {...ctx} />,
      <SettingsPage {...ctx} />,
      <ProductSourcesPage user={user} />,
    ][tab] || null;
  }
  if (user.role === 'dealer') {
    return [
      <DashboardPage title="Dealer Dashboard" subtitle="Live overview of requests, bids, wins, subscription, and account status." extra={<DealerRequestsPanel {...ctx} />} {...ctx} />,
      <IncomingRequestsPage {...ctx} />,
      <DealerActiveBidsPage {...ctx} />,
      <DealerHistoryPage {...ctx} />,
      <BusinessProfilePage {...ctx} />,
      <NotificationsPage {...ctx} />,
      <ReportsPage {...ctx} />,
    ][tab] || null;
  }
  return [
    <BuyerHomePage {...ctx} />,
    <BuyerBidPage {...ctx} />,
    <OrdersHistoryPage {...ctx} />,
    <CartPage {...ctx} />,
    <NotificationsPage {...ctx} />,
    <ProfilePage {...ctx} />,
    <ReportsPage {...ctx} />,
  ][tab] || null;
}

function LoginPage({ loading, error, onLogin, onRegister }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  return (
    <AuthLayout>
      <form className="auth-card" onSubmit={(event) => { event.preventDefault(); onLogin(username, password); }}>
        <div className="auth-icon"><HubIcon size={46} /></div>
        <h1>Turacoz BiddingTool Login</h1>
        <p>Find your own products.</p>
        {error ? <div className={`notice ${error.includes('successful') ? 'success' : ''}`}>{error}</div> : null}
        <label className="field-with-icon"><User size={21} /><input aria-label="Username" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoFocus /></label>
        <label className="field-with-icon"><Shield size={21} /><input aria-label="Password" placeholder="Password" value={password} type="password" onChange={(event) => setPassword(event.target.value)} /></label>
        <button className="primary sign-in" disabled={loading}><LogOut size={16} />{loading ? 'Signing in...' : 'Sign in'}</button>
        <button className="link-button" type="button" onClick={onRegister}>Need an account? Register here</button>
      </form>
    </AuthLayout>
  );
}

function RegisterPage({ loading, error, onRegister, onCancel }) {
  const [form, setForm] = useState({ name: '', username: '', password: '', role: 'buyer' });
  const update = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  return (
    <AuthLayout>
      <form className="auth-card" onSubmit={(event) => { event.preventDefault(); onRegister(form); }}>
        <div className="auth-icon"><User size={28} /></div>
        <h1>Create Account</h1>
        <p>Register as a buyer or dealer. Admin accounts are managed from the backend seed process.</p>
        {error ? <div className="notice">{error}</div> : null}
        <label>Full name<input value={form.name} onChange={(event) => update('name', event.target.value)} /></label>
        <label>Username / Email<input value={form.username} onChange={(event) => update('username', event.target.value)} /></label>
        <label>Password<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} /></label>
        <label>Role<select value={form.role} onChange={(event) => update('role', event.target.value)}><option value="buyer">Buyer</option><option value="dealer">Dealer</option></select></label>
        <button className="primary" disabled={loading}>{loading ? 'Creating...' : 'Register'}</button>
        <button className="link-button" type="button" onClick={onCancel}>Back to login</button>
      </form>
    </AuthLayout>
  );
}

function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <div className="auth-art">
        <div>
          <span>Live dealer bidding</span>
          <h2>One backend. Web portal. Flutter mobile app.</h2>
        </div>
      </div>
      {children}
    </div>
  );
}

function DashboardPage({ title, subtitle, data, extra }) {
  const metrics = metricEntries(data.dashboard);
  const charts = data.dashboard?.charts || {};
  const hasCharts = Object.values(charts).some((value) => Array.isArray(value) && value.length);
  return (
    <Page>
      <Section title={title} subtitle={subtitle} icon={Home} />
      <div className="metric-grid">
        {metrics.length ? metrics.map((item) => <Metric key={item.key} label={item.label} value={item.value} />) : <Empty title="No dashboard metrics yet" />}
      </div>
      {hasCharts ? (
        <section className="analytics-stack">
          <h2>Platform Analytics Dashboard</h2>
          {list(charts.revenue_by_month).length ? <BarPanel title="Revenue by Month (Commission Paid)" rows={charts.revenue_by_month} /> : null}
          <div className="grid-two">
            <ComparisonPanel title="Dealers by State" rows={charts.dealers_by_state} />
            <ComparisonPanel title="Dealers by Category" rows={charts.dealers_by_category} />
          </div>
          <div className="grid-two">
            <ComparisonPanel title="Buyers by State" rows={charts.buyers_by_state} />
            <ComparisonPanel title="Products by Category" rows={charts.products_by_category} />
          </div>
          <div className="grid-two">
            <ComparisonPanel title="Bid Success Rate (Status)" rows={charts.bid_success_rate} />
            <ComparisonPanel title="Top Cities" rows={charts.top_cities} />
          </div>
          {list(charts.recent_reports).length ? (
            <Panel title="Recent Reports">
              <AdminList rows={charts.recent_reports} empty="No recent reports.">
                {(row) => (
                  <AdminListItem
                    icon={<FileText size={18} />}
                    title={row.reason || row.title || 'Report'}
                    subtitle={`Reporter: ${row.reporter || ''} | Reported: ${row.reported_party || row.reported || ''}`}
                    trailing={<Status text={row.status || 'open'} />}
                  />
                )}
              </AdminList>
            </Panel>
          ) : null}
        </section>
      ) : (
        <div className="grid-two">
          <Panel title="Recent Notifications">
            <SimpleList rows={data.dashboard?.activity || data.notifications} primary={(row) => row.action || row.title} secondary={(row) => row.entity_type ? `${row.entity_type} | ${dateTime(row.created_at)}` : (row.message || row.body)} />
          </Panel>
          <Panel title="Recent Reports">
            <SimpleList rows={data.dashboard?.charts?.recent_reports || data.dashboard?.recent_reports || data.reports} primary={(row) => row.reason || row.title || row.id} secondary={(row) => row.status || row.description} />
          </Panel>
        </div>
      )}
      {title === 'Admin Dashboard' ? (
        <div className="grid-two">
          <Panel title="Dealer Preview">
            <SimpleList rows={data.dealers} primary={(row) => row.business_name || row.name || row.full_name || row.email} secondary={(row) => `${row.email || ''} | ${row.city || ''}, ${row.state || ''} | ${row.status || 'active'}`} />
          </Panel>
          <Panel title="Buyer Preview">
            <SimpleList rows={data.buyers} primary={(row) => row.full_name || row.name || row.email} secondary={(row) => `${row.email || ''} | Bids: ${row.bid_count || 0} | Purchases: ${row.purchase_count || 0}`} />
          </Panel>
        </div>
      ) : null}
      {extra}
    </Page>
  );
}

function BuyerHomePage({ data, setBidProduct, run, user }) {
  const [products,setProducts]=useState([]);
  const [query,setQuery]=useState('');const [appliedQuery,setAppliedQuery]=useState('');
  const [filters,setFilters]=useState(emptyCatalogFilters);
  const [facets,setFacets]=useState({});const [total,setTotal]=useState(0);
  const [searchMode,setSearchMode]=useState('exact');
  const [catalogLoading,setCatalogLoading]=useState(false);const [catalogError,setCatalogError]=useState('');
  const [selected,setSelected]=useState(null);const requestVersion=useRef(0);
  const [refreshKey,setRefreshKey]=useState(0);
  const search=()=>setAppliedQuery(query.trim());
  useEffect(()=>{
    const next=query.trim();
    if(next===appliedQuery)return;
    const timer=setTimeout(()=>setAppliedQuery(next),250);
    return()=>clearTimeout(timer);
  },[query,appliedQuery]);
  useEffect(()=>{
    const version=++requestVersion.current;setCatalogLoading(true);setCatalogError('');setProducts([]);setTotal(0);setSearchMode('exact');
    api.catalogSearch(user.access_token,catalogParams(filters,{q:appliedQuery,limit:50,offset:0}))
      .then(result=>{if(version===requestVersion.current){setProducts(result.items);setFacets(result.facets);setTotal(result.total);setSearchMode(result.search_mode||'exact');}})
      .catch(error=>{if(version===requestVersion.current)setCatalogError(friendlyErrorMessage(error));})
      .finally(()=>{if(version===requestVersion.current)setCatalogLoading(false);});
    return()=>{requestVersion.current++;};
  },[user.access_token,appliedQuery,filters,refreshKey]);
  const loadMore=async()=>{
    const version=requestVersion.current;setCatalogLoading(true);
    try {const result=await api.catalogSearch(user.access_token,catalogParams(filters,{q:appliedQuery,limit:50,offset:products.length,include_facets:false}));if(version===requestVersion.current)setProducts(old=>[...old,...result.items.filter(row=>!old.some(item=>item.id===row.id))]);}
    catch(error){setCatalogError(friendlyErrorMessage(error));}
    finally{if(version===requestVersion.current)setCatalogLoading(false);}
  };
  const openProduct=async product=>{setSelected(product);try{setSelected(await api.productDetail(user.access_token,product.id));}catch{setSelected(product);}};
  return <Page>
    <div className="toolbar buyer-search"><div className="search-box wide-search"><Search size={17}/><input type="search" value={query} onChange={event=>setQuery(event.target.value)} onKeyDown={event=>{if(event.key==='Enter')search();}} placeholder="Search products, brand, model or specifications..." aria-label="Search products"/></div><button className="primary" disabled={catalogLoading} onClick={search}>Search</button></div>
    <div className="buyer-catalog-layout"><aside className="filter-panel"><div><strong>Filters</strong><button className="link-button" onClick={()=>setFilters(emptyCatalogFilters())}>Reset</button></div><CatalogFilters facets={facets} filters={filters} onChange={setFilters}/></aside>
    <section className="catalog-results"><div className="catalog-summary"><strong>{total.toLocaleString()} matching products · {products.length} loaded</strong><label>Sort: <select value={filters.sort} onChange={event=>setFilters({...filters,sort:event.target.value})}>{['Newest','Year','A-Z','Lowest Price','Highest Price'].map(value=><option key={value}>{value}</option>)}</select></label></div>
    {searchMode==='related'&&<p className="muted search-note">No exact match; showing close product and category matches.</p>}
    {catalogError&&<div role="alert"><p>{catalogError}</p><button disabled={catalogLoading} onClick={()=>setRefreshKey(value=>value+1)}>Retry loading products</button></div>}{catalogLoading&&<p role="status">Loading products…</p>}
    <div className="product-grid buyer-grid">{products.map(product=><ProductCard key={product.id} product={product} onSelect={()=>openProduct(product)} onCart={()=>run(token=>api.addCartItem(token,product.id,1),'Added to cart.')} onBid={()=>setBidProduct(product)}/>)}</div>
    {!catalogLoading&&!catalogError&&!products.length&&<Empty title="No products match these filters."/>}
    {products.length<total&&<button disabled={catalogLoading} onClick={loadMore}>Load more products</button>}</section></div>
    {selected&&<ProductDetailsModal product={selected} onClose={()=>setSelected(null)} onCart={()=>run(token=>api.addCartItem(token,selected.id,1),'Added to cart.')} onBid={()=>{setSelected(null);setBidProduct(selected);}}/>}
  </Page>;
}

function BuyerBidPage({ user, data, setBidProduct, run, setReportBid }) {
  const [requestDetails, setRequestDetails] = useState(null);
  const live = data.bids.filter((bid) => ['active', 'updated'].includes(bid.status) && bid.selectable);
  const requests = data.buyerRequests.filter((request) => request.status === 'active');
  return (
    <Page>
      <Section title="Active Bids & Live Offers" subtitle="Monitor your active bid requests and choose the winning dealer offer." icon={Bolt} />
      <Panel title={`My Active Bid Requests (${requests.length})`}>
        <AdminList rows={requests} empty="You have no active bid requests. Go to Home to request bids.">
          {(req) => {
            const offers = Number(req.offers_count || data.bids.filter((bid) => bid.bid_request_id === req.id).length || 0);
            return (
              <AdminListItem
                icon={offers ? <ClockIcon /> : <AlertIcon />}
                title={`${req.product || req.product_name} (Qty: ${req.quantity || 1})`}
                subtitle={offers ? `Status: ${req.status} | Received Offers: ${offers} | Ends: ${req.expires_at || req.ends_at || ''}` : `Status: ${req.status} | No dealer offers received yet.`}
                onClick={() => setRequestDetails(req)}
                trailing={offers ? <ChevronRight size={16} /> : <button className="danger ghost" onClick={(event) => { event.stopPropagation(); run((token) => api.cancelBuyerRequest(token, req.id), 'Bid request cancelled successfully.'); }}>Change/Cancel</button>}
              />
            );
          }}
        </AdminList>
      </Panel>
      <Panel title={`Live Bid Offers (${live.length})`}>
        <AdminList rows={live} empty="No active bids or dealer offers currently open.">
          {(bid) => <AdminListItem icon={<Bolt size={18} />} title={`${bid.product} | ${money(bid.amount)}`} subtitle="Dealer identity is hidden until you accept this bid | Terms: Warranty & Delivery included" trailing={<button className="primary" onClick={() => run((token) => api.acceptBid(token, bid.id), 'Bid accepted.')}>Accept Offer</button>} />}
        </AdminList>
      </Panel>
      {data.products[0] ? <button className="fab" onClick={() => setBidProduct(data.products[0])}><Plus size={18} /> Start Bid</button> : null}
      <Panel title="Finalized winning offers"><AdminList rows={data.bids.filter((bid) => bid.status === 'won')} empty="No finalized offers yet.">{(bid) => <AdminListItem title={`${bid.product} | ${money(bid.amount)}`} subtitle={`Request ${bid.bid_request_id} | ${bid.dealer}`} trailing={<button onClick={() => setRequestDetails(data.buyerRequests.find((request) => request.id === bid.bid_request_id) || { id: bid.bid_request_id, product: bid.product, status: 'awarded' })}>Contact details</button>} />}</AdminList></Panel>
      {requestDetails ? <BuyerRequestDetailsModal user={user} data={data} onReport={setReportBid} request={data.buyerRequests.find((row) => row.id === requestDetails.id) || requestDetails} bids={data.bids} onClose={() => setRequestDetails(null)} onAccept={(bid) => run((token) => api.acceptBid(token, bid.id), 'Bid accepted.')} onCancel={() => run((token) => api.cancelBuyerRequest(token, requestDetails.id), 'Request closed.')} /> : null}
    </Page>
  );
}

function OrdersHistoryPage({ user, data, setReportBid, setBidProduct, run }) {
  const [tab, setTab] = useState('won');
  const groups = {
    won: data.bids.filter((bid) => bid.status === 'won' || bid.status === 'completed'),
    expired: data.bids.filter((bid) => bid.status === 'expired' && bid.request_status !== 'cancelled'),
    cancelled: data.bids.filter((bid) => bid.request_status === 'cancelled'),
    all: data.bids.filter((bid) => bid.status !== 'active' && bid.status !== 'updated'),
  };
  const rebid = (bid) => run(async (token) => {
    const product = data.products.find((item) => item.id === bid.product_id) || await api.productDetail(token, bid.product_id);
    setBidProduct({ ...product, bidQuantity: bid.quantity || 1 });
  });
  return (
    <Page>
      <Section title="Orders / History" subtitle="Orders, bid history, purchased products, expired bids, cancelled bids, and cart history." icon={ClipboardList} />
      <Panel title="Order History Activity">
        <div className="tab-row">{[['won', 'Accepted (Won)'], ['expired', 'Expired'], ['cancelled', 'Cancelled'], ['all', 'All History']].map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>
        <HistoryList user={user} data={data} bids={groups[tab]} onReport={setReportBid} onRebid={rebid} />
      </Panel>
      <Panel title="Request History">
        <AdminList rows={data.buyerRequests.filter((request) => request.status !== 'active' && (tab === 'all' || request.status === (tab === 'won' ? 'awarded' : tab)))} empty="No closed requests in this tab.">
          {(request) => <AdminListItem icon={<ClipboardList size={18} />} title={`${request.product} (Qty: ${request.quantity})`} subtitle={`Status: ${request.status} | Request: ${request.id}`} trailing={<Status text={request.status} />} />}
        </AdminList>
      </Panel>
    </Page>
  );
}

function CartPage({ data, setBidProduct, setTab, run }) {
  const items = list(data.cart?.items);
  return (
    <Page>
      <Section title="Cart" subtitle="Products added by the buyer. Adjust quantity, remove items, or start bidding." icon={ShoppingCart} />
      <button onClick={() => setTab(0)}>Continue Browsing</button>
      <Panel title={`${items.length} cart items`}>
        <AdminList rows={items} empty="Cart is empty. Add products from catalog.">
          {(item) => {
            const product = data.products.find((candidate) => candidate.id === item.product_id) || data.products.find((candidate) => candidate.name === (item.product || item.name));
            // Cart rows include the product ID and display fields already. Do not
            // make bidding depend on whether the product happens to be in the
            // currently loaded (and possibly searched/filtered) catalogue page.
            const bidProduct = product || (item.product_id ? {
              ...item,
              id: item.product_id,
              name: item.name || item.product || item.product_name,
              bidQuantity: item.quantity || 1,
            } : null);
            return (
              <AdminListItem
                icon={<ShoppingCart size={18} />}
                title={item.name || item.product || item.product_name}
                subtitle={`Quantity ${item.quantity || 1} | ${item.brand || ''} ${item.model || ''}`}
                trailing={(
                  <div className="admin-item-actions">
                    <button className="icon-button" title="Remove item" onClick={() => run((token) => api.removeCartItem(token, item.id), 'Removed from cart.')}><X size={16} /></button>
                    <button className="icon-button" title="Quantity +" disabled={!item.product_id} onClick={() => item.product_id && run((token) => api.addCartItem(token, item.product_id, 1), 'Added to cart.')}><Plus size={16} /></button>
                    <button onClick={() => run((token) => api.removeCartItem(token, item.id), 'Removed from cart.')}>Remove</button>
                    <button className="primary" disabled={!bidProduct} onClick={() => bidProduct && setBidProduct({ ...bidProduct, bidQuantity: item.quantity || 1 })}>Start Bid</button>
                  </div>
                )}
              />
            );
          }}
        </AdminList>
      </Panel>
    </Page>
  );
}

function AdminUsersPage({ title, role, rows, run, setDetails }) {
  const [showFilters, setShowFilters] = useState(false);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ status: '', state: '', city: '', category: '' });
  const splitChoices = (keys) => [...new Set(rows.flatMap(row=>firstText(row,keys).split(',').map(value=>value.trim()).filter(Boolean)))].sort();
  const states = splitChoices(['state','states']);
  const cities = splitChoices(['city','cities']);
  const categories = splitChoices(['categories','category']);
  const roleLabel = role === 'dealer' ? 'dealer' : 'buyer';
  const filteredRows = rows.filter((row) => {
    const q = lower(search);
    if (q) {
      const haystack = role === 'dealer'
        ? [row.id, row.business_name, row.name, row.full_name, row.email, row.phone, row.category, row.categories, row.state, row.city, row.area, row.pincode, row.brands, JSON.stringify(row.service_preferences || {})]
        : [row.full_name, row.name, row.email, row.phone, row.id, row.pincode, row.pincodes, row.state, row.states, row.city, row.cities];
      if (!haystack.some((value) => lower(value).includes(q))) return false;
    }
    if (filters.status && lower(row.status) !== lower(filters.status)) return false;
    if (filters.state && !lower(firstText(row, ['state', 'states'])).includes(lower(filters.state))) return false;
    if (filters.city && !lower(firstText(row, ['city', 'cities'])).includes(lower(filters.city))) return false;
    if (filters.category && !lower(firstText(row, ['categories', 'category'])).includes(lower(filters.category))) return false;
    return true;
  });
  const hasAnalytics = search || Object.values(filters).some(Boolean);
  async function openDetails(token, id) {
    const details = role === 'dealer' ? await api.dealerDetails(token, id) : await api.buyerDetails(token, id);
    setDetails({ ...details, _kind: role });
  }
  return (
    <Page>
      <Section title={title} subtitle={`Search, filter, audit, and moderate live registered ${roleLabel} profiles.`} icon={role === 'dealer' ? Store : Users} />
      <div className="toolbar admin-toolbar">
        <div className="search-box wide-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') run(() => Promise.resolve()); }}
            placeholder={role === 'dealer' ? 'Search Name, Business, Phone, Category, State, District, Brand...' : 'Search Name, ID, Phone, Email, Pincode...'}
          />
        </div>
        <button className="primary" onClick={() => run(() => Promise.resolve())}><RefreshCw size={16} /> Search</button>
        <button onClick={() => setShowFilters((value) => !value)}><Filter size={16} /> Filters</button>
      </div>
      {showFilters ? (
        <Panel title="Filter Drawer">
          <div className="filter-row">
            <select value={filters.status} onChange={(event) => setFilters((old) => ({ ...old, status: event.target.value }))}>
              <option value="">Status</option>
              {['verified', 'flagged', 'banned', 'pending', 'active', 'held', 'suspended'].map((item) => <option key={item} value={item}>{item.toUpperCase()}</option>)}
            </select>
            <select value={filters.state} onChange={(event) => setFilters((old) => ({ ...old, state: event.target.value }))}><option value="">State</option>{states.map((item) => <option key={item}>{item}</option>)}</select>
            <select value={filters.city} onChange={(event) => setFilters((old) => ({ ...old, city: event.target.value }))}><option value="">City</option>{cities.map((item) => <option key={item}>{item}</option>)}</select>
            <select value={filters.category} onChange={(event) => setFilters((old) => ({ ...old, category: event.target.value }))}><option value="">Category</option>{categories.map((item) => <option key={item}>{item}</option>)}</select>
            <button className="link-button" onClick={() => setFilters({ status: '', state: '', city: '', category: '' })}>Reset Filters</button>
            <button onClick={() => setShowFilters(false)}>Close</button>
          </div>
        </Panel>
      ) : null}
      {hasAnalytics ? <SearchAnalytics rows={filteredRows} label={filters.state || filters.city || search || filters.status} /> : null}
      <Panel title={`${filteredRows.length} ${roleLabel}s found`}>
        <AdminList rows={filteredRows} empty="No matching records.">
          {(row) => {
            const id = row.id;
            const name = role === 'dealer'
              ? firstText(row, ['business_name', 'name', 'full_name', 'email'], 'Dealer Profile')
              : firstText(row, ['full_name', 'name', 'email'], 'Buyer Profile');
            const subtitle = role === 'dealer'
              ? `${row.email || ''} | ${row.city || ''}, ${row.state || ''} | categories: ${row.categories || row.category || ''}`
              : `${row.email || ''} | Bids: ${row.bid_count || 0} | Purchases: ${row.purchase_count || 0}`;
            return (
              <AdminListItem
                key={id}
                icon={role === 'dealer' ? <Store size={18} /> : <User size={18} />}
                title={name}
                subtitle={subtitle}
                onClick={() => run((token) => openDetails(token, id))}
                trailing={(
                  <div className="admin-item-actions" onClick={(event) => event.stopPropagation()}>
                    <Status text={row.status || 'active'} />
                    <select value={row.status || 'active'} title="Moderate Status" aria-label={`Status for ${name}`} onChange={(event) => {const status=event.target.value;if(status==='deleted'&&!window.confirm(`Delete ${name}? Account access will be removed and history retained.`)){event.target.value=row.status;return;}run((token) => api.setUserStatus(token, id, status), 'User status updated.');}}>
                      {['pending', 'verified', 'active', 'held', 'suspended', 'flagged', 'banned', 'deleted'].map((status) => <option key={status} value={status}>{status.toUpperCase()}</option>)}
                    </select>
                    <ChevronRight size={16} />
                  </div>
                )}
              />
            );
          }}
        </AdminList>
      </Panel>
    </Page>
  );
}

function ProductAdminPage({ user, data, run, onExport }) {
  const empty = { name: '', category: '', subcategory: '', brand: '', model: '', image_url: '', price_min: '', price_max: '', location: '', status: 'active', specifications: 'Warranty: 1 year' };
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(empty);
  const [filters, setFilters] = useState({ category: 'All', brand: '', sort: 'Newest', product_type:'', years:[] });
  const [catalog, setCatalog] = useState({items:[],total:0,catalog_total:0,brands:[]});
  const [appliedSearch, setAppliedSearch] = useState('');
  const [page, setPage] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [editorError, setEditorError] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { setPage(0); }, [filters]);
  useEffect(() => {
    let cancelled=false;
    setCatalogLoading(true); setCatalogError('');
    api.adminProducts(user.access_token,{q:appliedSearch,category:filters.category==='All'?'':filters.category,brand:filters.brand,sort:filters.sort,product_type:filters.product_type,years:filters.years,limit:50,offset:page*50})
      .then(result=>{if(!cancelled)setCatalog(result);})
      .catch(error=>{if(!cancelled)setCatalogError(friendlyErrorMessage(error));})
      .finally(()=>{if(!cancelled)setCatalogLoading(false);});
    return ()=>{cancelled=true;};
  },[user.access_token,appliedSearch,filters,page,refreshKey,data.products]);
  const searchCatalog=()=>{setPage(0);setAppliedSearch(search.trim());setRefreshKey(value=>value+1);};
  const products=catalog.items;
  const categories=['All',...data.categories.map(category=>category.name)];
  const brands=catalog.brands;
  const distribution=Object.fromEntries((catalog.facets?.categories||[]).map(row=>[row.value,row.count]));
  const filtered=products;
  const update = (key, value) => { setEditorError(''); setForm((old) => ({ ...old, [key]: value })); };
  const openAdd = () => { setEditorError(''); setForm({ ...empty, category: categories.find((item) => item !== 'All') || '' }); setModal('add'); };
  const openEdit = (product) => {
    setEditorError('');
    setForm({ ...empty, ...product, model: product.model || '', location: product.location || '', subcategory: product.item || product.subcategory || '', specifications: toSpecText(product.specifications) || 'Warranty: 1 year' });
    setModal(product.id);
  };
  const draft = () => ({
    name: form.name,
    category: form.category,
    subcategory: form.subcategory,
    brand: form.brand,
    model: form.model,
    image_url: form.image_url,
    price_min: Number(form.price_min || 0),
    price_max: Number(form.price_max || 0),
    location: form.location,
    status: form.status,
    specifications: parseSpecText(form.specifications),
  });
  return (
    <Page>
      <Section title="Products Catalog Management" subtitle="Amazon-style grid interface for managing dynamic product items and categories." icon={Package} />
      <Panel title="Product Catalog Statistics">
        <p><strong>{catalog.catalog_total.toLocaleString()} products in the catalog</strong> | {catalog.total.toLocaleString()} matching products | Showing {products.length} on this page</p>
        <div className="stats-wrap">
          {Object.entries(distribution).map(([category, count]) => <span key={category}><span className="dot" /> <strong>{category}:</strong> {count} products</span>)}
        </div>
      </Panel>
      <div className="toolbar admin-toolbar">
        <div className="search-box wide-search"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search products" onKeyDown={event=>{if(event.key==='Enter')searchCatalog();}} placeholder="Search products by SKU, Name, brand, model, spec..." /></div>
        <button className="primary" disabled={catalogLoading} onClick={searchCatalog}><Search size={16} /> Search</button>
        <button onClick={() => setFiltersOpen((value) => !value)}><Filter size={16} /> Filters</button>
        <button className="button" onClick={() => onExport('products')}><Download size={16} /> Download CSV</button>
        <button className="primary" onClick={openAdd}><Plus size={16} /> + Add Product</button>
      </div>
      <div className="choice-row">
        {categories.map((category) => <button key={category} className={filters.category === category ? 'active' : ''} onClick={() => setFilters((old) => ({ ...old, category, product_type:'',brand:'',years:[] }))}>{category}</button>)}
      </div>
      {filtersOpen ? (
        <Panel title="Catalog Filters">
          <div className="filter-row">
            <select aria-label="Product brand filter" value={filters.brand} onChange={(event) => setFilters((old) => ({ ...old, brand: event.target.value }))}><option value="">Brand</option>{brands.map((brand) => <option key={brand}>{brand}</option>)}</select>
            <select aria-label="Product type filter" value={filters.product_type||''} onChange={event=>setFilters({...filters,product_type:event.target.value})}><option value="">All product types</option>{(catalog.facets?.product_types||[]).map(row=><option key={row.value} value={row.value}>{row.value} ({row.count})</option>)}</select>
            <select value={filters.sort} onChange={(event) => setFilters((old) => ({ ...old, sort: event.target.value }))}>{['Newest', 'Lowest Price', 'Highest Price', 'Name', 'Year'].map((item) => <option key={item}>{item}</option>)}</select>
            <button className="link-button" onClick={() => setFilters({ category: 'All', brand: '', sort: 'Newest', product_type:'', years:[] })}>Reset</button>
          </div>
          <CatalogFilters facets={catalog.facets||{}} filters={filters} onChange={setFilters} specsOnly />
        </Panel>
      ) : null}
      {catalogError && <p role="alert">{catalogError}</p>}
      {catalogLoading && <p role="status">Loading products...</p>}
      <div className="admin-product-grid">
        {filtered.length ? filtered.map((product) => (
          <article className="admin-product-card" key={product.id}>
            <ProductImage key={product.image_url||'none'} product={product} className="admin-product-image" iconSize={44}/>
            <div className="admin-product-body">
              <span>{product.category || 'General'}</span>
              <h3>{product.name}</h3>
              <p>{product.brand} | {product.model}</p>
              <p>{productSpecs(product) || 'No specifications added.'}</p>
              <strong>{product.source === 'icecat' ? `${product.release_year || 'Current'} · Bid for price` : `${money(product.price_min)} - ${money(product.price_max)}`}</strong>
              <Status text={product.status || 'active'} />
            </div>
            <div className="product-actions">
              <button onClick={() => openEdit(product)}><Pencil size={14} /> Edit</button>
              <button className="danger ghost" onClick={() => window.confirm(`Delete ${product.name}? Bidding history will be retained.`) && run((token) => api.deleteProduct(token, product.id), 'Product deleted.')}><Trash2 size={14} /> Delete</button>
            </div>
          </article>
        )) : <Empty title="No products match the filters." />}
      </div>
      <div className="row-actions" aria-label="Product pagination"><button disabled={catalogLoading||page===0} onClick={()=>setPage(value=>value-1)}>Previous products</button><span>Page {page+1} of {Math.max(1,Math.ceil(catalog.total/50))}</span><button disabled={catalogLoading||(page+1)*50>=catalog.total} onClick={()=>setPage(value=>value+1)}>Next products</button></div>
      {modal ? (
        <ProductEditorModal
          title={modal === 'add' ? 'Add Product to Catalog' : 'Edit Product'}
          form={form}
          categories={data.categories}
          onUpdate={update}
          onClose={() => !saving && setModal(null)}
          saving={saving}
          error={editorError}
          onSave={async (imageFile) => {
            setSaving(true); setEditorError('');
            try {
              const ok=await run(async token=>{
                let uploadedImageUrl = '';
                const payload = draft();
                try {
                  if (imageFile) {
                    const uploaded = await api.uploadProductImage(token, imageFile);
                    uploadedImageUrl = uploaded.image_url;
                    payload.image_url = uploadedImageUrl;
                  }
                  return await (modal==='add'?api.createProduct(token,payload):api.updateProduct(token,modal,payload));
                } catch(error) {
                  if (uploadedImageUrl) {
                    try { await api.deleteUnlinkedProductImage(token, uploadedImageUrl); } catch {}
                  }
                  setEditorError(friendlyErrorMessage(error));
                  throw error;
                }
              },modal==='add'?'Product added successfully!':'Product updated.');
              if(ok){if(modal==='add'){setSearch(form.name.trim());setAppliedSearch(form.name.trim());setFilters({category:'All',brand:'',sort:'Newest',product_type:'',years:[]});setPage(0);}setModal(null);setRefreshKey(value=>value+1);}
            } finally {setSaving(false);}
          }}
        />
      ) : null}
    </Page>
  );
}

function BidHistoryPage({ data, run, setReportBid, admin, onExport }) {
  const [tab, setTab] = useState('bids');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [commissionStatus, setCommissionStatus] = useState('');
  const [selectedBid, setSelectedBid] = useState(null);
  const filteredBids = data.bids.filter((bid) => {
    const q = lower(query);
    if (q && ![bid.product, bid.dealer, bid.buyer, bid.id].some((value) => lower(value).includes(q))) return false;
    if (status && (bid.request_status === 'cancelled' ? 'cancelled' : bid.status) !== status) return false;
    return true;
  });
  const filteredPayments = data.payments.filter((payment) => {
    const q = lower(query);
    if (q && ![payment.product, payment.dealer, payment.id].some((value) => lower(value).includes(q))) return false;
    if (commissionStatus && lower(payment.payment_status || payment.status) !== lower(commissionStatus)) return false;
    return true;
  });
  const filteredLogs = data.logs.filter((log) => {
    const q = lower(query);
    return !q || [log.action, log.entity_type, log.event_type].some((value) => lower(value).includes(q));
  });
  const dueCommission = data.payments.filter((item) => ['pending', 'failed'].includes(item.payment_status || item.status)).reduce((sum, item) => sum + Number(item.amount || item.commission_amount || 0), 0);
  const totalCommission = data.payments.reduce((sum, item) => sum + Number(item.amount || item.commission_amount || 0), 0);
  const paidCommission = data.payments.filter((item) => (item.payment_status || item.status) === 'paid').reduce((sum, item) => sum + Number(item.amount || item.commission_amount || 0), 0);
  return (
    <Page>
      <Section title={admin ? 'Bids History & Financial Auditing' : 'Bid History'} subtitle="Auditing trail for bid requests, commission payments, and low-level action logs." icon={Gavel} />
      <div className="toolbar admin-toolbar">
        <div className="search-box wide-search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search within history (products, dealer/buyer names, IDs, actions)..." /></div>
        <button className="button" onClick={() => onExport('bids')}><Download size={16} /> Export Records</button>
      </div>
      {admin ? (
        <Panel title="Revenue & Commission Summary">
          <div className="revenue-row">
            <Metric label="Total Commission Recorded" value={money(totalCommission)} />
            <Metric label="Collected Revenue (Paid)" value={money(paidCommission)} />
            <Metric label="Pending Commission (Outstanding)" value={money(dueCommission)} />
          </div>
        </Panel>
      ) : null}
      <div className="tab-row">
        {[
          ['bids', 'Bid History'],
          ['payments', 'Commissions & Payments'],
          ['logs', 'Audit Logs'],
        ].map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}
      </div>
      {tab === 'bids' ? (
        <Panel title={`${filteredBids.length} bid records`}>
          <div className="filter-row compact"><span>Filter status:</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All</option>{[['won', 'Won'], ['active', 'Active'], ['updated', 'Updated'], ['lost', 'Lost'], ['expired', 'Expired'], ['withdrawn', 'Withdrawn'], ['cancelled', 'Cancelled']].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
          <AdminList rows={filteredBids} empty="No matching bid records.">
            {(bid) => <AdminListItem icon={<Gavel size={18} />} title={bid.product} subtitle={`Dealer: ${bid.dealer || ''} | Amount: ${money(bid.amount)} | Code: ${bid.id}`} onClick={() => setSelectedBid(bid)} trailing={<><Status text={bid.status} /><ChevronRight size={16} /></>} />}
          </AdminList>
        </Panel>
      ) : null}
      {tab === 'payments' ? (
        <Panel title="Commissions & Payments">
          <div className="filter-row compact"><span>Filter payment status:</span><select value={commissionStatus} onChange={(event) => setCommissionStatus(event.target.value)}><option value="">All</option>{['pending', 'paid', 'failed', 'waived', 'refunded'].map((item) => <option key={item}>{item}</option>)}</select></div>
          <AdminList rows={filteredPayments} empty="No commission/payment logs.">
            {(payment) => <AdminListItem icon={<IndianRupee size={18} />} title={payment.product || 'Commission Payment'} subtitle={`Dealer: ${payment.dealer || ''} | Date: ${payment.created_at || ''}`} trailing={<div className="admin-item-actions"><strong>{money(payment.amount || payment.commission_amount)}</strong><Status text={payment.payment_status || payment.status} /><select value={payment.payment_status || payment.status || 'pending'} onChange={(event) => run((token) => api.setPaymentStatus(token, payment.id, event.target.value), 'Payment status updated.')}><option>pending</option><option>paid</option><option>failed</option><option>waived</option><option>refunded</option></select></div>} />}
          </AdminList>
        </Panel>
      ) : null}
      {tab === 'logs' ? (
        <Panel title="Low-level Platform Activity Trails">
          <AdminList rows={filteredLogs} empty="No audit logs recorded.">
            {(log) => <AdminListItem icon={<ReceiptText size={18} />} title={`[${text(log.entity_type || log.event_type).toUpperCase()}] ${log.action || ''}`} subtitle={`Metadata: ${log.metadata_json || log.metadata || '{}'} | Date: ${log.created_at || ''}`} trailing={<span className="muted-small">{log.id}</span>} />}
          </AdminList>
        </Panel>
      ) : null}
      {selectedBid ? <BidDetailsModal bid={selectedBid} payments={data.payments} onClose={() => setSelectedBid(null)} onReport={() => setReportBid?.(selectedBid)} /> : null}
    </Page>
  );
}

function ReportsPage({ user, data, run, onExport }) {
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState('');
  const [recipient, setRecipient] = useState(user.role === 'admin' ? 'both' : 'admin');
  const [note, setNote] = useState('');
  useEffect(() => {
    if (!selected?.id) return undefined;
    let cancelled = false;
    const reportId = selected.id;
    Promise.all([api.report(user.access_token, reportId), api.reportMessages(user.access_token, reportId)])
      .then(([report, messages]) => {
        if (!cancelled) setSelected((current) => current?.id === reportId ? { ...report, _messages: messages } : current);
      }).catch(() => {});
    return () => { cancelled = true; };
  }, [selected?.id, data.reports, user.access_token]);
  async function loadReport(token, id) {
    const report = await api.report(token, id);
    const messages = await api.reportMessages(token, id);
    setSelected({ ...report, _messages: messages });
  }
  const openReport = (id) => run((token) => loadReport(token, id));
  const sendMessage = () => {
    const textValue = message.trim();
    if (!selected || !textValue) return;
    run(async (token) => {
      await api.sendReportMessage(token, selected.id, recipient, textValue);
      await loadReport(token, selected.id);
      setMessage('');
    }, 'Message sent.');
  };
  const updateStatus = (status) => {
    if (!selected) return;
    run(async (token) => {
      await api.updateReportStatus(token, selected.id, status, note);
      await loadReport(token, selected.id);
    }, 'Report status updated.');
  };
  const requestClosure = () => {
    if (!selected) return;
    const reason = window.prompt('Cancellation reason', 'User requested closure') || '';
    if (reason.trim().length < 3) return;
    run(async (token) => {
      await api.requestReportClosure(token, selected.id, reason.trim());
      await loadReport(token, selected.id);
    }, 'Closure requested.');
  };
  const decideClosure = (status) => {
    if (!selected) return;
    const reason = window.prompt(`${status === 'approved' ? 'Approve' : 'Reject'} closure note`, '') || '';
    run(async (token) => {
      await api.closureDecision(token, selected.id, status, reason.trim());
      await loadReport(token, selected.id);
    }, `Closure ${status}.`);
  };
  return (
    <Page>
      <Section title={user.role === 'admin' ? 'Reports & Dispute Center' : 'Reports / Support'} subtitle={user.role === 'admin' ? 'Moderate dispute logs, selective broadcast message threads, and resolve client complaints.' : 'View your reports and their review status.'} icon={FileText} />
      <div className="toolbar">
        <button className="button" onClick={() => onExport('reports')}><Download size={16} /> Export CSV</button>
      </div>
      <div className="reports-layout">
        <Panel title={`${data.reports.length} report records`}>
          <AdminList rows={data.reports} empty="No reports filed.">
            {(row) => (
              <AdminListItem
                icon={<FileText size={18} />}
                title={row.reason || 'General Dispute'}
                subtitle={[
                  `Reporter: ${row.reporter || row.reporter_name || ''}`,
                  `Reported Party: ${row.reported_party || row.reported_name || ''}`,
                  row.closure_requested_status === 'requested' ? `Requested by: ${row.closure_requested_by_name || 'Reporter'}` : '',
                  row.closure_reason ? `Reason: ${row.closure_reason}` : '',
                ].filter(Boolean).join(' | ')}
                onClick={() => openReport(row.id)}
                trailing={<><Status text={row.status || 'open'} /><ChevronRight size={16} /></>}
              />
            )}
          </AdminList>
        </Panel>
        {selected ? (
          <ReportDetailsPanel
            user={user}
            details={{ ...selected, _messages: mergeMessages(selected._messages || [], data.liveMessages[selected.id] || []) }}
            message={message}
            setMessage={setMessage}
            recipient={recipient}
            setRecipient={setRecipient}
            note={note}
            setNote={setNote}
            onSend={sendMessage}
            onStatus={updateStatus}
            onRequestClosure={requestClosure}
            onClosureDecision={decideClosure}
            onClose={() => setSelected(null)}
          />
        ) : null}
      </div>
    </Page>
  );
}

function ReportDetailsPanel({ user, details, message, setMessage, recipient, setRecipient, note, setNote, onSend, onStatus, onRequestClosure, onClosureDecision, onClose }) {
  const closureRequested = details.closure_requested_status === 'requested';
  return (
    <Panel title={details.reason || `Report ${details.id}`}>
      {user.role === 'admin' && details.contacts_unlocked && <BidConversation bidId={details.bid_id} user={user} readOnly />}
      <div className="report-header-card">
        <div>
          <strong>Report ID: {details.id} | Bid ID: {details.bid_id || 'N/A'} | Status: {text(details.status).toUpperCase()}</strong>
          {details.closure_requested_status && details.closure_requested_status !== 'none' ? <span>Closure request: {details.closure_requested_status} | Requested by: {details.closure_requested_by_name || 'Reporter'}</span> : null}
        </div>
        <button className="icon-button" onClick={onClose} title="Close details"><X size={18} /></button>
      </div>
      <div className="report-product-card">
        <strong>Product: {details.product || 'N/A'}</strong>
        <span>Brand: {details.product_brand || 'N/A'}</span>
        <span>Quantity: {details.quantity || 1} pcs</span>
        <span>Deal Amount: {money(details.bid_amount)}</span>
        <span>Warranty: {details.warranty || 'N/A'}</span>
        <span>Delivery: {details.delivery || 'N/A'} days</span>
        {details.description ? <p>Dispute Description: {details.description}</p> : null}
      </div>
      {user.role === 'admin' && <><div className="message-list chat-thread">
        {list(details._messages).length ? list(details._messages).map((msg) => {
          const mine = msg.sender_id === user.id || (user.role === 'admin' && ['admin', 'agent'].includes(msg.sender_role));
          return (
            <div className={`message bubble ${mine ? 'mine' : ''}`} key={msg.id}>
              <div><strong>{msg.sender_name || msg.sender_role || 'System'}</strong><span>To: {text(msg.recipient_group || 'both').toUpperCase()}</span></div>
              <p>{msg.message}</p>
              <small>{msg.created_at}</small>
            </div>
          );
        }) : <Empty title="No messages in this chat yet." />}
      </div>
      <div className="inline-form">
        {user.role === 'admin'
          ? <select value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="both">Both</option><option value="buyer">Buyer Only</option><option value="dealer">Dealer Only</option></select>
          : <select value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="both">To Everyone (Public)</option><option value="admin">To Admin Only (Private)</option></select>}
        <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Type your message/resolution details here..." />
        <button className="icon-button" onClick={onSend} title="Send message"><Send size={18} /></button>
      </div></>}
      {user.role === 'admin' ? (
        <div className="inline-form">
          <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Admin note" />
          {['resolved', 'rejected', 'closed', 'escalated'].map((status) => <button key={status} onClick={() => onStatus(status)}>{status}</button>)}
          {closureRequested ? (
            <>
              <button className="success" onClick={() => onClosureDecision('approved')}>Approve Closure</button>
              <button className="danger ghost" onClick={() => onClosureDecision('rejected')}>Reject Closure</button>
            </>
          ) : null}
        </div>
      ) : (
        <button onClick={onRequestClosure}>Cancel Report</button>
      )}
    </Panel>
  );
}

function SettingsPage({ data, run }) {
  const [rules, setRules] = useState(data.settings.bid_rules || {});
  const [limits, setLimits] = useState(data.settings.location_rules || {});
  const [eligibility, setEligibility] = useState(data.settings.dealer_rules || {});
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!dirty) {
      setRules(data.settings.bid_rules || {});
      setLimits(data.settings.location_rules || {});
      setEligibility(data.settings.dealer_rules || {});
    }
  }, [data.settings, dirty]);
  const numberField = (label, key, values, setter, min, max) => <label key={key}>{label}<input type="number" min={min} max={max} step="any" required value={values[key] ?? ''} onChange={(event) => { setDirty(true); setter({ ...values, [key]: event.target.value }); }} /></label>;
  const save = async (event, key, values) => {
    event.preventDefault();
    const numericKeys = key === 'bid_rules' ? ['expiry_hours', 'min_time_hours', 'max_time_hours', 'max_dealers', 'min_bidding_increment'] : key === 'location_rules' ? ['max_radius_km'] : ['min_rating_threshold'];
    const payload = { ...values };
    numericKeys.forEach((field) => { payload[field] = Number(values[field]); });
    if (await run((token) => api.saveSetting(token, key, payload), 'Platform rules saved.')) setDirty(false);
  };
  return (
    <Page>
      <Section title="Platform Rules & Categories" subtitle="Manage bid duration, dealer eligibility, service limits and product types." icon={Settings} />
      <Panel title="Subscription billing"><p>Dealers bid with an active subscription. Winning a bid adds no commission. Contact details are revealed immediately to the buyer and winning dealer.</p></Panel>
      <Panel title="Bid timing & rules"><form onSubmit={(event) => save(event, 'bid_rules', rules)}>
        <div className="form-grid">
          {numberField('Default bidding duration (hours)', 'expiry_hours', rules, setRules, 1 / 60, 72)}
          {numberField('Minimum bidding duration (hours)', 'min_time_hours', rules, setRules, 1 / 60, 72)}
          {numberField('Maximum bidding duration (hours)', 'max_time_hours', rules, setRules, 1 / 60, 72)}
          {numberField('Maximum invited dealers (0 = unlimited)', 'max_dealers', rules, setRules, 0, 10000)}
          {numberField('Minimum price decrease (Rs., 0 = disabled)', 'min_bidding_increment', rules, setRules, 0, 9999999999.99)}
        </div><p>Buyers choose a duration within these limits. Set minimum, default and maximum to the same value for a fixed duration. Existing requests keep their saved deadline.</p><button className="button" type="submit">Save bid rules</button>
      </form></Panel>
      <Panel title="Location limits"><form onSubmit={(event) => save(event, 'location_rules', limits)}><div className="form-grid">{numberField('Maximum service radius (km)', 'max_radius_km', limits, setLimits, 0.1, 5000)}</div><button className="button" type="submit">Save location rules</button></form></Panel>
      <Panel title="Dealer eligibility"><form onSubmit={(event) => save(event, 'dealer_rules', eligibility)}><div className="form-grid">{numberField('Minimum dealer rating', 'min_rating_threshold', eligibility, setEligibility, 0, 5)}<label>Verification required<input type="checkbox" checked={eligibility.verification_required !== false} onChange={(event) => { setDirty(true); setEligibility({ ...eligibility, verification_required: event.target.checked }); }} /></label></div><button className="button" type="submit">Save dealer rules</button></form></Panel>
      <Panel title="Hierarchical Category Tree">
        <CategoryManager categories={data.categories} run={run} />
      </Panel>
    </Page>
  );
}

function AdminList({ rows = [], empty, children }) {
  if (!rows.length) return <Empty title={empty || 'No records found.'} />;
  return <div className="admin-list">{rows.map((row, index) => <React.Fragment key={row.id || index}>{children(row, index)}</React.Fragment>)}</div>;
}

function AdminListItem({ icon, title, subtitle, trailing, onClick }) {
  return (
    <div
      className={`admin-list-item ${onClick ? 'clickable' : ''}`}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (event) => { if (event.key === 'Enter' || event.key === ' ') onClick(event); } : undefined}
    >
      <div className="avatar-icon">{icon}</div>
      <div className="admin-list-main">
        <strong>{title}</strong>
        <span>{subtitle}</span>
      </div>
      <div className="admin-list-trailing">{trailing}</div>
    </div>
  );
}

function SearchAnalytics({ rows, label }) {
  const counts = {
    verified: rows.filter((row) => ['verified', 'active'].includes(lower(row.status))).length,
    flagged: rows.filter((row) => lower(row.status) === 'flagged').length,
    banned: rows.filter((row) => lower(row.status) === 'banned').length,
    pending: rows.filter((row) => lower(row.status) === 'pending').length,
  };
  const categoryCounts = {};
  const cityCounts = {};
  rows.forEach((row) => {
    firstText(row, ['categories', 'category']).split(',').map((item) => item.trim()).filter(Boolean).forEach((item) => { categoryCounts[item] = (categoryCounts[item] || 0) + 1; });
    const city = firstText(row, ['city', 'cities']);
    if (city) cityCounts[city] = (cityCounts[city] || 0) + 1;
  });
  return (
    <section className="search-analytics">
      <h3>Search Analytics: "{label}"</h3>
      <div className="analytics-line">
        <strong>Total matching: {rows.length}</strong>
        <span className="green-text">Verified: {counts.verified}</span>
        <span className="orange-text">Flagged: {counts.flagged}</span>
        <span className="red-text">Banned: {counts.banned}</span>
        <span className="blue-text">Pending: {counts.pending}</span>
      </div>
      {Object.keys(categoryCounts).length ? <ChipSummary title="Categories:" items={categoryCounts} /> : null}
      {Object.keys(cityCounts).length > 1 ? <ChipSummary title="Cities:" items={cityCounts} /> : null}
    </section>
  );
}

function ChipSummary({ title, items }) {
  return (
    <div className="chip-summary">
      <strong>{title}</strong>
      <div className="chip-row">{Object.entries(items).map(([key, value]) => <span className="chip" key={key}>{key}: {value}</span>)}</div>
    </div>
  );
}

function ProductEditorModal({ title, form, categories, onUpdate, onClose, onSave, saving, error }) {
  const [imageFile, setImageFile] = useState(null);
  const topCategories = categories.filter((item) => !item.parent_id);
  const selectedParent = topCategories.find((item) => item.name === form.category);
  const childCategories = selectedParent
    ? list(selectedParent.items)
    : topCategories.flatMap((item) => list(item.items)).concat(categories.filter((item) => item.parent_id));
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={event=>{event.preventDefault();onSave(imageFile);}}>
      {form.has_bid_history ? <p>This product has bidding history. Name, category, item, brand and model are locked; prices, status and specifications can be edited.</p> : null}
      {error && <p role="alert">{error}</p>}
      <div className="form-grid">
        <label className="wide">Product Name (Required)<input required minLength={2} maxLength={255} disabled={!!form.has_bid_history} value={form.name} onChange={(event) => onUpdate('name', event.target.value)} /></label>
        <label>Category (Required)
          <select aria-label="Category (Required)" required disabled={!!form.has_bid_history} value={form.category} onChange={(event) => { onUpdate('category', event.target.value); onUpdate('subcategory', ''); }}>
            <option value="">Select category</option>
            {topCategories.length ? topCategories.map((item) => <option key={item.id} value={item.name}>{item.name}</option>) : <option value={form.category}>{form.category || 'General'}</option>}
          </select>
        </label>
        <label>Subcategory / Item (Optional)
          <select aria-label="Subcategory / Item (Optional)" disabled={!!form.has_bid_history} value={form.subcategory || ''} onChange={(event) => onUpdate('subcategory', event.target.value)}>
            <option value="">Select item</option>
            {childCategories.map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}
          </select>
        </label>
        <label>Brand Name (select or type new)<input required maxLength={190} disabled={!!form.has_bid_history} value={form.brand} onChange={(event) => onUpdate('brand', event.target.value)} /></label>
        <label>Model Name / Number<input maxLength={190} disabled={!!form.has_bid_history} value={form.model} onChange={(event) => onUpdate('model', event.target.value)} /></label>
        {form.image_url ? <div className="wide product-image-upload-current"><ProductImage product={{name:form.name || 'Product image',image_url:form.image_url}} className="admin-product-image" iconSize={28}/><span>Current image is kept unless you upload a replacement.</span></div> : <p className="wide">No image is attached yet.</p>}
        <label className="wide">Upload product image<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setImageFile(event.target.files?.[0] || null)} /></label>
        <p className="wide">Choose a JPEG, PNG, or WebP file. It will be stored in the site’s local product image folder; image URLs are not accepted.</p>
        {imageFile ? <p className="wide">Selected image: {imageFile.name} (saved locally when you save the product)</p> : null}
        <label>Min Price (Rs.)<input type="number" min="0" step="0.01" value={form.price_min} onChange={(event) => onUpdate('price_min', event.target.value)} /></label>
        <label>Max Price (Rs.)<input type="number" min={Number(form.price_min)||0} step="0.01" value={form.price_max} onChange={(event) => onUpdate('price_max', event.target.value)} /></label>
        <label>Status<select aria-label="Status" value={form.status || 'active'} onChange={(event) => onUpdate('status', event.target.value)}><option value="active">Active</option><option value="inactive">Inactive</option><option value="archived">Archived</option></select></label>
        <label>Location<input value={form.location || ''} onChange={(event) => onUpdate('location', event.target.value)} /></label>
        <label className="wide">Specifications<textarea aria-label="Specifications" value={form.specifications} onChange={(event) => onUpdate('specifications', event.target.value)} /></label>
      </div>
      <button className="primary" type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save Product'}</button>
      </form>
    </Modal>
  );
}

function BidDetailsModal({ bid, payments, onClose, onReport, user, liveMessages = [] }) {
  const linkedPayments = payments.filter((payment) => payment.bid_id === bid.id);
  const won = ['won', 'completed'].includes(String(bid.status || '').toLowerCase());
  return (
    <Modal title={bid.product} onClose={onClose} wide>
      <div className="details-grid">
        <KV label="Bid ID" value={bid.id} />
        <KV label="Buyer" value={bid.buyer} />
        <KV label="Dealer" value={bid.dealer} />
        <KV label="Amount" value={money(bid.amount)} />
        <KV label="Status" value={bid.status} />
        <KV label="Ends" value={dateTime(bid.ends_at)} />
      </div>
      {won ? (
        <Panel title="Dealer Contact Details">
          <div className="details-grid">
            <KV label="Dealer Business" value={bid.dealer} />
            <KV label="Owner / Contact Name" value={bid.owner_name || bid.ownerName} />
            <KV label="Phone" value={bid.dealer_phone || bid.dealerPhone} />
            <KV label="Email" value={bid.dealer_email || bid.dealerEmail} />
            <KV label="Business Address" value={bid.business_address || bid.businessAddress} />
            <KV label="GST Number" value={bid.gst_number || bid.gstNumber} />
            <KV label="Warranty" value={bid.warranty_text || bid.warrantyText} />
            <KV label="Delivery Time" value={bid.delivery_time || bid.deliveryTime ? `${bid.delivery_time || bid.deliveryTime}` : ''} />
            <KV label="Free Gifts" value={bid.free_gifts || bid.freeGifts} />
            <KV label="Extra Services" value={bid.extra_services || bid.extraServices} />
            <KV label="Dealer Notes" value={bid.notes} />
          </div>
        </Panel>
      ) : null}
      {linkedPayments.length > 0 && <Panel title="Historical commission payments">
        <SimpleList rows={linkedPayments} primary={(row) => `${row.product || bid.product} | ${money(row.amount || row.commission_amount)}`} secondary={(row) => `${row.payment_status || row.status} | ${row.created_at || ''}`} />
      </Panel>}
      {won && user?.role === 'admin' && <BidConversation bidId={bid.id} user={user} liveMessages={liveMessages} readOnly />}
      {onReport ? <button onClick={onReport}>Report</button> : null}
    </Modal>
  );
}

function CategoryManager({ categories, run }) {
  const emptyDraft = { mode: 'add-parent', id: '', parent_id: '', name: '' };
  const [draft, setDraft] = useState(emptyDraft);
  const parents = categories.filter((item) => !item.parent_id);
  const childrenFor = (parent) => {
    const nested = list(parent.items);
    if (nested.length) return nested;
    return categories.filter((item) => String(item.parent_id || '') === String(parent.id || ''));
  };
  const reset = () => setDraft(emptyDraft);
  const startParent = () => setDraft(emptyDraft);
  const startChild = (parent) => setDraft({ mode: 'add-child', id: '', parent_id: parent.id, name: '' });
  const editParent = (parent) => setDraft({ mode: 'edit-parent', id: parent.id, parent_id: '', name: parent.name });
  const editChild = (child, parent) => setDraft({ mode: 'edit-child', id: child.id, parent_id: parent.id, name: child.name });
  const save = () => {
    const name = draft.name.trim();
    if (!name) return;
    run(
      (token) => draft.id
        ? api.updateCategory(token, draft.id, name, draft.parent_id || null)
        : api.createCategory(token, name, draft.parent_id || null),
      draft.id ? 'Category updated.' : 'Category saved.',
    ).then((ok) => ok && reset());
  };
  const draftTitle = draft.mode === 'add-child'
    ? `Add Subcategory${parents.find((item) => item.id === draft.parent_id)?.name ? ` under ${parents.find((item) => item.id === draft.parent_id)?.name}` : ''}`
    : draft.mode === 'edit-child'
      ? 'Edit Subcategory'
      : draft.mode === 'edit-parent'
        ? 'Edit Category'
        : 'Add Parent Category';
  return (
    <div className="category-manager">
      <div className="category-action-bar">
        <div>
          <strong>Hierarchical Category Tree</strong>
          <span>{parents.length} parent categories</span>
        </div>
        <button className="primary" onClick={startParent}><Plus size={16} /> Add Category</button>
      </div>
      <Panel title={draftTitle}>
        <div className="category-editor-row">
          <label>Name<input placeholder="Category / item name" value={draft.name} onChange={(event) => setDraft((old) => ({ ...old, name: event.target.value }))} /></label>
          <label>Parent
            <select value={draft.parent_id} disabled={draft.mode === 'edit-parent'} onChange={(event) => setDraft((old) => ({ ...old, parent_id: event.target.value, mode: event.target.value ? (old.id ? 'edit-child' : 'add-child') : (old.id ? 'edit-parent' : 'add-parent') }))}>
              <option value="">Top level category</option>
              {parents.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <div className="category-editor-actions">
            <button className="primary" disabled={!draft.name.trim()} onClick={save}><Check size={16} /> {draft.id ? 'Save Changes' : draft.parent_id ? 'Add Subcategory' : 'Add Category'}</button>
            <button onClick={reset}>Clear</button>
          </div>
        </div>
      </Panel>
      <div className="category-tree">
        {parents.length ? parents.map((parent) => (
          <section className="category-group" key={parent.id}>
            <header>
              <div className="category-title">
                <Layers size={18} />
                <strong>{parent.name}</strong>
                <span>{childrenFor(parent).length} items</span>
              </div>
              <div className="row-actions">
                <button onClick={() => startChild(parent)}><Plus size={14} /> Add Subcategory</button>
                <button onClick={() => editParent(parent)}><Pencil size={14} /> Edit</button>
                <button className="danger ghost" onClick={() => window.confirm(`Delete ${parent.name} and its child items?`) && run((token) => api.deleteCategory(token, parent.id), 'Category deleted.')}><Trash2 size={14} /> Delete</button>
              </div>
            </header>
            <div className="category-child-list">
              {childrenFor(parent).length ? childrenFor(parent).map((child) => (
                <div className="category-child-row" key={child.id}>
                  <span><ChevronRight size={14} /> {child.name}</span>
                  <div className="row-actions">
                    <button className="icon-button" title="Edit subcategory" onClick={() => editChild(child, parent)}><Pencil size={14} /></button>
                    <button className="icon-button danger" title="Delete subcategory" onClick={() => window.confirm(`Delete ${child.name}?`) && run((token) => api.deleteCategory(token, child.id), 'Category deleted.')}><X size={14} /></button>
                  </div>
                </div>
              )) : <span className="muted-small">No items/subcategories yet.</span>}
            </div>
          </section>
        )) : <Empty title="No categories created yet." />}
      </div>
    </div>
  );
}

function BarPanel({ title, rows }) {
  const values = list(rows);
  const max = Math.max(1, ...values.map((row) => Number(row.value || row.amount || row.count || 0)));
  return (
    <Panel title={title}>
      <div className="bar-list">
        {values.map((row, index) => {
          const value = Number(row.value || row.amount || row.count || 0);
          return <div key={row.label || row.month || index}><span>{row.label || row.month || row.name}</span><div><i style={{ width: `${Math.max(4, (value / max) * 100)}%` }} /></div><strong>{money(value)}</strong></div>;
        })}
      </div>
    </Panel>
  );
}

function ComparisonPanel({ title, rows = [] }) {
  const values = list(rows);
  const max = Math.max(1, ...values.map((row) => Number(row.value || row.count || 0)));
  return (
    <Panel title={title}>
      {values.length ? (
        <div className="comparison-list">
          {values.map((row, index) => {
            const value = Number(row.value || row.count || 0);
            return <div key={row.label || row.name || index}><span>{row.label || row.name || row.status || 'Item'}</span><div><i style={{ width: `${Math.max(4, (value / max) * 100)}%` }} /></div><strong>{value}</strong></div>;
          })}
        </div>
      ) : <Empty title="No chart data." />}
    </Panel>
  );
}

function FilterChecks({ title, values, selected, onToggle }) {
  return (
    <div className="filter-checks">
      <strong>{title}</strong>
      {values.map((value) => (
        <label className="check" key={value}>
          <input type="checkbox" checked={selected.includes(value)} onChange={() => onToggle(value)} />
          {value}
        </label>
      ))}
    </div>
  );
}

function AlertIcon() {
  return <span className="status-icon warning"><Flag size={18} /></span>;
}

function ClockIcon() {
  return <span className="status-icon info"><Bolt size={18} /></span>;
}

function ProductDetailsModal({ product, onClose, onCart, onBid }) {
  const specs = Object.entries(product.specifications || {});
  const technicalGroups = list(product.technical_specifications);
  const softwareGroups = list(product.software_specifications);
  return (
    <Modal title={product.name} onClose={onClose} wide>
      <div className="product-detail-layout">
        <ProductImage key={product.image_url||'none'} product={product} className="product-detail-art" iconSize={72}/>
        <div className="product-detail-info">
          <span className="eyebrow">{product.category}{product.subcategory || product.item ? ` / ${product.subcategory || product.item}` : ''}</span>
          <h2>{product.brand} {product.model}</h2>
          <strong>Price discovered through dealer bidding</strong>
          <Status text={product.status || 'active'} />
          <div className="details-grid">
            <KV label="Brand" value={product.brand} />
            <KV label="Model" value={product.model} />
            <KV label="Release year" value={product.release_year} />
          </div>
          {product.description || product.summary_description ? <p>{product.description || product.summary_description}</p> : null}
        </div>
      </div>
      <Panel title="Specification highlights">
        {specs.length ? <div className="details-grid">{specs.map(([key, value]) => <KV key={key} label={key} value={value} />)}</div> : <Empty title="No specifications added." />}
      </Panel>
      <SpecificationGroups title="Technical specifications" groups={technicalGroups} />
      <SpecificationGroups title="Software specifications" groups={softwareGroups} />
      <div className="row-actions">
        <button className="success" onClick={onCart}><ShoppingCart size={15} /> Add to Cart</button>
        <button className="primary" onClick={onBid}><Bolt size={15} /> Start Bid</button>
      </div>
    </Modal>
  );
}

function SpecificationGroups({ title, groups }) {
  if (!groups.length) return <Panel title={title}><Empty title={`No ${title.toLowerCase()} available.`} /></Panel>;
  return (
    <Panel title={title}>
      <div className="specification-groups">
        {groups.map((group) => (
          <section key={`${group.id}-${group.name}`} className="specification-group">
            <h3>{group.name}</h3>
            <div className="details-grid">
              {list(group.features).map((feature) => <KV key={`${feature.id}-${feature.name}`} label={feature.name} value={feature.value} />)}
            </div>
          </section>
        ))}
      </div>
    </Panel>
  );
}

function BuyerRequestDetailsModal({ user, data, onReport, request, bids, onClose, onAccept, onCancel }) {
  const offers = bids.filter((bid) => bid.bid_request_id === request.id && bid.status !== 'withdrawn');
  const winner = offers.find((bid) => bid.status === 'won');
  return (
    <Modal title={`Bid Request: ${request.product || request.product_name}`} onClose={onClose} wide>
      <div className="info-badge-row">
        <span><Package size={14} /> Quantity: {request.quantity || 1}</span>
        <span><InfoIcon /> Status: {request.status || request.request_status || 'active'}</span>
        {request.status === 'active' && onCancel ? <button className="danger ghost" onClick={onCancel}>Cancel Request</button> : null}
      </div>
      <Panel title={`Dealer Offers (${offers.length})`}>
        <AdminList rows={offers} empty="No dealer offers received yet.">
          {(bid) => (
            <AdminListItem
              icon={<Bolt size={18} />}
              title={bid.dealer || 'Dealer'}
              subtitle={[
                bid.discount_amount || bid.discountAmount ? `Includes Discount: -${money(bid.discount_amount || bid.discountAmount)}` : '',
                `Delivery Time: ${bid.delivery_time || bid.deliveryTime || ''}`,
                `Warranty: ${bid.warranty_text || bid.warrantyText || 'None'}`,
                bid.free_gifts || bid.freeGifts ? `Free Gifts: ${bid.free_gifts || bid.freeGifts}` : '',
                bid.extra_services || bid.extraServices ? `Extra Services: ${bid.extra_services || bid.extraServices}` : '',
                bid.notes ? `Notes: ${bid.notes}` : '',
              ].filter(Boolean).join(' | ')}
              trailing={<div className="admin-item-actions"><strong className="green-text">{money(bid.amount)}</strong><Status text={bid.status} />{request.status === 'active' && <button className="primary" disabled={!bid.selectable} onClick={() => onAccept(bid)}>{bid.selectable ? 'Accept Offer' : 'Dealer unavailable'}</button>}</div>}
            />
          )}
        </AdminList>
      </Panel>
      {winner && <Panel title="Winning dealer contact"><p>{winner.dealer} | {winner.owner_name} | {winner.dealer_phone} | {winner.dealer_email}</p><p>{winner.business_address}</p><button onClick={() => onReport(winner)}>Report dealer</button></Panel>}
    </Modal>
  );
}

function InfoIcon() {
  return <span aria-hidden="true" className="mini-icon">i</span>;
}

function HistoryList({ user, data, bids, onReport, onRebid }) {
  const [details, setDetails] = useState(null);
  if (!bids.length) return <Empty title="No records in this tab." />;
  return (
    <>
      <div className="history-list">
        {bids.map((bid) => (
          <article className="history-card" key={bid.id}>
            <div className="history-head">
              <Status text={bid.status} />
              <strong>{bid.product}</strong>
              <b>{money(bid.amount)}</b>
            </div>
            {bid.status === 'won' || bid.status === 'completed' ? (
              <div className="contact-block">
                <strong>Dealer Contact Details</strong>
                {bid.owner_name || bid.ownerName ? <span><User size={14} /> {bid.owner_name || bid.ownerName}</span> : null}
                {bid.dealer_phone || bid.dealerPhone ? <span><PhoneIcon /> {bid.dealer_phone || bid.dealerPhone}</span> : null}
                {bid.dealer_email || bid.dealerEmail ? <span><MailIcon /> {bid.dealer_email || bid.dealerEmail}</span> : null}
                {bid.business_address || bid.businessAddress ? <span><MapPin size={14} /> {bid.business_address || bid.businessAddress}</span> : null}
                {bid.gst_number || bid.gstNumber ? <span><ReceiptText size={14} /> GST: {bid.gst_number || bid.gstNumber}</span> : null}
              </div>
            ) : null}
            <div className="row-actions">
              <button onClick={() => setDetails(bid)}><Eye size={14} /> Details</button>
              {bid.status !== 'lost' ? <button className="danger ghost" onClick={() => onReport(bid)}><Flag size={14} /> Report</button> : null}
              <button className="primary" onClick={() => onRebid(bid)}>Rebid</button>
            </div>
          </article>
        ))}
      </div>
      {details ? <BidDetailsModal user={user} liveMessages={data.liveBidMessages[details.id] || []} bid={data.bids.find((bid) => bid.id === details.id) || details} payments={[]} onClose={() => setDetails(null)} onReport={() => onReport(details)} /> : null}
    </>
  );
}

function PhoneIcon() {
  return <span aria-hidden="true" className="mini-icon">p</span>;
}

function MailIcon() {
  return <span aria-hidden="true" className="mini-icon">@</span>;
}

function DealerBidDetailModal({ user, data, onReport, bid, mine, onClose }) {
  const status = String(bid.status || '').toLowerCase();
  const won = ['won', 'completed'].includes(status);
  const commissionStatus = String(bid.commission_payment_status || bid.commissionPaymentStatus || '').toLowerCase();
  const buyerDetailsUnlocked = won && mine;
  const buyerAddress = [
    bid.buyer_address || bid.buyerAddress,
    bid.buyer_area || bid.buyerArea,
    bid.buyer_city || bid.buyerCity,
    bid.buyer_state || bid.buyerState,
    bid.buyer_pincode || bid.buyerPincode,
  ].filter(Boolean).join(', ');
  return (
    <Modal title={mine ? `My Bid: ${bid.product}` : `Competitor Bid details (${bid.dealer || 'Dealer'})`} onClose={onClose}>
      <div className="detail-list">
        <KV label={mine ? 'Your Offer' : 'Bid Offer Amount'} value={money(bid.amount)} />
        {Number(bid.discount_amount || bid.discountAmount || 0) > 0 ? <KV label="Discount Given" value={`-${money(bid.discount_amount || bid.discountAmount)}`} /> : null}
        <KV label="Delivery Duration" value={`${bid.delivery_time || bid.deliveryTime || ''}`} />
        <KV label="Warranty Terms" value={bid.warranty_text || bid.warrantyText || 'None'} />
        <KV label="Status" value={String(status).toUpperCase()} />
        {bid.free_gifts || bid.freeGifts ? <KV label="Free Gifts" value={bid.free_gifts || bid.freeGifts} /> : null}
        {bid.extra_services || bid.extraServices ? <KV label="Extra Services" value={bid.extra_services || bid.extraServices} /> : null}
        {bid.notes ? <KV label="Special Notes" value={bid.notes} /> : null}
        {won ? (
          <>
            <hr />
            {buyerDetailsUnlocked ? (
              <>
                <strong className="green-text">Buyer Details</strong>
                <KV label="Name" value={bid.buyer || bid.buyer_name || bid.buyerName} />
                <KV label="Phone" value={bid.buyer_phone || bid.buyerPhone} />
                <KV label="Email" value={bid.buyer_email || bid.buyerEmail} />
                <KV label="Address" value={buyerAddress || bid.buyer_address || bid.buyerAddress} />
              </>
            ) : <p>Buyer contacts are shared with the winning dealer.</p>}
            <KV label="Bid Amount" value={money(bid.amount)} />
            <KV label="Warranty" value={bid.warranty_text || bid.warrantyText} />
            <KV label="Delivery" value={bid.delivery_time || bid.deliveryTime ? `${bid.delivery_time || bid.deliveryTime}` : ''} />
            <KV label="Notes" value={bid.notes} />
          </>
        ) : null}
        {status === 'lost' ? (
          <>
            <hr />
            <strong>Winning Offer Details</strong>
            <KV label="Winning Price" value={money(bid.winning_amount || bid.winningAmount)} />
            <KV label="Difference" value={money(bid.price_difference || bid.priceDifference)} />
            <KV label="Why You Lost" value={bid.lost_reason || bid.lostReason || 'buyer selected another offer'} />
            {bid.winning_warranty_text || bid.winningWarrantyText ? <KV label="Warranty" value={bid.winning_warranty_text || bid.winningWarrantyText} /> : null}
            {bid.winning_delivery_time || bid.winningDeliveryTime ? <KV label="Delivery" value={`${bid.winning_delivery_time || bid.winningDeliveryTime}`} /> : null}
            {bid.winning_free_gifts || bid.winningFreeGifts ? <KV label="Additional Benefits" value={bid.winning_free_gifts || bid.winningFreeGifts} /> : null}
            {bid.winning_extra_services || bid.winningExtraServices ? <KV label="Other Offer Details" value={bid.winning_extra_services || bid.winningExtraServices} /> : null}
            {bid.winning_notes || bid.winningNotes ? <KV label="Notes" value={bid.winning_notes || bid.winningNotes} /> : null}
            <p>Winning dealer identity is hidden.</p>
          </>
        ) : null}
      </div>
      <Panel title={`All offers for request ${bid.bid_request_id}`}><AdminList rows={data.bids.filter((offer) => offer.bid_request_id === bid.bid_request_id && offer.status !== 'withdrawn')} empty="No offers.">{(offer) => <AdminListItem title={`${offer.dealer} | ${money(offer.amount)}`} subtitle={`${offer.warranty_text || 'No warranty'} | ${offer.delivery_time || ''}`} trailing={<Status text={offer.status} />} />}</AdminList></Panel>
      {buyerDetailsUnlocked && <button onClick={() => onReport(bid)}>Report buyer</button>}
    </Modal>
  );
}

function ChipSelector({ title, options, values, onChange }) {
  const choices = options.map((option) => typeof option === 'string' ? { id: option, name: option } : option);
  const choiceIds = new Set(choices.map((option) => option.id));
  const selected = values.filter((value) => choiceIds.has(value));
  const change = (next) => onChange([...values.filter((value) => !choiceIds.has(value)), ...next]);
  return (
    <div className="chip-summary">
      <strong>{title}</strong>
      <div className="chip-row">
        {selected.map((value) => <span className="chip" key={value}>{choices.find((option) => option.id === value)?.name || value}<button type="button" aria-label={`Remove ${choices.find((option) => option.id === value)?.name || value}`} onClick={() => change(selected.filter((item) => item !== value))}><X size={12} /></button></span>)}
        <select aria-label={title} value="" onChange={(event) => event.target.value && !selected.includes(event.target.value) && change([...selected, event.target.value])}>
          <option value="">{title.includes('Items') ? 'Add Item' : 'Add Category'}</option>
          {choices.filter((option) => !selected.includes(option.id)).map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      </div>
    </div>
  );
}

function IncomingRequestsPage(ctx) {
  return <Page><DealerRequestsPanel {...ctx} /></Page>;
}

function DealerRequestsPanel({ data, setDealerOffer }) {
  return (
    <Panel title="Incoming Bid Requests">
      <AdminList rows={data.dealerRequests} empty="No eligible requests at this moment.">
        {(row) => (
          <AdminListItem
            icon={<Status text={row.status || 'active'} />}
            title={row.product || row.product_name || ''}
            subtitle={`Request ${row.id} | ${row.buyer_area || row.location || row.area || ''} | Qty ${row.quantity || 1} | Ends ${dateTime(row.expires_at || row.ends_at)}`}
            trailing={<button className="primary" onClick={() => setDealerOffer({ request: row })}>Submit Bid</button>}
          />
        )}
      </AdminList>
    </Panel>
  );
}

function DealerActiveBidsPage({ user, data, setDealerOffer, setReportBid }) {
  const [details, setDetails] = useState(null);
  const active = data.bids.filter((bid) => bid.status === 'active' || bid.status === 'updated');
  const myBids = active.filter((bid) => bid.dealer === 'My Shop' || bid.is_mine || bid.mine);
  const otherBids = active.filter((bid) => !myBids.includes(bid));
  return (
    <Page>
      <Section title="Active Bids" subtitle="Submit, preview, edit, withdraw, and monitor current bid offers before expiry." icon={Pencil} />
      <DealerRequestsPanel data={data} setDealerOffer={setDealerOffer} />
      <Panel title="My active submitted bids">
        <AdminList rows={myBids} empty="No submitted bids yet.">
          {(bid) => (
            <AdminListItem
              icon={<Check size={18} />}
              title={bid.product}
              subtitle={`Request ${bid.bid_request_id} | My Offer: ${money(bid.amount)} | Warranty: ${bid.warranty_text || bid.warrantyText || 'None'} | Delivery: ${bid.delivery_time || bid.deliveryTime || ''} | Ends ${dateTime(bid.ends_at)}`}
              onClick={() => setDetails({ bid, mine: true })}
              trailing={<div className="admin-item-actions"><button onClick={(event) => { event.stopPropagation(); setDealerOffer({ request: { id: bid.bid_request_id, product: bid.product }, bid }); }}><Pencil size={14} /> Edit</button><Status text={bid.status} /></div>}
            />
          )}
        </AdminList>
      </Panel>
      <Panel title="Other dealers' bids (Live marketplace)">
        <AdminList rows={otherBids} empty="No other bids submitted by competitors yet.">
          {(bid) => (
            <AdminListItem
              icon={<Users size={18} />}
              title={`${bid.product} (${bid.dealer || 'Competitor'})`}
              subtitle={`Request ${bid.bid_request_id} | Offer: ${money(bid.amount)} | Warranty: ${bid.warranty_text || bid.warrantyText || 'None'} | Delivery: ${bid.delivery_time || bid.deliveryTime || ''} | Ends ${dateTime(bid.ends_at)}`}
              onClick={() => setDetails({ bid, mine: false })}
              trailing={<Status text={bid.status} />}
            />
          )}
        </AdminList>
      </Panel>
      <Panel title="Finalized requests"><AdminList rows={data.bids.filter((bid) => bid.status === 'won')} empty="No finalized requests yet.">{(bid) => <AdminListItem title={`${bid.product} | Winning offer ${money(bid.amount)}`} subtitle={`Request ${bid.bid_request_id} | ${bid.warranty_text || ''} | ${bid.delivery_time || ''}`} trailing={<button onClick={() => setDetails({ bid, mine: bid.is_mine })}>{bid.is_mine ? 'Contact details' : 'Final offer details'}</button>} />}</AdminList></Panel>
      {details ? <DealerBidDetailModal user={user} data={data} onReport={setReportBid} bid={data.bids.find((bid) => bid.id === details.bid.id) || details.bid} mine={details.mine} onClose={() => setDetails(null)} /> : null}
    </Page>
  );
}

function DealerHistoryPage({ user, data, run, setReportBid, onExport }) {
  const [tab, setTab] = useState('won');
  const [details, setDetails] = useState(null);
  const ownBids = data.bids.filter((bid) => bid.is_mine);
  const groups = {
    won: ownBids.filter((bid) => bid.status === 'won'),
    lost: ownBids.filter((bid) => bid.status === 'lost'),
    pending: ownBids.filter((bid) => bid.status === 'active' || bid.status === 'updated'),
    completed: ownBids.filter((bid) => !['active', 'updated'].includes(bid.status)),
  };
  return (
    <Page>
      <Section title="Dealer Bid History" subtitle="Overview of all your bid activity, outcomes, and earnings breakdown." icon={ClipboardList} />
      <button className="button" onClick={() => onExport('bids')}><Download size={16} /> Export History</button>
      <Panel title="Bid Summary">
        <div className="tab-row">{[['won', 'Won Bids'], ['lost', 'Lost Bids'], ['pending', 'Pending Bids'], ['completed', 'Closed Bids']].map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>
        <AdminList rows={groups[tab]} empty="No records in this tab.">
          {(bid) => (
            <AdminListItem
              icon={<Gavel size={18} />}
              title={bid.product}
              subtitle={`${bid.buyer || 'Buyer details hidden'} | ${money(bid.amount)}`}
              onClick={() => setDetails(bid)}
              trailing={(
                <div className="admin-item-actions">
                  <Status text={bid.status} />
                  <button onClick={(event) => { event.stopPropagation(); setDetails(bid); }}><Eye size={14} /> Details</button>
                  {bid.status !== 'lost' ? <button className="danger ghost" onClick={(event) => { event.stopPropagation(); setReportBid(bid); }}><Flag size={14} /> Report</button> : null}
                  {['active', 'updated'].includes(bid.status) ? (
                    <button className="danger ghost" onClick={(event) => {
                      event.stopPropagation();
                      if (window.confirm('Are you sure you want to withdraw this bid? If you exceed 3 withdrawals, your profile may be flagged.')) {
                        run((token) => api.withdrawBid(token, bid.id), 'Bid withdrawn.');
                      }
                    }}>Withdraw Bid</button>
                  ) : null}
                </div>
              )}
            />
          )}
        </AdminList>
      </Panel>
      {details ? <DealerBidDetailModal user={user} data={data} onReport={setReportBid} bid={data.bids.find((bid) => bid.id === details.id) || details} mine onClose={() => setDetails(null)} /> : null}
    </Page>
  );
}

function BusinessProfilePage({ user, data, run, onDeleteAccount }) {
  const profile = data.profile || {};
  const [form, setForm] = useState({});
  const [pinConfirmed, setPinConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [companyChoices, setCompanyChoices] = useState([]);
  const [companyChoicesLoading, setCompanyChoicesLoading] = useState(false);
  const [companySearch, setCompanySearch] = useState('');
  const dirty = useRef(false);
  useEffect(() => {
    if (dirty.current) return;
    setForm({
      business_name: profile.business_name || profile.name || '',
      full_name: profile.full_name || profile.owner_name || user.name || '',
      gst_number: profile.gst_number || '',
      phone: profile.phone || '',
      description: profile.description || '',
      service_radius_km: profile.service_radius_km || profile.radius_km || 25,
      address: profile.address || profile.business_address || '',
      area: profile.area || '',
      city: profile.city || '',
      state: profile.state || '',
      country: profile.country || 'India',
      pincode: profile.pincode || '',
      latitude: profile.latitude || 0,
      longitude: profile.longitude || 0,
      branches: Array.isArray(profile.branches) ? profile.branches.join(', ') : (profile.branches || ''),
      service_cities: Array.isArray(profile.service_cities)
        ? profile.service_cities.join(', ')
        : (profile.branches || ''),
      service_states: Array.isArray(profile.service_states) ? profile.service_states.join(', ') : (profile.service_states || ''),
      service_districts: Array.isArray(profile.service_districts) ? profile.service_districts.join(', ') : (profile.service_districts || ''),
      delivery_method: profile.delivery_method || 'radius',
      categories: Array.isArray(profile.category_ids) ? profile.category_ids : list(profile.categories),
      brands: Array.isArray(profile.brands) ? profile.brands : text(profile.brands).split(',').map((item) => item.trim()).filter(Boolean),
    });
  }, [data.profile, user]);
  const parentCategories = list(data.categories).filter((item) => !item.parent_id);
  const selectedCategoryNames = list(form.categories);
  const companyScopes = React.useMemo(() => {
    const selected = new Set(selectedCategoryNames);
    return parentCategories
      .filter(parent => selected.has(parent.id) || list(parent.items).some(item => selected.has(item.id)))
      .map(parent => {
        const selectedChildren = list(parent.items).filter(item => selected.has(item.id));
        return {
          categories: [parent.name],
          product_types: selectedChildren.map(item => item.name),
        };
      });
  }, [data.categories, form.categories]);
  const companyScopeKey = JSON.stringify(companyScopes);
  useEffect(() => {
    let cancelled = false;
    setCompanyChoices([]);
    setCompanyChoicesLoading(companyScopes.length > 0);
    if (!companyScopes.length) return () => { cancelled = true; };

    const allProductTypesSelected = companyScopes.every(scope => scope.product_types.length === 0);
    const allProductTypesRestricted = companyScopes.every(scope => scope.product_types.length > 0);
    const companyQueries = allProductTypesSelected || allProductTypesRestricted
      ? [{
          categories: companyScopes.flatMap(scope => scope.categories),
          product_types: allProductTypesRestricted
            ? [...new Set(companyScopes.flatMap(scope => scope.product_types))]
            : [],
        }]
      : companyScopes;

    // Group compatible scopes, but keep mixed full-category/product-type
    // selections separate so the category scopes remain an OR.
    Promise.all(companyQueries.map(scope => api.catalogSearch(user.access_token, {
      ...scope,
      limit: 1,
      offset: 0,
      include_facets: true,
    })))
      .then(results => {
        if (cancelled) return;
        const choices = [...new Set(results.flatMap(result =>
          (result.facets?.brands || []).map(row => row.value).filter(Boolean),
        ))].sort((a, b) => a.localeCompare(b));
        setCompanyChoices(choices);
        const available = new Set(choices.map(value => value.toLocaleLowerCase()));
        setForm(current => {
          if (JSON.stringify(current.categories || []) !== JSON.stringify(selectedCategoryNames)) return current;
          const brands = list(current.brands);
          const inScope = brands.filter(value => available.has(value.toLocaleLowerCase()));
          if (inScope.length === brands.length) return current;
          dirty.current = true;
          return { ...current, brands: inScope };
        });
      })
      .catch(() => {
        if (!cancelled) setCompanyChoices([]);
      })
      .finally(() => {
        if (!cancelled) setCompanyChoicesLoading(false);
      });
    return () => { cancelled = true; };
  }, [user.access_token, companyScopeKey]);
  const update = (key, value) => { dirty.current = true; setForm((old) => ({ ...old, [key]: value })); };
  const save = async () => {
    setSaving(true);
    const ok = await run((token) => api.updateProfile(token, {
    ...form,
    service_radius_km: Number(form.service_radius_km),
    branches: text(form.branches).split(',').map((item) => item.trim()).filter(Boolean),
    service_states: text(form.service_states).split(',').map((item) => item.trim()).filter(Boolean),
    service_cities: text(form.service_cities).split(',').map((item) => item.trim()).filter(Boolean),
    service_districts: text(form.service_districts).split(',').map((item) => item.trim()).filter(Boolean),
    latitude: Number(form.latitude || 0),
    longitude: Number(form.longitude || 0),
    }), 'Business profile updated successfully!');
    if (ok) dirty.current = false;
    setSaving(false);
  };
  // Wait for the saved profile to populate the form before accepting edits.
  // Otherwise an early keystroke marks the empty form dirty and drops hydration.
  if (!data.profile || !form.delivery_method) return <Page><Section title="Business Profile & Configurations" icon={Store} /><Panel><p role="status">Loading your saved business profile…</p></Panel></Page>;
  const setCategoryCoverage = (parent, all, toggledItem) => {
    const children = list(parent.items);
    const selected = new Set(selectedCategoryNames);
    const currentItems = children.filter(item => selected.has(item.id));
    const full = selected.has(parent.id) && (currentItems.length === 0 || currentItems.length === children.length);
    let nextItems;
    if (toggledItem) {
      if (full) nextItems = children.filter(item => item.id !== toggledItem.id);
      else nextItems = currentItems.some(item => item.id === toggledItem.id)
        ? currentItems.filter(item => item.id !== toggledItem.id)
        : [...currentItems, toggledItem];
      if (nextItems.length === children.length) {
        selected.add(parent.id);
        children.forEach(item => selected.delete(item.id));
      } else if (nextItems.length) {
        selected.add(parent.id);
        children.forEach(item => selected.delete(item.id));
        nextItems.forEach(item => selected.add(item.id));
      } else {
        selected.delete(parent.id);
        children.forEach(item => selected.delete(item.id));
      }
    } else if (all) {
      selected.add(parent.id);
      children.forEach(item => selected.delete(item.id));
    } else {
      selected.delete(parent.id);
      children.forEach(item => selected.delete(item.id));
    }
    update('categories', [...selected]);
  };
  const companyOptions = companyChoices
    .filter(value => value.toLowerCase().includes(companySearch.toLowerCase()));
  const selectedCompaniesOutsideScope = !companyChoicesLoading
    ? list(form.brands).filter(value => !companyChoices.some(choice => choice.toLocaleLowerCase() === value.toLocaleLowerCase()))
    : [];
  return (
    <Page>
      <Section title="Business Profile & Configurations" subtitle="Manage owner name, shop details, GST numbers, item types, and service coverage rules." icon={Store} />
      {data.dealerSubscribed ? <span className="subscription-chip"><Check size={16} /> Subscribed</span> : null}
      <Panel title="Store & Verification Info">
        <div className="form-grid">
          <label>Shop Name<input value={form.business_name || ''} onChange={(event) => update('business_name', event.target.value)} /></label>
          <label>Owner / Contact Name<input value={form.full_name || ''} onChange={(event) => update('full_name', event.target.value)} /></label>
          <label>GST Number<input value={form.gst_number || ''} onChange={(event) => update('gst_number', event.target.value)} /></label>
          <label>Store Phone<input value={form.phone || ''} onChange={(event) => update('phone', event.target.value)} /></label>
          <label className="wide">Business Description<textarea value={form.description || ''} onChange={(event) => update('description', event.target.value)} placeholder="Describe your product quality, shipping standards, or support terms..." /></label>
        </div>
      </Panel>
      <Panel title="Service Coverage & Operating Scope">
        <div className="form-grid">
          <label>Service Radius (km)<input type="number" min="0.1" step="0.1" disabled={form.delivery_method !== 'radius'} value={form.service_radius_km ?? ''} onChange={(event) => update('service_radius_km', event.target.value)} /></label>
          <label>Delivery Method<select value={form.delivery_method || 'radius'} onChange={(event) => update('delivery_method', event.target.value)}><option value="radius">Radius</option><option value="city">Cities</option><option value="district">District</option><option value="state">State</option></select></label>
          <label>Operating Branches<input value={form.branches || ''} onChange={(event) => update('branches', event.target.value)} /></label>
          <label>Service Cities<input disabled={form.delivery_method !== 'city'} value={form.service_cities || ''} onChange={(event) => update('service_cities', event.target.value)} placeholder="Separate cities with commas" /></label>
          <label>Service States<input disabled={form.delivery_method === 'radius'} value={form.service_states || ''} onChange={(event) => update('service_states', event.target.value)} placeholder="Separate states with commas" /></label>
          <label>Service Districts<input disabled={form.delivery_method !== 'district'} value={form.service_districts || ''} onChange={(event) => update('service_districts', event.target.value)} placeholder="Separate districts with commas" /></label>
        </div>
        <p>{form.delivery_method === 'radius' ? 'Radius uses your shop pin. City/state coverage lists do not limit this circle.' : 'List the places you serve, separated by commas. For cities/districts, service states limit matches; otherwise your shop state is used.'}</p>
      </Panel>
      <Panel title="Product Offerings & Categories">
        <p>Select a whole category or specific product types. Leave every category unchecked to include all categories. Manufacturer choices are loaded only from the selected categories and product types.</p>
        <div className="form-grid">
          {parentCategories.map(parent => {
            const children = list(parent.items);
            const selected = new Set(selectedCategoryNames);
            const chosenChildren = children.filter(item => selected.has(item.id));
            const all = selected.has(parent.id) && (chosenChildren.length === 0 || chosenChildren.length === children.length);
            const partial = chosenChildren.length > 0 && chosenChildren.length < children.length;
            return <fieldset className="wide dealer-category-checks" key={parent.id}>
              <legend><label className="check"><input type="checkbox" checked={all} ref={node => { if (node) node.indeterminate = partial; }} onChange={event => setCategoryCoverage(parent, event.target.checked)} />{parent.name} <small>{all ? 'All products' : partial ? `${chosenChildren.length} selected` : selected.size === 0 ? 'No category restriction' : 'Not selected'}</small></label></legend>
              <div className="dealer-product-checks">{children.map(item => <label className="check" key={item.id}><input type="checkbox" checked={all || selected.has(item.id)} onChange={() => setCategoryCoverage(parent, false, item)} />{item.name}</label>)}</div>
            </fieldset>;
          })}
        </div>
        <label className="wide dealer-company-filter">Companies / manufacturers you deal with
          {companyScopes.length ? <>
            <input value={companySearch} onChange={event => setCompanySearch(event.target.value)} placeholder="Search companies in selected categories" />
            <span className="muted">Leave companies unchecked to accept every manufacturer available in the selected categories and product types. Changing the selection removes companies that do not sell within the new scope.</span>
            {companyChoicesLoading ? <span className="muted" role="status">Loading manufacturers for your selection…</span> : null}
            <div className="dealer-company-checks">{companyOptions.map(company => <label className="check" key={company}><input type="checkbox" checked={list(form.brands).some(value => value.toLocaleLowerCase() === company.toLocaleLowerCase())} onChange={() => update('brands', list(form.brands).some(value => value.toLocaleLowerCase() === company.toLocaleLowerCase()) ? list(form.brands).filter(value => value.toLocaleLowerCase() !== company.toLocaleLowerCase()) : [...list(form.brands), company])} />{company}</label>)}</div>
            {!companyChoicesLoading && !companyOptions.length ? <span className="muted">No manufacturers were found for this selection.</span> : null}
          </> : <span className="muted">Select a category or product type to see only the manufacturers available in that selection.</span>}
          {selectedCompaniesOutsideScope.length ? <div className="dealer-company-checks" aria-label="Saved companies outside the current selection">
            <span className="muted">Saved company restrictions outside this selection:</span>
            {selectedCompaniesOutsideScope.map(company => <button type="button" className="link-button" key={company} onClick={() => update('brands', list(form.brands).filter(value => value.toLocaleLowerCase() !== company.toLocaleLowerCase()))}>Remove {company}</button>)}
          </div> : null}
        </label>
      </Panel>
      <Panel title="Physical Address">
        <div className="form-grid">
          <label className="wide">Shop Street Address<input value={form.address || ''} onChange={(event) => update('address', event.target.value)} /></label>
          <label>Area / Locality<input value={form.area || ''} onChange={(event) => update('area', event.target.value)} /></label>
          <label>City<input value={form.city || ''} onChange={(event) => update('city', event.target.value)} /></label>
          <label>State<input value={form.state || ''} onChange={(event) => update('state', event.target.value)} /></label>
          <label>Country<input value={form.country || ''} onChange={(event) => update('country', event.target.value)} /></label>
          <label>Pincode<input value={form.pincode || ''} onChange={(event) => update('pincode', event.target.value)} /></label>
        </div>
        <h4>Drag/Tap Map to set shop coordinates & Address details</h4>
        <MapCoordinatePicker
          token={user.access_token}
          radiusKm={form.delivery_method === 'radius' ? Math.min(Number(form.service_radius_km) || 0, Number(data.settings?.location_rules?.max_radius_km ?? 5000)) : 0}
          onConfirmedChange={setPinConfirmed}
          latitude={form.latitude}
          longitude={form.longitude}
          onChange={(coords) => {
            update('latitude', coords.latitude);
            update('longitude', coords.longitude);
          }}
          onDetails={(details) => {
            if ('address' in details) update('address', details.address);
            if ('area' in details) update('area', details.area);
            if ('city' in details) update('city', details.city);
            if ('state' in details) update('state', details.state);
            if ('country' in details) update('country', details.country);
            if ('pincode' in details) update('pincode', details.pincode);
          }}
        />
      </Panel>
      <div className="row-actions">
        <button className="primary" disabled={saving || !data.profile || (form.delivery_method === 'radius' && !pinConfirmed)} onClick={save}><Check size={16} /> {saving ? 'Saving…' : 'Save Business Profile'}</button>
        <button className="danger ghost" onClick={onDeleteAccount}>Delete Account</button>
        {!data.dealerSubscribed ? <button onClick={() => run((token) => api.activateDealerSubscription(token), 'Subscription activated.')}>Subscribe Now</button> : null}
      </div>
    </Page>
  );
}

function NotificationsPage({ data, run }) {
  return (
    <Page>
      <div className="section-action-row">
        <Section title="Notifications" subtitle="Live platform updates for bids, reports, payments, and account changes." icon={Bell} />
        <button className="small-action" onClick={() => run((token) => api.markNotificationsRead(token), 'Notifications marked read.')}>Mark all read</button>
      </div>
      <div className="list-stack">
        {data.notifications.map((item) => (
          <button className={`notification ${item.is_read ? '' : 'unread'}`} key={item.id} onClick={() => run((token) => api.markNotificationRead(token, item.id))}>
            <div><strong>{item.title}</strong><p>{item.message || item.body}</p></div>
            <span>{dateTime(item.created_at)}</span>
          </button>
        ))}
      </div>
    </Page>
  );
}

function ProfilePage({ user, data, run, onDeleteAccount }) {
  const [profile, setProfile] = useState({});
  const [pinConfirmed, setPinConfirmed] = useState(false);
  const emptyLocation = { label: '', address: '', country: 'India', state: '', city: '', area: '', pincode: '', latitude: 0, longitude: 0, is_default: false };
  const [location, setLocation] = useState(emptyLocation);
  const [editingLocationId, setEditingLocationId] = useState('');
  const initialLocationLoaded = useRef(false);
  useEffect(() => {
    const next = data.profile || user || {};
    setProfile({
      ...next,
      preferred_radius: next.preferred_radius || next.matching_radius_km || next.radius_km || 15,
      latitude: next.latitude || 0,
      longitude: next.longitude || 0,
    });
    const first = list(data.buyerLocations)[0];
    if (first && !initialLocationLoaded.current) {
      initialLocationLoaded.current = true;
      setLocation({
        label: first.label || '',
        address: first.address || first.address_line || '',
        country: first.country || 'India',
        state: first.state || '',
        city: first.city || '',
        area: first.area || '',
        pincode: first.pincode || '',
        latitude: first.latitude || 0,
        longitude: first.longitude || 0,
        is_default: first.is_default === true || first.is_default === 1,
      });
      setEditingLocationId(first.id || '');
    }
  }, [data.profile, data.buyerLocations, user]);
  const update = (key, value) => setProfile((old) => ({ ...old, [key]: value }));
  const updateLocation = (key, value) => setLocation((old) => ({ ...old, [key]: value }));
  const loadLocation = (row) => {
    setEditingLocationId(row.id || '');
    setLocation({
      label: row.label || '',
      address: row.address || row.address_line || '',
      country: row.country || 'India',
      state: row.state || '',
      city: row.city || '',
      area: row.area || '',
      pincode: row.pincode || '',
      latitude: row.latitude || 0,
      longitude: row.longitude || 0,
      is_default: row.is_default === true || row.is_default === 1,
    });
  };
  const newLocation = () => {
    initialLocationLoaded.current = true;
    setEditingLocationId('');
    setLocation({ ...emptyLocation, is_default: !list(data.buyerLocations).length });
  };
  const saveProfile = () => run((token) => api.updateProfile(token, {
    full_name: profile.full_name || profile.name || user.name,
    phone: profile.phone || '',
    address: location.address || profile.address || '',
    country: location.country || profile.country || 'India',
    state: location.state || profile.state || '',
    city: location.city || profile.city || '',
    area: location.area || profile.area || '',
    pincode: location.pincode || profile.pincode || '',
    preferred_radius: Number(profile.preferred_radius || 15),
    latitude: Number(location.latitude || profile.latitude || 0),
    longitude: Number(location.longitude || profile.longitude || 0),
  }), 'Profile saved successfully!');
  const saveLocation = () => {
    if (!pinConfirmed) return;
    if (Number(location.latitude || 0) === 0 && Number(location.longitude || 0) === 0) {
      window.alert('Set a map pin before saving location.');
      return Promise.resolve();
    }
    if (!location.state?.trim() || !location.city?.trim()) {
      window.alert('Search and confirm the map pin so city and state are filled before saving.');
      return Promise.resolve();
    }
    if (!location.address?.trim() && !location.area?.trim()) {
      window.alert('Add a street address or area before saving this location.');
      return Promise.resolve();
    }
    return run((token) => api.saveBuyerLocation(token, {
      ...location,
      label: location.label || location.address || 'Saved location',
      country: location.country || 'India',
      latitude: Number(location.latitude || 0),
      longitude: Number(location.longitude || 0),
      is_default: Boolean(location.is_default || !list(data.buyerLocations).length),
    }, editingLocationId || undefined), editingLocationId ? 'Saved location updated.' : 'Location saved.').then((ok) => ok && newLocation());
  };
  return (
    <Page>
      <Section title="Profile & Default Location Settings" subtitle="Configure personal information, default shipping addresses, pincode matching radius, and raising dispute support." icon={User} />
      <Panel title="Account & Location Details">
        <div className="form-grid">
          <label>Full name<input value={profile.full_name || profile.name || ''} onChange={(event) => update('full_name', event.target.value)} /></label>
          <label>Email<input value={profile.email || ''} onChange={(event) => update('email', event.target.value)} /></label>
          <label>Phone<input value={profile.phone || ''} onChange={(event) => update('phone', event.target.value)} /></label>
          <label>Buyer matching radius (km)<input value={profile.preferred_radius || ''} onChange={(event) => update('preferred_radius', event.target.value)} /></label>
        </div>
        {list(data.buyerLocations).length ? (
          <>
            <h4>Saved Locations</h4>
            <AdminList rows={data.buyerLocations} empty="No saved locations.">
              {(row) => (
                <AdminListItem
                  icon={<MapPin size={18} />}
                  title={row.label || 'Saved location'}
                  subtitle={`${row.area || ''}, ${row.city || ''}, ${row.state || ''} | ${row.latitude || ''}, ${row.longitude || ''}`}
                  trailing={(
                    <div className="admin-item-actions" onClick={(event) => event.stopPropagation()}>
                      {row.is_default ? <Status text="default" /> : null}
                      <button onClick={() => loadLocation(row)}><Pencil size={14} /> Edit</button>
                      <button disabled={row.is_default === true || row.is_default === 1} onClick={() => run((token) => api.setDefaultBuyerLocation(token, row.id), 'Default location updated.')}>Set default</button>
                      <button className="danger ghost" onClick={() => run((token) => api.deleteBuyerLocation(token, row.id), 'Location deleted.')}>Delete</button>
                    </div>
                  )}
                />
              )}
            </AdminList>
          </>
        ) : null}
        <div className="form-grid">
          <label>Location name<input value={location.label} onChange={(event) => updateLocation('label', event.target.value)} placeholder="Home, Office, Clinic..." /></label>
          <label className="wide">Street Address<input value={location.address} onChange={(event) => updateLocation('address', event.target.value)} /></label>
          <label>Area / Neighborhood<input value={location.area} onChange={(event) => updateLocation('area', event.target.value)} /></label>
          <label>City<input value={location.city} onChange={(event) => updateLocation('city', event.target.value)} /></label>
          <label>State<input value={location.state} onChange={(event) => updateLocation('state', event.target.value)} /></label>
          <label>Country<input value={location.country} onChange={(event) => updateLocation('country', event.target.value)} /></label>
          <label>Pincode<input value={location.pincode} onChange={(event) => updateLocation('pincode', event.target.value)} /></label>
          <label className="check"><input type="checkbox" checked={Boolean(location.is_default)} onChange={(event) => updateLocation('is_default', event.target.checked)} /> Default location</label>
        </div>
        <h4>Drag/Tap Map to set shipping coordinates & address details</h4>
        <MapCoordinatePicker
          token={user.access_token}
          key={editingLocationId || 'new-location'}
          onConfirmedChange={setPinConfirmed}
          latitude={location.latitude}
          longitude={location.longitude}
          onChange={(coords) => setLocation((old) => ({ ...old, ...coords }))}
          onDetails={(details) => setLocation((old) => ({
            ...old,
            address: details.address ?? old.address,
            city: details.city ?? old.city,
            state: details.state ?? old.state,
            country: details.country ?? old.country,
            pincode: details.pincode ?? old.pincode,
            area: details.area ?? old.area,
            label: old.label || [details.area, details.city].filter(Boolean).join(', '),
          }))}
        />
        <div className="info-badge-row">
          <span>Email: {user.email}</span>
          <span>Status: {user.status}</span>
          <span>Saved: {list(data.buyerLocations).length}/3</span>
        </div>
        <div className="row-actions">
          <button onClick={newLocation}><MapPin size={14} /> New Location</button>
          <button disabled={!pinConfirmed} onClick={saveLocation}><MapPin size={14} /> {editingLocationId ? 'Update Location' : 'Save Location'}</button>
          <button className="danger ghost" onClick={onDeleteAccount}>Delete Account</button>
          <button className="primary" disabled={!pinConfirmed && (Number(location.latitude) !== 0 || Number(location.longitude) !== 0)} onClick={saveProfile}><Check size={16} /> Save Profile</button>
        </div>
      </Panel>
      <Panel title="Reports & Dispute History">
        <SimpleList rows={data.reports} primary={(row) => row.reason || row.id} secondary={(row) => `Status: ${row.status || 'open'} | ${dateTime(row.created_at)}`} />
      </Panel>
    </Page>
  );
}

function BidSetupModal({ product, locations, rules = {}, onClose, onStart }) {
  const defaultLocation = locations.find((loc) => loc.is_default === true || loc.is_default === 1) || locations[0];
  const defaultMinutes = Math.round(Number(rules.expiry_hours ?? 24) * 60);
  const [form, setForm] = useState({ quantity: product.bidQuantity || 1, expiry_minutes: defaultMinutes, notes: '', location_id: defaultLocation ? String(defaultLocation.location_id || defaultLocation.id) : '', skip_flagged_dealers: true });
  const [localError, setLocalError] = useState('');
  const expiryOptions = [
    [1, '1 Minute (Testing)'],
    [30, '30 Minutes'],
    [60, '1 Hour'],
    [120, '2 Hours'],
    [180, '3 Hours'],
    [240, '4 Hours'],
    [720, '12 Hours'],
    [1440, '24 Hours'],
    [2880, '48 Hours'],
    [4320, '72 Hours'],
    ...(![1, 30, 60, 120, 180, 240, 720, 1440, 2880, 4320].includes(defaultMinutes) ? [[defaultMinutes, `${defaultMinutes} Minutes (Default)`]] : []),
  ].filter(([minutes]) => minutes >= Number(rules.min_time_hours ?? (1 / 60)) * 60 - 1e-9 && minutes <= Number(rules.max_time_hours ?? 72) * 60 + 1e-9).sort((a, b) => a[0] - b[0]);
  const update = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const submit = () => {
    const quantity = Number(form.quantity);
    if (!locations.length) {
      setLocalError('Add and save a map-pinned profile location before starting a bid.');
      return;
    }
    if (!form.location_id) {
      setLocalError('Select a saved location for this bid.');
      return;
    }
    if (!Number.isInteger(quantity) || quantity <= 0 || quantity > 100000) {
      setLocalError('Quantity must be a whole number from 1 to 100000.');
      return;
    }
    setLocalError('');
    onStart({
      product_id: product.id,
      quantity,
      location_id: form.location_id,
      skip_flagged_dealers: form.skip_flagged_dealers,
      expiry_minutes: Number(form.expiry_minutes || 1440),
      fields: {
        ...(form.notes.trim() ? { Notes: form.notes.trim() } : {}),
        Source: 'Buyer bid setup popup',
      },
    });
  };
  return (
    <Modal title={`Start bid for ${product.name}`} onClose={onClose}>
      <div className="details-grid">
        <KV label="Product" value={product.name} />
        <KV label="Brand" value={product.brand} />
        <KV label="Price Range" value={`${money(product.price_min)} - ${money(product.price_max)}`} />
      </div>
      <div className="form-grid">
        <label>Quantity<input type="number" min="1" value={form.quantity} onChange={(event) => update('quantity', event.target.value)} /></label>
        <label>Select Saved Location<select value={form.location_id} onChange={(event) => update('location_id', event.target.value)}><option value="">{locations.length ? 'Select saved location' : 'No saved locations'}</option>{locations.map((loc) => <option key={loc.id} value={loc.location_id || loc.id}>{loc.label || loc.city}</option>)}</select></label>
        <label>Bid Expiry Duration<select value={form.expiry_minutes} onChange={(event) => update('expiry_minutes', Number(event.target.value))}>{expiryOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="check"><input type="checkbox" checked={form.skip_flagged_dealers} onChange={(event) => update('skip_flagged_dealers', event.target.checked)} /> Skip flagged dealers</label>
        <label className="wide">Optional notes<textarea value={form.notes} onChange={(event) => update('notes', event.target.value)} /></label>
      </div>
      {localError ? <div className="notice">{localError}</div> : null}
      <button className="primary" onClick={submit}><Bolt size={16} /> Start Bid</button>
    </Modal>
  );
}

function DealerOfferModal({ request, bid, onClose, onSubmit }) {
  const [form, setForm] = useState({
    amount: bid?.amount || '',
    discount_amount: bid?.discount_amount || '',
    warranty_text: bid?.warranty_text || '',
    delivery_time: bid?.delivery_time || '',
    installation_included: bid?.installation_included || false,
    free_gifts: bid?.free_gifts || '',
    extra_services: bid?.extra_services || '',
    notes: bid?.notes || '',
  });
  const [localError, setLocalError] = useState('');
  const update = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const submit = () => {
    const amount = Number(form.amount);
    const discount = form.discount_amount === '' ? 0 : Number(form.discount_amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setLocalError('Bid amount must be a valid number greater than 0.');
      return;
    }
    if (!Number.isFinite(discount) || discount < 0) {
      setLocalError('Discount amount must be a valid number. Use 0 if there is no discount.');
      return;
    }
    setLocalError('');
    onSubmit({
      bid_request_id: request.id,
      amount,
      discount_amount: discount,
      warranty_text: form.warranty_text,
      delivery_time: String(form.delivery_time),
      installation_included: form.installation_included,
      free_gifts: form.free_gifts,
      extra_services: form.extra_services,
      notes: form.notes,
    });
  };
  return (
    <Modal title={bid ? 'Edit Bid Offer' : 'Submit Customized Bid'} onClose={onClose}>
      <p>Quote the final total for all {request.quantity || bid?.quantity || 1} requested units, including any discount. The discount field records savings already included in that total.</p>
      <div className="form-grid">
        <label>Final Total (Rs.)<input inputMode="decimal" value={form.amount} onChange={(event) => update('amount', event.target.value)} /></label>
        <label>Included Savings (Rs.)<input inputMode="decimal" value={form.discount_amount} onChange={(event) => update('discount_amount', event.target.value)} /></label>
        <label>Warranty Text<input value={form.warranty_text} onChange={(event) => update('warranty_text', event.target.value)} /></label>
        <label>Delivery Time<input value={form.delivery_time} onChange={(event) => update('delivery_time', event.target.value)} /></label>
        <label>Free Gifts<input value={form.free_gifts} onChange={(event) => update('free_gifts', event.target.value)} /></label>
        <label>Extra Services<input value={form.extra_services} onChange={(event) => update('extra_services', event.target.value)} /></label>
        <label className="check"><input type="checkbox" checked={form.installation_included} onChange={(event) => update('installation_included', event.target.checked)} /> Installation included</label>
        <label className="wide">Dealer Notes<textarea value={form.notes} onChange={(event) => update('notes', event.target.value)} /></label>
      </div>
      {localError ? <div className="notice">{localError}</div> : null}
      <button className="primary" onClick={submit}>Submit Bid</button>
    </Modal>
  );
}

function ReportModal({ bid, onClose, onSubmit }) {
  const [reason, setReason] = useState('Wrong product details');
  const [description, setDescription] = useState('');
  return (
    <Modal title="File Dispute / Report" onClose={onClose}>
      <label>Reason<select value={reason} onChange={(event) => setReason(event.target.value)}>{['Wrong product details', 'Payment issue', 'Dealer no response', 'Buyer no response', 'Quality concern', 'Other'].map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <button className="primary" onClick={() => onSubmit({ bid_id: bid.id, reason, description })}>Submit Report</button>
    </Modal>
  );
}

function DetailsModal({ details, user, run, refresh, onClose }) {
  const [message, setMessage] = useState('');
  const [recipient, setRecipient] = useState('both');
  const [note, setNote] = useState('');
  if (details._kind === 'dealer' || details._kind === 'buyer') {
    return <AdminAccountDetails details={details} role={details._kind} onClose={onClose} />;
  }
  if (details._kind === 'report') {
    const related = [];
    return (
      <Modal title={details.reason || `Report ${details.id}`} onClose={onClose} wide>
        <div className="report-header-card">
          <div>
            <strong>Report ID: {details.id} | Bid ID: {details.bid_id || 'N/A'} | Status: {text(details.status).toUpperCase()}</strong>
            {details.closure_requested_status && details.closure_requested_status !== 'none' ? <span>Closure request: {details.closure_requested_status} | Requested by: {details.closure_requested_by_name || 'Reporter'}</span> : null}
          </div>
          {user.role === 'admin' ? (
            <select onChange={(event) => event.target.value && run((token) => api.updateReportStatus(token, details.id, event.target.value, note), 'Report status updated.').then((ok) => ok && refresh())} defaultValue="">
              <option value="">Update Status</option>
              {['resolved', 'rejected', 'closed', 'escalated'].map((status) => <option key={status} value={status}>{status.toUpperCase()}</option>)}
            </select>
          ) : null}
        </div>
        {related.length > 1 ? <div className="notice">Note: Both Buyer and Dealer have reported this Bid.</div> : null}
        <div className="report-product-card">
          <strong>Product: {details.product || 'N/A'}</strong>
          <span>Brand: {details.product_brand || 'N/A'}</span>
          <span>Quantity: {details.quantity || 1} pcs</span>
          <span>Deal Amount: {money(details.bid_amount)}</span>
          <span>Warranty: {details.warranty || 'N/A'}</span>
          <span>Delivery: {details.delivery || 'N/A'} days</span>
          {details.description ? <p>Dispute Description: {details.description}</p> : null}
        </div>
        <Panel title={user.role === 'admin' ? 'Messages' : 'Report status'}>
          {user.role === 'admin' && <>
          <div className="message-list chat-thread">
            {details._messages.length ? details._messages.map((msg) => {
              const mine = ['admin', 'agent'].includes(msg.sender_role);
              return (
                <div className={`message bubble ${mine ? 'mine' : ''}`} key={msg.id}>
                  <div><strong>{msg.sender_name || msg.sender_role || 'System'}</strong><span>To: {text(msg.recipient_group || 'both').toUpperCase()}</span></div>
                  <p>{msg.message}</p>
                  <small>{msg.created_at}</small>
                </div>
              );
            }) : <Empty title="No messages in this chat yet." />}
          </div>
          <div className="inline-form">
            {user.role === 'admin' ? <select value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="both">Both</option><option value="buyer">Buyer Only</option><option value="dealer">Dealer Only</option></select> : <select value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="both">To Everyone (Public)</option><option value="admin">To Admin Only (Private)</option></select>}
            <input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Type your message/resolution details here..." />
            <button className="icon-button" onClick={() => run((token) => api.sendReportMessage(token, details.id, recipient, message), 'Message sent.').then((ok) => ok && refresh())}><Send size={18} /></button>
          </div>
          </>}
          {user.role === 'admin' ? (
            <div className="inline-form">
              <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Admin note" />
              {['resolved', 'rejected', 'closed', 'escalated'].map((status) => <button key={status} onClick={() => run((token) => api.updateReportStatus(token, details.id, status, note), 'Report status updated.').then((ok) => ok && refresh())}>{status}</button>)}
            </div>
          ) : (
            <button onClick={() => run((token) => api.requestReportClosure(token, details.id, 'User requested closure'), 'Closure requested.').then((ok) => ok && refresh())}>Cancel Report</button>
          )}
        </Panel>
      </Modal>
    );
  }
  return (
    <Modal title="Details" onClose={onClose} wide>
      <div className="details-grid">{Object.entries(details).map(([key, value]) => <KV key={key} label={key.replaceAll('_', ' ')} value={typeof value === 'object' ? JSON.stringify(value) : value} />)}</div>
    </Modal>
  );
}

function AdminAccountDetails({ details, role, onClose }) {
  const basic = details.basic || details;
  const isDealer = role === 'dealer';
  const locations = list(details.locations || details.addresses);
  const categories = list(details.categories);
  const bids = list(details.bids);
  const commissions = list(details.commissions);
  const reports = list(details.reports);
  const timeline = list(details.timeline);
  return (
    <Modal title={isDealer ? (basic.business_name || 'Dealer Profile') : (basic.full_name || 'Buyer Profile')} onClose={onClose} wide>
      <div className="detail-titlebar">
        <div>
          <strong>{isDealer ? (basic.business_name || 'Dealer Profile') : (basic.full_name || 'Buyer Profile')}</strong>
          <span>Account ID: {basic.id || details.id || ''}</span>
        </div>
      </div>
      <Panel title={isDealer ? 'Business & Owner Information' : 'Buyer Information'}>
        <div className="details-grid">
          <KV label={isDealer ? 'Owner Name' : 'Full Name'} value={basic.owner_name || basic.full_name || basic.name} />
          <KV label="Email Address" value={basic.email} />
          <KV label="Phone Number" value={basic.phone} />
          {isDealer ? <KV label="GST Number" value={basic.gst_number} /> : null}
          <KV label={isDealer ? 'Registered Address' : 'Address'} value={basic.business_address || basic.address} />
          {isDealer ? <KV label="Rating" value={basic.rating || '0.0'} /> : null}
          {isDealer ? <><KV label="Verification" value={basic.verification_status} /><KV label="Subscription" value={basic.subscribed ? 'Active' : 'Inactive'} /><KV label="Coverage method" value={basic.service_preferences?.method || 'radius'} /><KV label="Service cities" value={list(basic.service_preferences?.cities).join(', ')} /><KV label="Service states" value={list(basic.service_preferences?.states).join(', ')} /><KV label="Service districts" value={list(basic.service_preferences?.districts).join(', ')} /></> : null}
          <KV label="Account Status" value={basic.status} />
        </div>
      </Panel>
      <div className="grid-two">
        <Panel title={isDealer ? 'Service Areas' : 'Saved Locations'}>
          <AdminList rows={locations} empty={isDealer ? 'No service areas defined.' : 'No saved locations.'}>
            {(row) => <AdminListItem icon={<MapPin size={17} />} title={`${isDealer ? (row.area || row.label || '') : (row.label || row.area || '')}, ${row.city || ''}`} subtitle={`State: ${row.state || ''} | Pincode: ${row.pincode || ''} | Radius: ${row.radius_km ?? row.preferred_radius ?? basic.preferred_radius ?? 15} km | Pin: ${row.latitude ?? ''}, ${row.longitude ?? ''}`} />}
          </AdminList>
        </Panel>
        <Panel title={isDealer ? 'Categories Served' : 'Buyer Activity'}>
          {isDealer ? (
            <AdminList rows={categories} empty="No categories served.">
              {(row) => <AdminListItem icon={<Package size={17} />} title={row.name || row.category || 'Category'} subtitle={row.item || row.subcategory || ''} />}
            </AdminList>
          ) : (
            <div className="details-grid">
              <KV label="Bids" value={basic.bid_count || bids.length} />
              <KV label="Purchases" value={basic.purchase_count || 0} />
              <KV label="Reports" value={reports.length} />
            </div>
          )}
        </Panel>
      </div>
      <div className="grid-two">
        <Panel title="Bid History">
          <AdminList rows={bids} empty="No bid history.">
            {(row) => <AdminListItem icon={<Gavel size={17} />} title={row.product || row.product_name || row.id} subtitle={`${row.amount != null || row.winning_amount != null ? money(row.amount ?? row.winning_amount) : 'No winning offer'} | ${row.status || row.request_status || ''}`} trailing={<Status text={row.status || row.request_status} />} />}
          </AdminList>
        </Panel>
        <Panel title={isDealer ? 'Historical payments' : 'Reports'}>
          <AdminList rows={isDealer ? commissions : reports} empty={isDealer ? 'No commissions.' : 'No reports.'}>
            {(row) => <AdminListItem icon={isDealer ? <IndianRupee size={17} /> : <FileText size={17} />} title={row.product || row.reason || row.id} subtitle={isDealer ? `${money(row.amount || row.commission_amount)} | ${row.payment_status || row.status || ''}` : `${row.status || ''} | ${row.created_at || ''}`} />}
          </AdminList>
        </Panel>
      </div>
      {isDealer && <Panel title="Reports"><SimpleList rows={reports} primary={row=>row.reason} secondary={row=>`${row.status} | ${row.description || ''}`} /></Panel>}
      <Panel title="Timeline">
        <AdminList rows={timeline} empty="No timeline entries.">
          {(row) => <AdminListItem icon={<ReceiptText size={17} />} title={row.action || row.event_type || (row.new_status ? `${row.old_status} → ${row.new_status}` : 'Activity')} subtitle={`${row.reason || ''} ${row.changed_by || ''} | ${dateTime(row.created_at)}`} />}
        </AdminList>
      </Panel>
    </Modal>
  );
}

function ProductImage({product,className='product-art',iconSize=42}) {
  const [loaded,setLoaded]=useState(false);const [failed,setFailed]=useState(false);
  const rawImageUrl = String(product.image_url || '');
  const resolvedImageUrl = /^https?:\/\//i.test(rawImageUrl) ? rawImageUrl : `${apiBaseUrl}${rawImageUrl.startsWith('/') ? rawImageUrl : `/${rawImageUrl}`}`;
  const imageSource = !rawImageUrl || failed ? '/catalog-placeholder.svg' : resolvedImageUrl;
  return <div className={className}>
    {!loaded&&failed&&<Package size={iconSize} aria-hidden="true"/>}
    <img src={imageSource} alt={product.name} loading={className==='product-detail-art'?'eager':'lazy'} className="catalog-product-photo" style={{opacity:loaded?1:0}} onLoad={()=>setLoaded(true)} onError={()=>{if (imageSource !== '/catalog-placeholder.svg') setFailed(true);}} />
  </div>;
}

function ProductCard({ product, onCart, onBid, onSelect }) {
  return (
    <article className="product-card" onClick={onSelect}>
      <ProductImage key={product.image_url||'none'} product={product}/>
      <span>{product.brand}</span>
      <h3 title={product.name}>{product.name}</h3>
      <p title={productSpecs(product)}>{productSpecs(product) || 'Standard Edition'}</p>
      <strong>{product.release_year ? `${product.release_date_basis === 'legacy_reported_year' ? 'Reported year' : 'Release year'}: ${product.release_year}` : 'Release year unknown'} · Bid for price</strong>
      <div className="product-actions">
        <button className="success" onClick={(event) => { event.stopPropagation(); onCart(); }}><ShoppingCart size={15} /> Add</button>
        <button onClick={(event) => { event.stopPropagation(); onBid(); }}><Bolt size={15} /> Bid</button>
      </div>
    </article>
  );
}

function SubscriptionBanner({ onSubscribe, onDismiss }) {
  return (
    <div className="subscription-banner">
      <Bolt size={20} />
      <div><strong>Subscription Required</strong><span>Subscribe to receive bid requests in your service area - Rs. 999/month</span></div>
      <button onClick={onSubscribe}>Subscribe Now</button>
      <button className="icon-button" onClick={onDismiss} title="Dismiss subscription banner"><X size={18} /></button>
    </div>
  );
}

function Page({ children }) {
  return <div className="page">{children}</div>;
}

function Section({ title, subtitle, icon: Icon }) {
  return (
    <div className="section-header">
      <div><Icon size={24} /></div>
      <section><h2>{title}</h2><p>{subtitle}</p></section>
    </div>
  );
}

function Panel({ title, children }) {
  return <section className="panel"><h3>{title}</h3>{children}</section>;
}

function Metric({ label, value }) {
  return <div className="metric"><Layers size={20} /><strong>{value}</strong><span>{label}</span></div>;
}

function Status({ text = 'active' }) {
  return <span className={`status ${String(text).toLowerCase()}`}>{text || 'active'}</span>;
}

function Empty({ title }) {
  return <div className="empty">{title}</div>;
}

function SimpleList({ rows = [], primary, secondary, action }) {
  if (!rows?.length) return <Empty title="No records found" />;
  return <div className="simple-list">{rows.slice(0, 8).map((row, index) => <div key={row.id || index}><div><strong>{primary(row)}</strong><span>{secondary?.(row)}</span></div>{action?.(row) || <ChevronRight size={16} />}</div>)}</div>;
}

function ResponsiveTable({ rows = [], columns }) {
  if (!rows?.length) return <Empty title="No records found" />;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map(([label]) => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={row.id || index}>{columns.map(([label, render]) => <td key={label} data-label={label}>{render(row)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function Modal({ title, children, onClose, wide }) {
  return (
    <div className="modal-layer" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className={`modal ${wide ? 'wide' : ''}`} onMouseDown={(event) => event.stopPropagation()}>
        <header><h2>{title}</h2><button className="icon-button" aria-label="Close" title="Close" onClick={onClose}><X size={18} /></button></header>
        <div className="modal-body">{children}</div>
      </section>
    </div>
  );
}

function KV({ label, value }) {
  return <div className="kv"><span>{label}</span><strong>{String(value ?? '')}</strong></div>;
}

export default App;
