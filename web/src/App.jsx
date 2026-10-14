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
  LifeBuoy,
  LogOut,
  Mail,
  MapPin,
  Menu,
  MoreHorizontal,
  Package,
  Pencil,
  Phone,
  Plus,
  ReceiptText,
  RefreshCw,
  Search,
  Send,
  Settings,
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
import {
  Countdown,
  DialogErrorContext,
  Empty,
  KV,
  Metric,
  Modal,
  Page,
  Panel,
  ProductImage,
  Section,
  SlipSkeletons,
  Status,
  dateTime,
  money,
  plural,
  toTime,
  useConfirm,
} from './ui.jsx';
import {
  BidSetupModal,
  BidSheet,
  BrandMark,
  BuyerRequestSlip,
  CompareOffersModal,
  MyBidSlip,
  RequestSlip,
  Standing,
  formatDelivery,
  isLive,
  standingFor,
} from './bidding.jsx';

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
  ['Browse products', Search],
  ['My requests', Bolt],
  ['Orders', ClipboardList],
  ['Cart', ShoppingCart],
  ['Alerts', Bell],
  ['Account', User],
  ['Help & reports', LifeBuoy],
];

const dealerNav = [
  ['Home', Home],
  ['Open requests', Inbox],
  ['My bids', Gavel],
  ['Past bids', ClipboardList],
  ['My shop', Store],
  ['Alerts', Bell],
  ['Help & reports', LifeBuoy],
];

function list(value) {
  return Array.isArray(value) ? value : [];
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
      value: key.includes('revenue') || key.includes('amount') || key.includes('commission') ? money(value) : String(value),
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
  const [live, setLive] = useState('connecting');
  const confirm = useConfirm();
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
          if (bucket === 'categories') next.categories = activeUser.role === 'admin' ? await api.adminCategories(token) : await api.categories(token);
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
      if (failures.length) throw failures.find((err) => err.status === 401) || failures[0];
      return true;
    } catch (err) {
      if (sessionTokenRef.current !== activeUser.access_token) return false;
      if (err.status === 401) {
        sessionStorage.removeItem(sessionKey);
        setUser(null);
        setError('Your session has ended. Sign in again to continue.');
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
        ['dealerRequests', 'bids', 'profile', 'settings'],
        ['bids', 'dealerRequests', 'profile', 'settings'],
        ['bids'],
        ['profile', 'categories', 'settings'],
        ['notifications'],
        ['reports'],
      ][activeTab] || [];
    }
    return [
      ['buyerLocations', 'notifications', 'settings'],
      ['bids', 'buyerRequests', 'buyerLocations', 'settings'],
      ['bids', 'buyerRequests'],
      ['cart', 'buyerLocations', 'settings'],
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
        setLive('live');
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
        setLive('reconnecting');
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
    } catch (err) {
      if (err.status === 429) setError('Too many sign-in attempts. Wait a few minutes, then try again.');
      else if (err.status === 401) setError('That username or password is not right. Check both and try again.');
      else if (err.status === 403) setError('This account is blocked. Contact support to get access back.');
      else if (err.status) setError(friendlyErrorMessage(err));
      else setError('Could not reach the server. Check your connection and try again.');
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
      if (err.status === 401) {
        logout();
        setError('Your session has ended. Sign in again to continue.');
        return false;
      }
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
        confirm,
        onExport: handleExport,
        onDeleteAccount: () => run((token) => api.deleteOwnAccount(token)).then((ok) => ok && logout()),
      })
    : registering
      ? <RegisterPage loading={loading} error={error} onRegister={handleRegister} onCancel={() => { setError(''); setRegistering(false); }} />
      : <LoginPage loading={loading} error={error} onLogin={handleLogin} onRegister={() => { setError(''); setRegistering(true); }} />;

  if (!user) return page;

  const alertsIndex = user.role === 'buyer' ? 4 : user.role === 'dealer' ? 5 : -1;
  const roleLabel = user.role === 'dealer' ? 'Shop account' : user.role === 'buyer' ? 'Buyer account' : 'Administrator';
  const liveLabel = live === 'live' ? 'Live' : live === 'reconnecting' ? 'Reconnecting' : 'Connecting';

  return (
    <DialogErrorContext.Provider value={{ error, clearError: () => setError('') }}>
      <div className="app-shell">
        <aside className={`side-nav ${drawerOpen ? 'open' : ''}`} aria-label="Sidebar">
          <div className="brand-block">
            <BrandMark />
            <div>
              <strong>Turacoz</strong>
              <span>Bid Tool</span>
            </div>
            <button type="button" className="icon-button mobile-only" aria-label="Close menu" onClick={() => setDrawerOpen(false)}><X size={18} aria-hidden="true" /></button>
          </div>
          <nav aria-label="Primary">
            {nav.map(([label, Icon], index) => (
              <button
                type="button"
                key={label}
                aria-current={tab === index ? 'page' : undefined}
                className={`nav-item ${tab === index ? 'active' : ''}`}
                onClick={() => {
                  setTab(index);
                  setDrawerOpen(false);
                }}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
                {index === alertsIndex && unread > 0 ? <b aria-label={`${unread} unread`}>{unread}</b> : null}
              </button>
            ))}
          </nav>
          <div className="rail-foot">
            <div className="rail-user">
              <strong>{user.name}</strong>
              <span>{roleLabel}</span>
            </div>
            <button type="button" className="small" onClick={logout}><LogOut size={15} aria-hidden="true" /> Sign out</button>
          </div>
        </aside>
        <div className="main-area">
          <header className="top-bar">
            <button type="button" className="icon-button mobile-only" onClick={() => setDrawerOpen(true)} aria-label="Menu" title="Menu"><Menu size={20} aria-hidden="true" /></button>
            <span className="top-brand"><BrandMark />Bid Tool</span>
            <div className="top-actions">
              <span className={`live-pill ${live}`} aria-live="polite" title={live === 'live' ? 'New requests and offers appear here instantly.' : 'Trying to restore live updates.'}>{liveLabel}</span>
              {alertsIndex >= 0 ? (
                <button type="button" className="icon-button badge-wrap" onClick={() => setTab(alertsIndex)} aria-label={unread ? `Alerts, ${unread} unread` : 'Alerts'} title="Alerts">
                  <Bell size={19} aria-hidden="true" />
                  {unread > 0 ? <span className="badge" aria-hidden="true">{unread}</span> : null}
                </button>
              ) : null}
              <button type="button" className="icon-button" onClick={() => loadPageData(user, tab)} aria-label="Refresh" title="Refresh"><RefreshCw size={19} aria-hidden="true" /></button>
              <button type="button" className="icon-button mobile-only" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut size={19} aria-hidden="true" /></button>
            </div>
          </header>
          {error ? <div className={`notice page-notice ${error.includes('successful') ? 'success' : ''}`} role="alert">{error}</div> : null}
          {toast ? <div className="toast-pop" role="status">{toast}</div> : null}
          {loading ? <div className="loading-strip" aria-hidden="true" /> : null}
          {user.role === 'dealer' && data.profile && !data.dealerSubscribed && !dismissSubscriptionBanner ? (
            <SubscriptionBanner
              onSubscribe={async () => {
                const ok = await confirm({
                  title: 'Activate your subscription?',
                  body: <p>Your shop will receive matching buyer requests right away. The plan costs ₹999 a month.</p>,
                  confirmLabel: 'Activate subscription',
                  cancelLabel: 'Not now',
                });
                if (ok) run((token) => api.activateDealerSubscription(token), 'Subscription activated. Requests will start arriving.');
              }}
              onDismiss={() => setDismissSubscriptionBanner(true)}
            />
          ) : null}
          <main>{page}</main>
        </div>
        <nav className="bottom-nav" aria-label="Quick navigation">
          {nav.slice(0, 4).map(([label, Icon], index) => (
            <button type="button" key={label} className={tab === index ? 'active' : ''} aria-current={tab === index ? 'page' : undefined} onClick={() => setTab(index)}>
              <Icon size={20} aria-hidden="true" />
              <span>{label.length > 14 ? label.replace(' products', '') : label}</span>
            </button>
          ))}
          <button type="button" className={tab > 3 ? 'active' : ''} onClick={() => setDrawerOpen(true)}>
            <span className="badge-wrap"><MoreHorizontal size={20} aria-hidden="true" />{unread > 0 && alertsIndex >= 0 ? <span className="badge" aria-hidden="true">{unread}</span> : null}</span>
            <span>More</span>
          </button>
        </nav>
        {drawerOpen ? <button type="button" className="scrim" aria-label="Close menu" onClick={() => setDrawerOpen(false)} /> : null}
        {bidProduct ? (
          <BidSetupModal
            product={bidProduct}
            locations={data.buyerLocations}
            rules={data.settings?.bid_rules}
            onClose={() => setBidProduct(null)}
            onAddLocation={() => { setBidProduct(null); setTab(5); }}
            onStart={(payload) => run((token) => api.startBid(token, payload), 'Bid started. Nearby shops can now send offers.').then((ok) => { if (ok) { setBidProduct(null); setTab(1); } })}
          />
        ) : null}
        {dealerOffer ? (
          <BidSheet
            request={dealerOffer.request}
            bid={dealerOffer.bid}
            allBids={data.bids}
            subscribed={data.dealerSubscribed}
            rules={data.settings?.bid_rules}
            onClose={() => setDealerOffer(null)}
            onSubmit={(payload) => run((token) => api.submitDealerBid(token, payload), dealerOffer.bid ? 'Bid updated.' : 'Bid submitted.').then((ok) => ok && setDealerOffer(null))}
          />
        ) : null}
        {reportBid ? (
          <ReportModal
            bid={reportBid}
            onClose={() => setReportBid(null)}
            onSubmit={(payload) => run((token) => api.createReport(token, payload), 'Report sent. Our team will review it.').then((ok) => ok && setReportBid(null))}
          />
        ) : null}
        {details ? <DetailsModal details={details} user={user} refresh={() => loadPageData(user, tab)} run={run} confirm={confirm} onClose={() => setDetails(null)} /> : null}
      </div>
    </DialogErrorContext.Provider>
  );
}

