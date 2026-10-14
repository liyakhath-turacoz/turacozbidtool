const defaultApiUrl=globalThis.location?.port==='8000' ? globalThis.location.origin : 'http://localhost:8000';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || defaultApiUrl).replace(/\/+$/, '');

function queryString(filters) {
  const query=new URLSearchParams();
  Object.entries(filters).forEach(([key,value])=>{
    if(value===undefined||value===null||value==='')return;
    if(Array.isArray(value))value.forEach(item=>query.append(key,item));else query.set(key,value);
  });
  return query;
}

const jsonHeaders = (token) => ({
  Accept: 'application/json',
  'Content-Type': 'application/json',
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

async function request(path, { token = '', method = 'GET', body, raw = false } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: jsonHeaders(token),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.headers.get('content-type')?.toLowerCase().includes('text/html')) {
    throw new Error('The server returned a webpage instead of API data. Restart the backend to load the latest routes and check the API address. Then retry.');
  }
  if (!response.ok) {
    const text = await response.text();
    const error = new Error(`API error ${response.status}: ${text}`);
    error.status = response.status;
    throw error;
  }
  if (raw) return response;
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text); }
  catch { throw new Error('The server returned invalid API data. Check the API address and restart the backend, then retry.'); }
}

export const apiBaseUrl = API_BASE_URL;