function renderPage(ctx) {
  const { user, tab } = ctx;
  if (user.role === 'admin') {
    return [
      <DashboardPage title="Admin Dashboard" subtitle="Platform health, bids, and alerts at a glance." {...ctx} />,
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
      <DealerHomePage {...ctx} />,
      <DealerRequestsPage {...ctx} />,
      <DealerBidsPage {...ctx} />,
      <DealerHistoryPage {...ctx} />,
      <BusinessProfilePage {...ctx} />,
      <NotificationsPage {...ctx} />,
      <ReportsPage {...ctx} />,
    ][tab] || null;
  }
  return [
    <BuyerHomePage {...ctx} />,
    <BuyerRequestsPage {...ctx} />,
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
        <BrandMark />
        <h1>Sign in</h1>
        <p>Welcome back. Pick up where you left off.</p>
        {error ? <div className={`notice ${error.includes('successful') ? 'success' : ''}`} role="alert">{error}</div> : null}
        <label>Username<input aria-label="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus /></label>
        <label>Password<input aria-label="Password" value={password} type="password" onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
        <button type="submit" className="primary sign-in" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
        <p className="auth-switch">New here? <button className="link-button" type="button" onClick={onRegister}>Create an account</button></p>
      </form>
    </AuthLayout>
  );
}

function RegisterPage({ loading, error, onRegister, onCancel }) {
  const [form, setForm] = useState({ name: '', username: '', password: '', role: 'buyer' });
  const [localError, setLocalError] = useState('');
  const update = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const submit = (event) => {
    event.preventDefault();
    if (form.password.length < 8) {
      setLocalError('Use a password with at least 8 characters.');
      return;
    }
    setLocalError('');
    onRegister(form);
  };
  const shown = localError || error;
  return (
    <AuthLayout>
      <form className="auth-card" onSubmit={submit}>
        <BrandMark />
        <h1>Create your account</h1>
        <p>Buyers ask for prices. Shops send bids. Pick the one that fits you.</p>
        {shown ? <div className="notice" role="alert">{shown}</div> : null}
        <fieldset className="role-choice">
          <legend>I want to</legend>
          <label className="role-option"><input type="radio" name="role" value="buyer" checked={form.role === 'buyer'} onChange={() => update('role', 'buyer')} /><strong>Buy products</strong><span>Compare offers from nearby shops</span></label>
          <label className="role-option"><input type="radio" name="role" value="dealer" checked={form.role === 'dealer'} onChange={() => update('role', 'dealer')} /><strong>Sell as a shop</strong><span>Bid on requests near you</span></label>
        </fieldset>
        <label>Full name<input value={form.name} onChange={(event) => update('name', event.target.value)} autoComplete="name" required /></label>
        <label>Username or email<input value={form.username} onChange={(event) => update('username', event.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required /></label>
        <label>Password<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} autoComplete="new-password" minLength={8} required /><span className="hint">At least 8 characters.</span></label>
        <button type="submit" className="primary sign-in" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
        <p className="auth-switch">Already have an account? <button className="link-button" type="button" onClick={onCancel}>Sign in</button></p>
      </form>
    </AuthLayout>
  );
}

function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <BrandArt />
      <main className="auth-main">{children}</main>
    </div>
  );
}

function shopSetupSteps(profile, subscribed) {
  const p = profile || {};
  const hasCoverage = p.delivery_method === 'radius'
    ? Number(p.service_radius_km) > 0 && Boolean(p.latitude) && Boolean(p.longitude)
    : [p.service_states, p.service_cities, p.service_districts].some((rows) => list(rows).length > 0);
  return [
    { key: 'subscription', done: Boolean(subscribed), title: 'Activate your subscription', hint: 'Needed to receive buyer requests and place bids.', action: 'subscribe' },
    { key: 'business', done: Boolean(text(p.business_name) && text(p.address)), title: 'Add your shop details', hint: 'Shop name and address are shown to a buyer after they choose you.', action: 'shop' },
    { key: 'area', done: hasCoverage, title: 'Set the area you serve', hint: 'Pin your shop on the map and choose how far you deliver.', action: 'shop' },
    { key: 'products', done: list(p.category_ids).length > 0, title: 'Choose the products you sell', hint: 'You only receive requests for the categories you pick.', action: 'shop' },
  ];
}

function DealerHomePage({ user, data, loading, setTab, setDealerOffer, run, confirm }) {
  const profile = data.profile;
  const subscribed = data.dealerSubscribed;
  const steps = shopSetupSteps(profile, subscribed);
  const pending = steps.filter((step) => !step.done);
  const metrics = data.dashboard?.metrics || {};
  const requests = [...list(data.dealerRequests)].sort((a, b) => toTime(a.expires_at) - toTime(b.expires_at));
  const myLive = list(data.bids).filter((bid) => bid.is_mine && isLive(bid));
  const leading = myLive.filter((bid) => standingFor(bid, data.bids).kind !== 'trail').length;
  const won = Number(metrics.won_bids || 0);
  const lost = Number(metrics.lost_bids || 0);
  const decided = won + lost;
  const subscribe = async () => {
    const ok = await confirm({
      title: 'Activate your subscription?',
      body: <p>Your shop will receive matching buyer requests right away. The plan costs ₹999 a month.</p>,
      confirmLabel: 'Activate subscription',
      cancelLabel: 'Not now',
    });
    if (ok) run((token) => api.activateDealerSubscription(token), 'Subscription activated. Requests will start arriving.');
  };
  return (
    <Page>
      <Section title="Today at your shop" subtitle="New buyer requests, your live bids and how you are doing." />

      {profile && pending.length ? (
        <Panel title={`Finish setting up your shop (${steps.length - pending.length} of ${steps.length} done)`}>
          <ol className="checklist">
            {steps.map((step) => (
              <li key={step.key} className={step.done ? 'done' : ''}>
                <span className="check-mark" aria-hidden="true">{step.done ? <Check size={14} /> : null}</span>
                <div>
                  <strong>{step.title}</strong>
                  <span>{step.hint}</span>
                </div>
                {step.done ? <span className="muted-small">Done</span> : (
                  <button type="button" className="small primary" onClick={() => (step.action === 'subscribe' ? subscribe() : setTab(4))}>{step.action === 'subscribe' ? 'Subscribe' : 'Set up'}</button>
                )}
              </li>
            ))}
          </ol>
        </Panel>
      ) : null}

      <dl className="stat-row">
        <Metric label="Open requests" value={requests.length} />
        <Metric label="Live bids" value={myLive.length} hint={myLive.length ? `Lowest on ${leading} of ${myLive.length}` : undefined} />
        <Metric label="Bids won" value={won} tone={won ? 'good' : ''} />
        <Metric label="Win rate" value={decided ? `${Math.round((won / decided) * 100)}%` : '—'} hint={decided ? `${won} won, ${lost} lost` : 'After your first result'} />
        <Metric label="Total won" value={money(metrics.revenue)} />
      </dl>

      <section aria-labelledby="closing-soon">
        <div className="panel-head">
          <h2 id="closing-soon" className="block-title">Closing soonest</h2>
          {requests.length > 3 ? <button type="button" className="link-button" onClick={() => setTab(1)}>See all {requests.length} requests</button> : null}
        </div>
        {loading && !requests.length ? <SlipSkeletons count={1} /> : requests.length ? (
          <div className="slip-grid">
            {requests.slice(0, 3).map((request) => (
              <RequestSlip key={request.id} request={request} blocked={subscribed ? '' : 'Activate your subscription to bid.'} onBid={(row) => setDealerOffer({ request: row })} />
            ))}
          </div>
        ) : (
          <Empty
            title="No open requests right now"
            hint={subscribed ? 'New requests show up here the moment a nearby buyer posts one. Keep this page open, or check the alerts.' : 'Activate your subscription to start receiving requests from buyers near you.'}
            action={subscribed ? <button type="button" onClick={() => setTab(4)}>Review what my shop sells</button> : <button type="button" className="primary" onClick={subscribe}>Activate subscription</button>}
          />
        )}
      </section>

      {myLive.length ? (
        <Panel title="Your live bids" actions={<button type="button" className="small" onClick={() => setTab(2)}>Manage bids</button>}>
          <AdminList rows={myLive}>
            {(bid) => (
              <AdminListItem
                title={`${bid.product}, ${money(bid.amount)}`}
                subtitle={<Standing standing={standingFor(bid, data.bids)} />}
                trailing={<Countdown until={bid.ends_at} />}
                onClick={() => setTab(2)}
              />
            )}
          </AdminList>
        </Panel>
      ) : null}
    </Page>
  );
}

function DealerRequestsPage({ data, loading, setDealerOffer, setTab, run, confirm }) {
  const [sort, setSort] = useState('soonest');
  const subscribed = data.dealerSubscribed;
  const rows = [...list(data.dealerRequests)].sort((a, b) => {
    if (sort === 'offers') return Number(b.offers_count || 0) - Number(a.offers_count || 0);
    if (sort === 'nearest') return (a.distance_km ?? 1e9) - (b.distance_km ?? 1e9);
    return toTime(a.expires_at) - toTime(b.expires_at);
  });
  const subscribe = async () => {
    const ok = await confirm({
      title: 'Activate your subscription?',
      body: <p>Your shop will receive matching buyer requests right away. The plan costs ₹999 a month.</p>,
      confirmLabel: 'Activate subscription',
      cancelLabel: 'Not now',
    });
    if (ok) run((token) => api.activateDealerSubscription(token), 'Subscription activated. Requests will start arriving.');
  };
  return (
    <Page>
      <Section
        title="Open requests"
        subtitle="Buyers near you who want a price. Send your best final price before the timer ends."
        actions={rows.length > 1 ? (
          <label className="inline-field">
            <span>Sort by</span>
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="soonest">Closing soonest</option>
              <option value="offers">Most bids</option>
              <option value="nearest">Nearest</option>
            </select>
          </label>
        ) : null}
      />
      {data.profile && !subscribed ? (
        <div className="page-banner warn">
          <div>
            <strong>Your subscription is not active.</strong>
            <p>Activate it to receive requests and place bids. Bidding stays locked until then.</p>
          </div>
          <button type="button" className="primary" onClick={subscribe}>Activate subscription</button>
        </div>
      ) : null}
      {loading && !rows.length ? <SlipSkeletons /> : rows.length ? (
        <div className="slip-grid">
          {rows.map((request) => (
            <RequestSlip key={request.id} request={request} blocked={subscribed ? '' : 'Activate your subscription to bid.'} onBid={(row) => setDealerOffer({ request: row })} />
          ))}
        </div>
      ) : (
        <Empty
          title="No open requests right now"
          hint="You are shown requests for products you sell, from buyers inside your service area. If nothing arrives for a while, check that your shop lists the right products and area."
          action={<button type="button" onClick={() => setTab(4)}>Check my shop settings</button>}
        />
      )}
    </Page>
  );
}

function DealerBidsPage({ user, data, loading, setDealerOffer, setReportBid, setTab, run, confirm }) {
  const [details, setDetails] = useState(null);
  const mine = list(data.bids).filter((bid) => bid.is_mine);
  const live = mine.filter(isLive).sort((a, b) => toTime(a.ends_at) - toTime(b.ends_at));
  const won = mine.filter((bid) => bid.status === 'won');
  const withdraw = async (bid) => {
    const ok = await confirm({
      title: 'Withdraw this bid?',
      body: (
        <>
          <p>The buyer will no longer see your {money(bid.amount)} offer for {bid.product}. You can bid again while the request is still open.</p>
          <p className="muted-small">Withdrawing more than 3 times can flag your shop and hide you from new requests.</p>
        </>
      ),
      confirmLabel: 'Withdraw bid',
      cancelLabel: 'Keep my bid',
      tone: 'danger',
    });
    if (ok) run((token) => api.withdrawBid(token, bid.id), 'Bid withdrawn.');
  };
  const trailing = live.filter((bid) => standingFor(bid, data.bids).kind === 'trail').length;
  return (
    <Page>
      <Section
        title="My bids"
        subtitle={live.length ? `${plural(live.length, 'live bid')}${trailing ? `, ${trailing} not the lowest` : ', all at the lowest price or unopposed'}. Revise any time before the timer ends.` : 'Bids you have placed that are still open.'}
      />
      {loading && !mine.length ? <SlipSkeletons count={1} /> : live.length ? (
        <div className="slip-grid">
          {live.map((bid) => (
            <MyBidSlip
              key={bid.id}
              bid={bid}
              standing={standingFor(bid, data.bids)}
              onRevise={(row) => setDealerOffer({ request: { id: row.bid_request_id, product: row.product, quantity: row.quantity, expires_at: row.ends_at, buyer_area: [row.buyer_area, row.buyer_city].filter(Boolean).join(', ') }, bid: row })}
              onWithdraw={withdraw}
              onDetails={(row) => setDetails({ bid: row, mine: true })}
            />
          ))}
        </div>
      ) : (
        <Empty
          title="You have no live bids"
          hint="Open requests are waiting for a price. Your bids appear here with a live view of where you stand."
          action={<button type="button" className="primary" onClick={() => setTab(1)}>See open requests</button>}
        />
      )}
      {won.length ? (
        <Panel title="Won, buyer details unlocked">
          <AdminList rows={won}>
            {(bid) => (
              <AdminListItem
                title={`${bid.product}, ${money(bid.amount)}`}
                subtitle={`${bid.buyer || 'Buyer'}${bid.buyer_phone ? `, ${bid.buyer_phone}` : ''}`}
                onClick={() => setDetails({ bid, mine: true })}
                trailing={<button type="button" onClick={(event) => { event.stopPropagation(); setDetails({ bid, mine: true }); }}>Buyer details</button>}
              />
            )}
          </AdminList>
        </Panel>
      ) : null}
      {details ? <DealerBidDetailModal user={user} data={data} onReport={setReportBid} bid={data.bids.find((bid) => bid.id === details.bid.id) || details.bid} mine={details.mine} onClose={() => setDetails(null)} /> : null}
    </Page>
  );
}