export const api = {
  bidMessages: (token, id) => request(`/bids/${id}/messages`, { token }),
  sendBidMessage: (token, id, message) => request(`/bids/${id}/messages`, { token, method: 'POST', body: { message } }),
  searchLocations: (token, query) => request(`/locations/search?q=${encodeURIComponent(query)}`, { token }),
  reverseLocation: (token, latitude, longitude) => request(`/locations/reverse?latitude=${latitude}&longitude=${longitude}`, { token }),
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: { username, password } }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  dashboard: (user) => {
    const path = user.role === 'admin'
      ? '/admin/dashboard'
      : user.role === 'dealer'
        ? '/dealer/dashboard'
        : '/buyer/dashboard';
    return request(path, { token: user.access_token });
  },
  profile: (token) => request('/profile', { token }),
  updateProfile: (token, payload) => request('/profile', { token, method: 'PUT', body: payload }),
  deleteOwnAccount: (token) => request('/profile', { token, method: 'DELETE' }),
  products: (token, query = '', limit = 250, offset = 0, category = '', brand = '') =>
    request(`/products?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}&category=${encodeURIComponent(category)}&brand=${encodeURIComponent(brand)}`, { token }),
  adminProducts: (token, filters) => request(`/admin/products?${queryString(filters)}`, {token}),
  catalogSearch: (token, filters) => request(`/catalog/search?${queryString(filters)}`, {token}),
  productSources: token => request('/admin/product-sources',{token}),
  createProductSource: (token,payload)=>request('/admin/product-sources',{token,method:'POST',body:payload}),
  saveProductSource: (token,id,payload) => request(`/admin/product-sources/${id}`,{token,method:'PUT',body:payload}),
  fetchProductSource: (token,id) => request(`/admin/product-sources/${id}/fetch`,{token,method:'POST'}),
  productStatistics: token => request('/admin/product-statistics',{token}),
  productStatisticsCsv: async token => (await request('/admin/product-statistics.csv',{token,raw:true})).blob(),
  productDetail: (token, id) => request(`/products/${id}`, { token }),
  createProduct: (token, payload) => request('/products', { token, method: 'POST', body: payload }),
  updateProduct: (token, id, payload) => request(`/products/${id}`, { token, method: 'PUT', body: payload }),
  deleteProduct: (token, id) => request(`/products/${id}`, { token, method: 'DELETE' }),
  bids: (token) => request('/bids', { token }),
  notifications: (token) => request('/notifications', { token }),
  markNotificationsRead: (token) => request('/notifications/mark-read', { token, method: 'POST' }),
  markNotificationRead: (token, id) => request(`/notifications/${id}/mark-read`, { token, method: 'POST' }),
  dealers: (token, query = '') => request(`/admin/dealers/search?q=${encodeURIComponent(query)}`, { token }),
  buyers: (token, query = '') => request(`/admin/buyers?q=${encodeURIComponent(query)}`, { token }),
  dealerDetails: (token, id) => request(`/admin/dealers/${id}/details`, { token }),
  buyerDetails: (token, id) => request(`/admin/buyers/${id}/details`, { token }),
  setUserStatus: (token, id, status) => request(`/admin/users/${id}/status`, { token, method: 'POST', body: { status } }),
  payments: (token) => request('/admin/payments', { token }),
  logs: (token) => request('/admin/logs', { token }),
  setPaymentStatus: (token, id, status) => request(`/admin/payments/${id}/status`, { token, method: 'POST', body: { status } }),
  settings: (token) => request('/settings', { token }),
  saveSetting: (token, key, value) => request(`/settings/${key}`, { token, method: 'POST', body: { value } }),
  categories: (token) => request('/categories', { token }),
  adminCategories: (token) => request('/admin/categories', { token }),
  createCategory: (token, name, parentId) => request('/admin/categories', { token, method: 'POST', body: { name, parent_id: parentId || null } }),
  updateCategory: (token, id, name, parentId) => request(`/admin/categories/${id}`, { token, method: 'PUT', body: { name, parent_id: parentId || null } }),
  deleteCategory: (token, id) => request(`/admin/categories/${id}`, { token, method: 'DELETE' }),
  reports: (token) => request('/reports', { token }),
  report: (token, id) => request(`/reports/${id}`, { token }),
  createReport: (token, payload) => request('/reports', { token, method: 'POST', body: payload }),
  reportMessages: (token, id) => request(`/reports/${id}/messages`, { token }),
  sendReportMessage: (token, id, recipientGroup, message) =>
    request(`/reports/${id}/messages`, { token, method: 'POST', body: { recipient_group: recipientGroup, message } }),
  updateReportStatus: (token, id, status, note) =>
    request(`/reports/${id}/status`, { token, method: 'POST', body: { status, note } }),
  requestReportClosure: (token, id, reason) =>
    request(`/reports/${id}/closure-request`, { token, method: 'POST', body: { reason } }),
  closureDecision: (token, id, status, reason) =>
    request(`/reports/${id}/closure-decision`, { token, method: 'POST', body: { status, reason } }),
  cart: (token) => request('/cart', { token }),
  addCartItem: (token, productId, quantity) =>
    request('/cart/items', { token, method: 'POST', body: { product_id: productId, quantity } }),
  removeCartItem: (token, id) => request(`/cart/items/${id}`, { token, method: 'DELETE' }),
  buyerLocations: (token) => request('/buyer/locations', { token }),
  saveBuyerLocation: (token, location, id) =>
    request(id ? `/buyer/locations/${id}` : '/buyer/locations', { token, method: id ? 'PUT' : 'POST', body: location }),
  setDefaultBuyerLocation: (token, id) => request(`/buyer/locations/${id}/default`, { token, method: 'POST' }),
  deleteBuyerLocation: (token, id) => request(`/buyer/locations/${id}`, { token, method: 'DELETE' }),
  startBid: (token, payload) => request('/buyer/bids', { token, method: 'POST', body: payload }),
  buyerRequests: (token) => request('/buyer/requests?include_closed=true', { token }),
  cancelBuyerRequest: (token, id) => request(`/buyer/requests/${id}`, { token, method: 'DELETE' }),
  acceptBid: (token, id, termsToken) =>
    request(`/buyer/bids/${id}/accept`, { token, method: 'POST', body: termsToken ? { terms_token: termsToken } : undefined }),
  dealerRequests: (token) => request('/dealer/requests', { token }),
  submitDealerBid: (token, payload) => request('/dealer/bids', { token, method: 'POST', body: payload }),
  withdrawBid: (token, id) => request(`/dealer/bids/${id}/withdraw`, { token, method: 'POST' }),
  dealerProducts: (token, { q = '', limit = 50, offset = 0 } = {}) =>
    request(`/dealer/products?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`, { token }),
  addDealerProduct: (token, payload) => request('/dealer/products', { token, method: 'POST', body: payload }),
  removeDealerProduct: (token, id) => request(`/dealer/products/${id}`, { token, method: 'DELETE' }),
  dealerProductCategories: (token) => request('/dealer/product-categories', { token }),
  dealerProductTemplate: async (token) => (await request('/dealer/products/template.csv', { token, raw: true })).blob(),
  uploadDealerCatalogue: async (token, file) => {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${API_BASE_URL}/dealer/products/upload`, { method: 'POST', headers: { Accept: 'application/json', Authorization: `Bearer ${token}` }, body: form });
    if (!response.ok) {
      const error = new Error(`API error ${response.status}: ${await response.text()}`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  },
  activateDealerSubscription: (token) => request('/dealer/subscription/activate', { token, method: 'POST' }),
  subscription: (token) => request('/dealer/subscription', { token }),
  subscriptionOrder: (token) => request('/dealer/subscription/order', { token, method: 'POST' }),
  subscriptionTestPay: (token, orderId) => request('/dealer/subscription/test-pay', { token, method: 'POST', body: { order_id: orderId } }),
  subscriptionVerify: (token, proof) => request('/dealer/subscription/verify', { token, method: 'POST', body: proof }),
  exportCsv: async (token, kind) => {
    const response = await request(`/export/${encodeURIComponent(kind)}.csv`, { token, raw: true });
    return response.blob();
  },
};