function BuyerRequestsPage({ user, data, loading, setReportBid, setTab, run, confirm }) {
  const [openId, setOpenId] = useState(null);
  const requests = list(data.buyerRequests);
  const active = requests.filter((request) => request.status === 'active');
  const awarded = requests.filter((request) => request.status === 'awarded');
  const offersFor = (requestId) => list(data.bids).filter((bid) => bid.bid_request_id === requestId && bid.status !== 'withdrawn');
  const opened = openId ? requests.find((request) => request.id === openId) : null;

  const cancelRequest = async (request) => {
    const ok = await confirm({
      title: 'Cancel this request?',
      body: <p>Shops will stop seeing your request for {request.product}{offersFor(request.id).length ? ', and the offers you have received will be closed' : ''}. This cannot be undone.</p>,
      confirmLabel: 'Cancel request',
      cancelLabel: 'Keep request',
      tone: 'danger',
    });
    if (ok) run((token) => api.cancelBuyerRequest(token, request.id), 'Request cancelled.');
  };

  const acceptOffer = async (offer) => {
    const units = Number(opened?.quantity || offer.quantity || 1);
    const ok = await confirm({
      title: `Accept ${money(offer.amount)} from ${offer.dealer || 'this shop'}?`,
      body: (
        <>
          <ul className="confirm-list">
            <li>{plural(units, 'unit')} of {opened?.product || offer.product}</li>
            <li>Delivery: {formatDelivery(offer.delivery_time)}</li>
            <li>Warranty: {text(offer.warranty_text) || 'None'}</li>
            <li>Installation: {Number(offer.installation_included) ? 'Included' : 'Not included'}</li>
          </ul>
          <p>Bidding closes straight away and the other offers are declined. The shop gets your contact details, and you get theirs. You cannot undo this.</p>
        </>
      ),
      confirmLabel: 'Accept offer',
      cancelLabel: 'Keep comparing',
    });
    if (ok) await run((token) => api.acceptBid(token, offer.id, offer.terms_token), 'Offer accepted. The shop contact details are now unlocked.');
  };

  const winnerContact = (request) => {
    const winner = offersFor(request.id).find((bid) => bid.status === 'won');
    if (!winner) return null;
    return (
      <div className="contact-block">
        <strong>You accepted {winner.dealer}. Contact them to arrange delivery.</strong>
        {winner.owner_name ? <span><User size={14} aria-hidden="true" /> {winner.owner_name}</span> : null}
        {winner.dealer_phone ? <span><PhoneIcon /> {winner.dealer_phone}</span> : null}
        {winner.dealer_email ? <span><MailIcon /> {winner.dealer_email}</span> : null}
        {winner.business_address ? <span><MapPin size={14} aria-hidden="true" /> {winner.business_address}</span> : null}
        <div className="row-actions"><button type="button" className="small danger" onClick={() => setReportBid(winner)}>Report a problem with this shop</button></div>
      </div>
    );
  };

  return (
    <Page>
      <Section
        title="My requests"
        subtitle={active.length ? `${plural(active.length, 'request')} open. Offers appear here the moment shops send them.` : 'Products you have asked shops to price.'}
        actions={<button type="button" className="primary" onClick={() => setTab(0)}><Plus size={16} aria-hidden="true" /> New request</button>}
      />
      {loading && !requests.length ? <SlipSkeletons count={1} /> : active.length ? (
        <div className="slip-grid">
          {active.map((request) => (
            <BuyerRequestSlip key={request.id} request={request} offers={offersFor(request.id)} onCompare={(row) => setOpenId(row.id)} onCancel={cancelRequest} />
          ))}
        </div>
      ) : (
        <Empty
          title="You have no open requests"
          hint="Pick a product and start a bid. Nearby shops will send their best price within your deadline."
          action={<button type="button" className="primary" onClick={() => setTab(0)}>Browse products</button>}
        />
      )}
      {awarded.length ? (
        <Panel title="Accepted offers">
          <AdminList rows={awarded}>
            {(request) => {
              const winner = offersFor(request.id).find((bid) => bid.status === 'won');
              return (
                <AdminListItem
                  title={`${request.product}${winner ? `, ${money(winner.amount)}` : ''}`}
                  subtitle={winner ? `From ${winner.dealer}` : `${plural(Number(request.quantity || 1), 'unit')}`}
                  onClick={() => setOpenId(request.id)}
                  trailing={<button type="button" className="small" onClick={(event) => { event.stopPropagation(); setOpenId(request.id); }}>Shop contact details</button>}
                />
              );
            }}
          </AdminList>
        </Panel>
      ) : null}
      {opened ? (
        <CompareOffersModal
          request={opened}
          offers={offersFor(opened.id)}
          winnerContact={winnerContact(opened)}
          onClose={() => setOpenId(null)}
          onAccept={acceptOffer}
          onCancel={opened.status === 'active' ? () => cancelRequest(opened) : undefined}
        />
      ) : null}
    </Page>
  );
}

function BrandArt() {
  return (
    <aside className="auth-art" aria-hidden="true">
      <BrandMark className="brand-mark art-mark" />
      <h2>Ask once. Shops compete.</h2>
      <p>Buyers post what they want. Nearby shops send their best final price before the timer ends. The buyer picks the winner.</p>
      <div className="slip">
        <div className="slip-top plain">
          <div className="slip-title">
            <small>Example request</small>
            <h3>55-inch 4K television</h3>
          </div>
          <span className="countdown soon"><span className="countdown-dot" />2h 14m left</span>
        </div>
        <ul className="slip-meta">
          <li>1 unit</li>
          <li>Andheri West, Mumbai</li>
        </ul>
        <hr className="slip-tear" />
        <div className="slip-foot">
          <div className="slip-price">
            <small>Lowest of 4 offers</small>
            <span className="price"><span className="price-hl">₹38,990</span></span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function DashboardPage({ title, subtitle, data, extra }) {
  const metrics = metricEntries(data.dashboard);
  const charts = data.dashboard?.charts || {};
  const hasCharts = Object.values(charts).some((value) => Array.isArray(value) && value.length);
  return (
    <Page>
      <Section title={title} subtitle={subtitle} icon={Home} />
      {metrics.length ? <dl className="stat-row">{metrics.map((item) => <Metric key={item.key} label={item.label} value={item.value} />)}</dl> : <Empty title="No dashboard metrics yet" />}
      {hasCharts ? (
        <section className="analytics-stack">
          <h2>Platform Analytics Dashboard</h2>
          {list(charts.revenue_by_month).length ? <BarPanel title="Revenue by month" rows={charts.revenue_by_month} /> : null}
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

function BuyerHomePage({ data, setBidProduct, setTab, run, user }) {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [filters, setFilters] = useState(emptyCatalogFilters);
  const [facets, setFacets] = useState({});
  const [total, setTotal] = useState(0);
  const [searchMode, setSearchMode] = useState('exact');
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [selected, setSelected] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [howItWorks, setHowItWorks] = useState(() => {
    try { return localStorage.getItem('bidtool_how_it_works_seen') !== '1'; } catch { return true; }
  });
  const requestVersion = useRef(0);
  const detailVersion = useRef(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const activeFilters = ['categories', 'product_types', 'brands', 'years'].reduce((sum, key) => sum + list(filters[key]).length, 0);
  const search = () => setAppliedQuery(query.trim());

  useEffect(() => {
    const next = query.trim();
    if (next === appliedQuery) return undefined;
    const timer = setTimeout(() => setAppliedQuery(next), 250);
    return () => clearTimeout(timer);
  }, [query, appliedQuery]);

  useEffect(() => {
    const version = ++requestVersion.current;
    setCatalogLoading(true);
    setCatalogError('');
    api.catalogSearch(user.access_token, catalogParams(filters, { q: appliedQuery, limit: 50, offset: 0 }))
      .then((result) => {
        if (version !== requestVersion.current) return;
        setProducts(result.items);
        setFacets(result.facets);
        setTotal(result.total);
        setSearchMode(result.search_mode || 'exact');
      })
      .catch((error) => { if (version === requestVersion.current) setCatalogError(friendlyErrorMessage(error)); })
      .finally(() => { if (version === requestVersion.current) setCatalogLoading(false); });
    return () => { requestVersion.current++; };
  }, [user.access_token, appliedQuery, filters, refreshKey]);

  const loadMore = async () => {
    const version = requestVersion.current;
    setCatalogLoading(true);
    try {
      const result = await api.catalogSearch(user.access_token, catalogParams(filters, { q: appliedQuery, limit: 50, offset: products.length, include_facets: false }));
      if (version === requestVersion.current) setProducts((old) => [...old, ...result.items.filter((row) => !old.some((item) => item.id === row.id))]);
    } catch (error) {
      setCatalogError(friendlyErrorMessage(error));
    } finally {
      if (version === requestVersion.current) setCatalogLoading(false);
    }
  };

  const openProduct = async (product) => {
    const version = ++detailVersion.current;
    setSelected(product);
    try {
      const full = await api.productDetail(user.access_token, product.id);
      if (version === detailVersion.current) setSelected(full);
    } catch {
      // The summary from the list is enough to show.
    }
  };
  const closeProduct = () => { detailVersion.current++; setSelected(null); };
  const dismissHowItWorks = () => {
    setHowItWorks(false);
    try { localStorage.setItem('bidtool_how_it_works_seen', '1'); } catch { /* private mode */ }
  };
  const addToCart = (product) => run((token) => api.addCartItem(token, product.id, 1), 'Added to your cart.');

  return (
    <Page>
      <Section title="Browse products" subtitle="Choose what you want to buy. Nearby shops compete to give you their best price." />
      {!data.buyerLocations.length ? (
        <div className="page-banner warn">
          <div>
            <strong>Add a delivery location to start a bid.</strong>
            <p>Shops are matched by distance, so we need a pin on the map first.</p>
          </div>
          <button type="button" className="primary" onClick={() => setTab(5)}>Add location</button>
        </div>
      ) : howItWorks ? (
        <div className="page-banner">
          <div>
            <strong>How it works</strong>
            <p>Start a bid on any product. Nearby shops send their best final price before your deadline. Compare delivery and warranty, then accept the offer you like.</p>
          </div>
          <button type="button" onClick={dismissHowItWorks}>Got it</button>
        </div>
      ) : null}
      <div className="toolbar buyer-search">
        <div className="search-box wide-search">
          <Search size={17} aria-hidden="true" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') search(); }} placeholder="Search by product, brand, model or feature" aria-label="Search products" />
        </div>
        <button type="button" className="primary" disabled={catalogLoading} onClick={search}>Search</button>
        <button type="button" className="filter-toggle" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((open) => !open)}>Filters{activeFilters ? ` (${activeFilters})` : ''}</button>
      </div>
      <div className="buyer-catalog-layout">
        <aside className={`filter-panel ${filtersOpen ? 'open' : ''}`} aria-label="Product filters">
          <div>
            <strong>Filters</strong>
            <button type="button" className="link-button" onClick={() => setFilters(emptyCatalogFilters())}>Reset</button>
          </div>
          <CatalogFilters facets={facets} filters={filters} onChange={setFilters} />
        </aside>
        <section className="catalog-results" aria-busy={catalogLoading}>
          <div className="catalog-summary">
            <strong>{total.toLocaleString('en-IN')} {total === 1 ? 'product' : 'products'}</strong>
            <label>
              <span>Sort by</span>
              <select value={filters.sort} onChange={(event) => setFilters({ ...filters, sort: event.target.value })}>
                {['Newest', 'Year', 'A-Z', 'Lowest Price', 'Highest Price'].map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
          </div>
          {searchMode === 'related' && <p className="muted search-note">Nothing matched exactly, so these are the closest products and categories.</p>}
          {catalogError ? (
            <div className="notice" role="alert">
              <p>{catalogError}</p>
              <button type="button" disabled={catalogLoading} onClick={() => setRefreshKey((value) => value + 1)}>Retry loading products</button>
            </div>
          ) : null}
          {catalogLoading && !products.length ? <p role="status" className="muted">Loading products…</p> : null}
          <div className="product-grid buyer-grid">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} onSelect={() => openProduct(product)} onCart={() => addToCart(product)} onBid={() => setBidProduct(product)} />
            ))}
          </div>
          {!catalogLoading && !catalogError && !products.length ? <Empty title="No products match" hint="Try fewer filters or a shorter search." action={<button type="button" onClick={() => { setFilters(emptyCatalogFilters()); setQuery(''); }}>Clear search and filters</button>} /> : null}
          {products.length < total ? <button type="button" disabled={catalogLoading} onClick={loadMore}>{catalogLoading ? 'Loading…' : 'Show more products'}</button> : null}
        </section>
      </div>
      {selected ? <ProductDetailsModal product={selected} onClose={closeProduct} onCart={() => addToCart(selected)} onBid={() => { const product = selected; closeProduct(); setBidProduct(product); }} /> : null}
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
  const labels = [['won', 'Accepted'], ['expired', 'Expired'], ['cancelled', 'Cancelled'], ['all', 'Everything']];
  const rebid = (bid) => run(async (token) => {
    const product = data.products.find((item) => item.id === bid.product_id) || await api.productDetail(token, bid.product_id);
    setBidProduct({ ...product, bidQuantity: bid.quantity || 1 });
  });
  const closedRequests = data.buyerRequests.filter((request) => request.status !== 'active' && (tab === 'all' || request.status === (tab === 'won' ? 'awarded' : tab)));
  return (
    <Page>
      <Section title="Orders" subtitle="Offers you accepted, and requests that ended without one." />
      <div className="tab-row" role="group" aria-label="Filter orders">
        {labels.map(([key, label]) => <button type="button" key={key} className={tab === key ? 'active' : ''} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}
      </div>
      <HistoryList user={user} data={data} bids={groups[tab]} onReport={setReportBid} onRebid={rebid} />
      <Panel title="Requests">
        <AdminList rows={closedRequests} empty="No requests in this view">
          {(request) => (
            <AdminListItem
              title={request.product}
              subtitle={plural(Number(request.quantity || 1), 'unit')}
              trailing={<Status text={request.status} />}
            />
          )}
        </AdminList>
      </Panel>
    </Page>
  );
}

function CartPage({ data, setBidProduct, setTab, run }) {
  const items = list(data.cart?.items);
  const startBid = (item) => run(async (token) => {
    const product = await api.productDetail(token, item.product_id);
    setBidProduct({ ...product, bidQuantity: item.quantity || 1 });
  });
  return (
    <Page>
      <Section
        title="Cart"
        subtitle="Products you saved to bid on later."
        actions={<button type="button" onClick={() => setTab(0)}>Keep browsing</button>}
      />
      <Panel>
        <AdminList rows={items} empty="Your cart is empty" hint="Save products here while you decide which to start bids on.">
          {(item) => (
            <AdminListItem
              icon={<ShoppingCart size={18} aria-hidden="true" />}
              title={item.name || item.product || item.product_name}
              subtitle={`${item.brand || ''} ${item.model || ''}`.trim() || undefined}
              trailing={(
                <div className="admin-item-actions">
                  <span className="qty-chip">{plural(Number(item.quantity || 1), 'unit')}</span>
                  <button type="button" className="small" aria-label={`Add one more ${item.name || 'unit'}`} onClick={() => run((token) => api.addCartItem(token, item.product_id, 1), 'Quantity increased.')}><Plus size={14} aria-hidden="true" /></button>
                  <button type="button" className="small" onClick={() => run((token) => api.removeCartItem(token, item.id), 'Removed from your cart.')}>Remove</button>
                  <button type="button" className="small primary" onClick={() => startBid(item)}>Start bid</button>
                </div>
              )}
            />
          )}
        </AdminList>
      </Panel>
    </Page>
  );
}

/** "A, B, C, D, E" becomes "A, B, C and 2 more" so long lists stay readable. */
function summarizeList(value, shown = 3) {
  const items = String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
  if (!items.length) return 'nothing selected yet';
  return items.length <= shown ? items.join(', ') : `${items.slice(0, shown).join(', ')} and ${items.length - shown} more`;
}

function AdminUsersPage({ title, role, rows, run, setDetails, confirm }) {
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
  const changeStatus = async (row, name, select) => {
    const status = select.value;
    const consequences = {
      deleted: 'Their access is removed and they are signed out. Their bids, orders and reports stay on record.',
      banned: 'They are signed out at once and cannot use the marketplace. Open requests and bids are closed.',
      suspended: 'They are signed out and cannot bid or post requests until you restore them.',
      held: 'They cannot bid or post requests until you release the hold.',
    };
    if (consequences[status]) {
      const ok = await confirm({
        title: `${titleCase(status)} ${name}?`,
        body: <p>{consequences[status]}</p>,
        confirmLabel: titleCase(status),
        cancelLabel: 'Cancel',
        tone: 'danger',
      });
      if (!ok) {
        select.value = row.status || 'active';
        return;
      }
    }
    run((token) => api.setUserStatus(token, row.id, status), 'Status updated.');
  };
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
        <Panel title="Filters">
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
              ? `${row.email || ''}, ${[row.city, row.state].filter(Boolean).join(', ')}. Sells: ${summarizeList(row.categories || row.category)}`
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
                    <select value={row.status || 'active'} title="Change status" aria-label={`Status for ${name}`} onChange={(event) => changeStatus(row, name, event.target)}>
                      {['pending', 'verified', 'active', 'held', 'suspended', 'flagged', 'banned', 'deleted'].map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}
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

function ProductAdminPage({ user, data, run, confirm, onExport }) {
  const empty = { name: '', category: '', subcategory: '', brand: '', model: '', price_min: '', price_max: '', location: '', status: 'active', specifications: 'Warranty: 1 year' };
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
              <button className="danger ghost" onClick={async () => { if (await confirm({ title: `Delete ${product.name}?`, body: <p>Buyers will no longer find it. Past requests and bids that used it stay on record.</p>, confirmLabel: 'Delete product', cancelLabel: 'Keep it', tone: 'danger' })) run((token) => api.deleteProduct(token, product.id), 'Product deleted.'); }}><Trash2 size={14} /> Delete</button>
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
          onSave={async () => {
            setSaving(true); setEditorError('');
            try {
              const ok=await run(async token=>{try{return await (modal==='add'?api.createProduct(token,draft()):api.updateProduct(token,modal,draft()));}catch(error){setEditorError(friendlyErrorMessage(error));throw error;}},modal==='add'?'Product added successfully!':'Product updated.');
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

function ReportsPage({ user, data, run, confirm, onExport }) {
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
  const requestClosure = async () => {
    if (!selected) return;
    const reason = await confirm({
      title: 'Close this report?',
      body: <p>Tell us why you want to close it. Our team can still see the history.</p>,
      input: { label: 'Reason', placeholder: 'For example: the shop fixed the problem', required: true, minLength: 3 },
      confirmLabel: 'Close report',
      cancelLabel: 'Keep it open',
    });
    if (!reason) return;
    run(async (token) => {
      await api.requestReportClosure(token, selected.id, reason);
      await loadReport(token, selected.id);
    }, 'Closure requested.');
  };
  const decideClosure = async (status) => {
    if (!selected) return;
    const note = await confirm({
      title: status === 'approved' ? 'Approve closing this report?' : 'Reject closing this report?',
      input: { label: 'Note (optional)', placeholder: 'Add context for the people involved' },
      confirmLabel: status === 'approved' ? 'Approve closure' : 'Reject closure',
      cancelLabel: 'Cancel',
    });
    if (note === false) return;
    run(async (token) => {
      await api.closureDecision(token, selected.id, status, note);
      await loadReport(token, selected.id);
    }, `Closure ${status}.`);
  };
  return (
    <Page>
      <Section title={user.role === 'admin' ? 'Reports & Dispute Center' : 'Help & reports'} subtitle={user.role === 'admin' ? 'Moderate dispute logs, selective broadcast message threads, and resolve client complaints.' : 'View your reports and their review status.'} icon={FileText} />
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

function SettingsPage({ data, run, confirm }) {
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
        <CategoryManager categories={data.categories} run={run} confirm={confirm} />
      </Panel>
    </Page>
  );
}

function AdminList({ rows = [], empty, hint, children }) {
  if (!rows.length) return <Empty title={empty || 'Nothing here yet.'} hint={hint} />;
  return <div className="admin-list">{rows.map((row, index) => <React.Fragment key={row.id || index}>{children(row, index)}</React.Fragment>)}</div>;
}

function AdminListItem({ icon, title, subtitle, trailing, onClick }) {
  const activate = (event) => {
    // Only react to keys pressed on the row itself, not on buttons or selects inside it.
    if (event.target !== event.currentTarget) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onClick(event);
    }
  };
  return (
    <div
      className={`admin-list-item ${onClick ? 'clickable' : ''}`}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? activate : undefined}
    >
      {icon ? <div className="avatar-icon">{icon}</div> : <span />}
      <div className="admin-list-main">
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
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
  const topCategories = categories.filter((item) => !item.parent_id);
  const selectedParent = topCategories.find((item) => item.name === form.category);
  const childCategories = selectedParent
    ? list(selectedParent.items)
    : topCategories.flatMap((item) => list(item.items)).concat(categories.filter((item) => item.parent_id));
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={event=>{event.preventDefault();onSave();}}>
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

function CategoryManager({ categories, run, confirm }) {
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
                <button className="danger ghost" onClick={async () => { if (await confirm({ title: `Delete ${parent.name}?`, body: <p>Its {plural(childrenFor(parent).length, 'subcategory', 'subcategories')} will be deleted too. Categories used by products or dealers cannot be deleted.</p>, confirmLabel: 'Delete category', cancelLabel: 'Keep it', tone: 'danger' })) run((token) => api.deleteCategory(token, parent.id), 'Category deleted.'); }}><Trash2 size={14} /> Delete</button>
              </div>
            </header>
            <div className="category-child-list">
              {childrenFor(parent).length ? childrenFor(parent).map((child) => (
                <div className="category-child-row" key={child.id}>
                  <span><ChevronRight size={14} /> {child.name}</span>
                  <div className="row-actions">
                    <button className="icon-button" title="Edit subcategory" onClick={() => editChild(child, parent)}><Pencil size={14} /></button>
                    <button className="icon-button danger" title="Delete subcategory" onClick={async () => { if (await confirm({ title: `Delete ${child.name}?`, confirmLabel: 'Delete', cancelLabel: 'Keep it', tone: 'danger' })) run((token) => api.deleteCategory(token, child.id), 'Category deleted.'); }}><X size={14} /></button>
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
              <button type="button" className="primary" onClick={() => onRebid(bid)}>Bid again</button>
            </div>
          </article>
        ))}
      </div>
      {details ? <BidDetailsModal user={user} liveMessages={data.liveBidMessages[details.id] || []} bid={data.bids.find((bid) => bid.id === details.id) || details} payments={[]} onClose={() => setDetails(null)} onReport={() => onReport(details)} /> : null}
    </>
  );
}

function PhoneIcon() {
  return <Phone size={14} aria-hidden="true" />;
}

function MailIcon() {
  return <Mail size={14} aria-hidden="true" />;
}

function DealerBidDetailModal({ user, data, onReport, bid, mine, onClose }) {
  const status = String(bid.status || '').toLowerCase();
  const won = ['won', 'completed'].includes(status);
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

function DealerHistoryPage({ user, data, setReportBid, onExport }) {
  const [tab, setTab] = useState('won');
  const [details, setDetails] = useState(null);
  const ownBids = list(data.bids).filter((bid) => bid.is_mine);
  const groups = {
    won: ownBids.filter((bid) => bid.status === 'won'),
    lost: ownBids.filter((bid) => bid.status === 'lost'),
    closed: ownBids.filter((bid) => !isLive(bid) && !['won', 'lost'].includes(bid.status)),
  };
  const labels = [['won', 'Won'], ['lost', 'Lost'], ['closed', 'Expired or withdrawn']];
  return (
    <Page>
      <Section
        title="Past bids"
        subtitle="Every bid that has finished, and how it ended."
        actions={<button type="button" onClick={() => onExport('bids')}><Download size={16} aria-hidden="true" /> Export as CSV</button>}
      />
      <div className="tab-row" role="group" aria-label="Filter past bids">
        {labels.map(([key, label]) => (
          <button type="button" key={key} className={tab === key ? 'active' : ''} aria-pressed={tab === key} onClick={() => setTab(key)}>{label} ({groups[key].length})</button>
        ))}
      </div>
      <Panel>
        <AdminList rows={groups[tab]} empty={tab === 'won' ? 'No wins yet' : 'Nothing here'} hint={tab === 'won' ? 'When a buyer picks your bid it shows up here with their contact details.' : undefined}>
          {(bid) => (
            <AdminListItem
              title={`${bid.product}, ${money(bid.amount)}`}
              subtitle={`${plural(Number(bid.quantity || 1), 'unit')}${bid.buyer ? `, ${bid.buyer}` : ''}`}
              onClick={() => setDetails(bid)}
              trailing={(
                <div className="admin-item-actions">
                  <Status text={bid.status} />
                  <button type="button" className="small" onClick={(event) => { event.stopPropagation(); setDetails(bid); }}><Eye size={14} aria-hidden="true" /> Details</button>
                  {bid.status === 'won' ? <button type="button" className="small danger" onClick={(event) => { event.stopPropagation(); setReportBid(bid); }}><Flag size={14} aria-hidden="true" /> Report</button> : null}
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

function BusinessProfilePage({ user, data, run, confirm, onDeleteAccount }) {
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
  if (!data.profile || !form.delivery_method) return <Page><Section title="My shop" /><Panel><p role="status">Loading your saved business profile…</p></Panel></Page>;
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
      <Section title="My shop" subtitle="What you sell, where you deliver and how buyers see you. Buyers only see your shop name until they accept your bid." />
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
        <button type="button" className="danger" onClick={async () => {
          const ok = await confirm({
            title: 'Delete your shop account?',
            body: (
              <>
                <p>You will be signed out, your live bids are withdrawn and you stop receiving requests.</p>
                <p>Bids you already won stay on record so any dispute can still be resolved.</p>
              </>
            ),
            confirmLabel: 'Delete my account',
            cancelLabel: 'Keep my account',
            tone: 'danger',
          });
          if (ok) onDeleteAccount();
        }}>Delete account</button>
        {!data.dealerSubscribed ? <button type="button" onClick={async () => {
          const ok = await confirm({
            title: 'Activate your subscription?',
            body: <p>Your shop will receive matching buyer requests right away. The plan costs ₹999 a month.</p>,
            confirmLabel: 'Activate subscription',
            cancelLabel: 'Not now',
          });
          if (ok) run((token) => api.activateDealerSubscription(token), 'Subscription activated. Requests will start arriving.');
        }}>Subscribe</button> : null}
      </div>
    </Page>
  );
}

function NotificationsPage({ data, run }) {
  const rows = list(data.notifications);
  const unread = rows.filter((item) => !item.is_read && !item.isRead).length;
  return (
    <Page>
      <Section
        title="Alerts"
        subtitle="New requests, offers and account updates from the last 7 days."
        actions={<button type="button" disabled={!unread} onClick={() => run((token) => api.markNotificationsRead(token), 'All alerts marked as read.')}>Mark all as read</button>}
      />
      {rows.length ? (
        <div className="list-stack">
          {rows.map((item) => {
            const isUnread = !item.is_read && !item.isRead;
            return (
              <button type="button" className={`notification ${isUnread ? 'unread' : ''}`} key={item.id} onClick={() => isUnread && run((token) => api.markNotificationRead(token, item.id))}>
                <strong>{isUnread ? <span className="sr-only">Unread: </span> : null}{item.title}</strong>
                <p>{item.message || item.body}</p>
                <span>{dateTime(item.created_at)}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <Empty title="You are all caught up" hint="New requests, offers and account updates will show up here." />
      )}
    </Page>
  );
}

function ProfilePage({ user, data, run, confirm, onDeleteAccount }) {
  const [profile, setProfile] = useState({});
  const [dirty, setDirty] = useState(false);
  const [pinConfirmed, setPinConfirmed] = useState(false);
  const emptyLocation = { label: '', address: '', country: 'India', state: '', city: '', area: '', pincode: '', latitude: 0, longitude: 0, is_default: false };
  const [location, setLocation] = useState(emptyLocation);
  const [editingLocationId, setEditingLocationId] = useState('');
  const [locationError, setLocationError] = useState('');
  const [detailsError, setDetailsError] = useState('');
  const initialLocationLoaded = useRef(false);
  const locations = list(data.buyerLocations);
  const toForm = (row) => ({
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

  // Refreshes must not wipe what the person is typing, so only sync a clean form.
  useEffect(() => {
    if (dirty) return;
    const next = data.profile || user || {};
    setProfile({
      ...next,
      preferred_radius: next.preferred_radius || next.matching_radius_km || next.radius_km || 15,
      latitude: next.latitude || 0,
      longitude: next.longitude || 0,
    });
  }, [data.profile, user, dirty]);

  useEffect(() => {
    const first = locations[0];
    if (first && !initialLocationLoaded.current) {
      initialLocationLoaded.current = true;
      setLocation(toForm(first));
      setEditingLocationId(first.id || '');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.buyerLocations]);

  const update = (key, value) => { setDirty(true); setProfile((old) => ({ ...old, [key]: value })); };
  const updateLocation = (key, value) => { setLocationError(''); setLocation((old) => ({ ...old, [key]: value })); };
  const loadLocation = (row) => { setLocationError(''); setEditingLocationId(row.id || ''); setLocation(toForm(row)); };
  const newLocation = () => {
    initialLocationLoaded.current = true;
    setLocationError('');
    setEditingLocationId('');
    setLocation({ ...emptyLocation, is_default: !locations.length });
  };

  // Details only change the person's own fields. Address and pin stay as stored, so editing
  // another saved location here can never silently move the default address.
  const saveProfile = async () => {
    const radius = Number(profile.preferred_radius);
    if (!Number.isFinite(radius) || radius <= 0 || radius > 5000) {
      setDetailsError('Enter a matching radius between 1 and 5000 km.');
      return;
    }
    setDetailsError('');
    const stored = data.profile || {};
    const ok = await run((token) => api.updateProfile(token, {
      full_name: profile.full_name || profile.name || user.name,
      phone: profile.phone || '',
      address: stored.address || '',
      country: stored.country || 'India',
      state: stored.state || '',
      city: stored.city || '',
      area: stored.area || '',
      pincode: stored.pincode || '',
      preferred_radius: radius,
      latitude: Number(stored.latitude || 0),
      longitude: Number(stored.longitude || 0),
    }), 'Details saved.');
    if (ok) setDirty(false);
  };

  const saveLocation = () => {
    if (!pinConfirmed) return Promise.resolve();
    if (Number(location.latitude || 0) === 0 && Number(location.longitude || 0) === 0) {
      setLocationError('Drop a pin on the map first.');
      return Promise.resolve();
    }
    if (!location.state?.trim() || !location.city?.trim()) {
      setLocationError('Confirm the pin on the map so the city and state fill in.');
      return Promise.resolve();
    }
    if (!location.address?.trim() && !location.area?.trim()) {
      setLocationError('Add a street address or an area for this location.');
      return Promise.resolve();
    }
    setLocationError('');
    return run((token) => api.saveBuyerLocation(token, {
      ...location,
      label: location.label || location.address || 'Saved location',
      country: location.country || 'India',
      latitude: Number(location.latitude || 0),
      longitude: Number(location.longitude || 0),
      is_default: Boolean(location.is_default || !locations.length),
    }, editingLocationId || undefined), editingLocationId ? 'Location updated.' : 'Location saved.').then((ok) => ok && newLocation());
  };

  const removeLocation = async (row) => {
    const ok = await confirm({
      title: `Delete "${row.label || 'this location'}"?`,
      body: <p>Open requests that already use it are not affected. You can add it again later.</p>,
      confirmLabel: 'Delete location',
      cancelLabel: 'Keep it',
      tone: 'danger',
    });
    if (ok) run((token) => api.deleteBuyerLocation(token, row.id), 'Location deleted.');
  };

  const removeAccount = async () => {
    const ok = await confirm({
      title: 'Delete your account?',
      body: (
        <>
          <p>You will be signed out and lose access straight away. Your open requests are closed.</p>
          <p>Orders you already accepted stay on record so the shops and our team can still resolve any dispute.</p>
        </>
      ),
      confirmLabel: 'Delete my account',
      cancelLabel: 'Keep my account',
      tone: 'danger',
    });
    if (ok) onDeleteAccount();
  };

  return (
    <Page>
      <Section title="Account" subtitle="Your details and the places you want things delivered." />
      <Panel title="Your details" actions={<span className="muted-small">{user.email}</span>}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="acct-name">Full name</label>
            <input id="acct-name" value={profile.full_name || profile.name || ''} autoComplete="name" onChange={(event) => update('full_name', event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="acct-phone">Phone</label>
            <input id="acct-phone" type="tel" value={profile.phone || ''} autoComplete="tel" onChange={(event) => update('phone', event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="acct-radius">Search for shops within (km)</label>
            <input id="acct-radius" type="number" min="1" max="5000" inputMode="numeric" value={profile.preferred_radius || ''} aria-invalid={Boolean(detailsError)} onChange={(event) => update('preferred_radius', event.target.value)} />
            <p className="hint">Only shops inside this distance can bid on your requests.</p>
            {detailsError ? <p className="field-error" role="alert">{detailsError}</p> : null}
          </div>
        </div>
        <div className="row-actions">
          <button type="button" className="primary" disabled={!dirty} onClick={saveProfile}><Check size={16} aria-hidden="true" /> Save details</button>
        </div>
      </Panel>

      <Panel title={`Delivery locations (${locations.length} of 3)`} actions={<button type="button" className="small" onClick={newLocation}><Plus size={14} aria-hidden="true" /> Add location</button>}>
        {locations.length ? (
          <AdminList rows={locations}>
            {(row) => (
              <AdminListItem
                icon={<MapPin size={18} aria-hidden="true" />}
                title={row.label || 'Saved location'}
                subtitle={[row.area, row.city, row.state].filter(Boolean).join(', ')}
                trailing={(
                  <div className="admin-item-actions">
                    {row.is_default ? <Status text="default" /> : null}
                    <button type="button" className="small" onClick={() => loadLocation(row)}><Pencil size={14} aria-hidden="true" /> Edit</button>
                    <button type="button" className="small" disabled={row.is_default === true || row.is_default === 1} onClick={() => run((token) => api.setDefaultBuyerLocation(token, row.id), 'Default location updated.')}>Make default</button>
                    <button type="button" className="small danger" onClick={() => removeLocation(row)}>Delete</button>
                  </div>
                )}
              />
            )}
          </AdminList>
        ) : (
          <Empty title="No delivery location yet" hint="Add one below. You need it to start a bid, because nearby shops are matched by distance." />
        )}
      </Panel>

      <Panel title={editingLocationId ? 'Edit location' : 'Add a location'}>
        <p className="muted-small">Search for the address or tap the map, then confirm the pin. The fields below fill in automatically and you can adjust them.</p>
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
        <div className="form-grid">
          <label>Location name<input value={location.label} onChange={(event) => updateLocation('label', event.target.value)} placeholder="Home, Office, Clinic..." /></label>
          <label>Pincode<input value={location.pincode} inputMode="numeric" onChange={(event) => updateLocation('pincode', event.target.value)} /></label>
          <label className="wide">Street address<input value={location.address} onChange={(event) => updateLocation('address', event.target.value)} /></label>
          <label>Area or neighbourhood<input value={location.area} onChange={(event) => updateLocation('area', event.target.value)} /></label>
          <label>City<input value={location.city} onChange={(event) => updateLocation('city', event.target.value)} /></label>
          <label>State<input value={location.state} onChange={(event) => updateLocation('state', event.target.value)} /></label>
          <label>Country<input value={location.country} onChange={(event) => updateLocation('country', event.target.value)} /></label>
          <label className="check"><input type="checkbox" checked={Boolean(location.is_default)} onChange={(event) => updateLocation('is_default', event.target.checked)} /> Use as my default location</label>
        </div>
        {locationError ? <div className="notice" role="alert">{locationError}</div> : null}
        <div className="row-actions">
          <button type="button" className="primary" disabled={!pinConfirmed} onClick={saveLocation}><MapPin size={14} aria-hidden="true" /> {editingLocationId ? 'Update location' : 'Save location'}</button>
          {!pinConfirmed ? <span className="muted-small">Confirm the pin on the map to save.</span> : null}
        </div>
      </Panel>

      <Panel title="Your reports">
        <SimpleList rows={data.reports} primary={(row) => row.reason || 'Report'} secondary={(row) => `${titleCase(row.status || 'open')}, ${dateTime(row.created_at)}`} />
      </Panel>

      <Panel title="Delete account" className="danger-zone">
        <p className="muted-small">This signs you out and closes your open requests. It cannot be undone.</p>
        <div className="row-actions"><button type="button" className="danger" onClick={removeAccount}><Trash2 size={14} aria-hidden="true" /> Delete my account</button></div>
      </Panel>
    </Page>
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

function ProductCard({ product, onCart, onBid, onSelect }) {
  const specs = productSpecs(product);
  return (
    <article className="product-card" onClick={onSelect}>
      <ProductImage product={product} />
      {product.brand ? <span className="product-brand">{product.brand}</span> : null}
      <h3 title={product.name}><button type="button" onClick={(event) => { event.stopPropagation(); onSelect(); }}>{product.name}</button></h3>
      <p title={specs}>{specs || 'Standard edition'}</p>
      {product.release_year ? <span className="product-year">{product.release_date_basis === 'legacy_reported_year' ? 'Reported ' : 'Released '}{product.release_year}</span> : null}
      <div className="product-actions">
        <button type="button" className="primary" onClick={(event) => { event.stopPropagation(); onBid(); }}>Start bid</button>
        <button type="button" className="icon-outline" aria-label={`Add ${product.name} to cart`} title="Add to cart" onClick={(event) => { event.stopPropagation(); onCart(); }}><ShoppingCart size={17} aria-hidden="true" /></button>
      </div>
    </article>
  );
}

function SubscriptionBanner({ onSubscribe, onDismiss }) {
  return (
    <div className="subscription-banner" role="region" aria-label="Subscription">
      <Bolt size={20} aria-hidden="true" />
      <div>
        <strong>Subscribe to start receiving requests</strong>
        <span>Buyers near you are asking for prices. Plan: ₹999 a month.</span>
      </div>
      <button type="button" onClick={onSubscribe}>Subscribe now</button>
      <button type="button" className="icon-button" onClick={onDismiss} aria-label="Dismiss" title="Dismiss"><X size={18} aria-hidden="true" /></button>
    </div>
  );
}

function SimpleList({ rows = [], primary, secondary, action }) {
  if (!rows?.length) return <Empty title="No records found" />;
  return <div className="simple-list">{rows.slice(0, 8).map((row, index) => <div key={row.id || index}><div><strong>{primary(row)}</strong><span>{secondary?.(row)}</span></div>{action?.(row) || <ChevronRight size={16} />}</div>)}</div>;
}

export default App;
