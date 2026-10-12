import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart' show kIsWeb;

import 'models.dart';

const configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');
final apiBaseUrl =
    (configuredApiBaseUrl.isNotEmpty
            ? configuredApiBaseUrl
            : kIsWeb && Uri.base.port == 8000
            ? Uri.base.origin
            : 'http://localhost:8000')
        .replaceFirst(RegExp(r'/+$'), '');

class ApiClient {
  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  Future<List<Map<String, dynamic>>> bidMessages(
    String token,
    String bidId,
  ) async => _list(await _get('/bids/$bidId/messages', token));
  Future<Map<String, dynamic>> sendBidMessage(
    String token,
    String bidId,
    String message,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/bids/$bidId/messages'),
      headers: _headers(token),
      body: jsonEncode({'message': message}),
    );
    _throwIfBad(response);
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> searchLocations(
    String token,
    String query,
  ) async => _list(
    await _get('/locations/search?q=${Uri.encodeQueryComponent(query)}', token),
  );

  Future<Map<String, dynamic>> reverseLocation(
    String token,
    double latitude,
    double longitude,
  ) => getMap(
    '/locations/reverse?latitude=$latitude&longitude=$longitude',
    token,
  );

  Future<SessionUser> login(String username, String password) async {
    final response = await _http
        .post(
          Uri.parse('$apiBaseUrl/auth/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        )
        .timeout(const Duration(seconds: 30));
    _throwIfBad(response);
    return SessionUser.fromJson(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> dashboard(SessionUser user) {
    final path = switch (user.role) {
      UserRole.admin => '/admin/dashboard',
      UserRole.buyer => '/buyer/dashboard',
      UserRole.dealer => '/dealer/dashboard',
    };
    return getMap(path, user.accessToken);
  }

  Future<List<ProductItem>> products(String token, {String query = ''}) async {
    final response = await _get(
      '/products?q=${Uri.encodeQueryComponent(query)}&limit=250&offset=0',
      token,
    );
    return _list(response).map((item) => ProductItem.fromJson(item)).toList();
  }

  Future<Map<String, dynamic>> catalogSearch(
    String token,
    Map<String, dynamic> filters,
  ) async {
    final query = <String, dynamic>{};
    for (final entry in filters.entries) {
      if (['specs', 'minimum', 'maximum', 'status'].contains(entry.key))
        continue;
      if (entry.value == null || entry.value == '') continue;
      query[entry.key] = entry.key == 'specs'
          ? jsonEncode(entry.value)
          : entry.value is List
          ? (entry.value as List).map((value) => value.toString()).toList()
          : entry.value.toString();
    }
    final response = await _http.get(
      Uri.parse('$apiBaseUrl/catalog/search').replace(queryParameters: query),
      headers: _headers(token),
    );
    _throwIfBad(response);
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> productSources(String token) =>
      getMap('/admin/product-sources', token);
  Future<Map<String, dynamic>> productStatistics(String token) =>
      getMap('/admin/product-statistics', token);
  Future<void> createProductSource(
    String token,
    Map<String, dynamic> settings,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/admin/product-sources'),
      headers: _headers(token),
      body: jsonEncode(settings),
    );
    _throwIfBad(response);
  }

  Future<void> saveProductSource(
    String token,
    String id,
    Map<String, dynamic> settings,
  ) async {
    final response = await _http.put(
      Uri.parse('$apiBaseUrl/admin/product-sources/$id'),
      headers: _headers(token),
      body: jsonEncode(settings),
    );
    _throwIfBad(response);
  }

  Future<void> fetchProductSource(String token, String id) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/admin/product-sources/$id/fetch'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> createProduct(String token, ProductDraft draft) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/products'),
      headers: _headers(token),
      body: jsonEncode(draft.toJson()),
    );
    _throwIfBad(response);
  }

  Future<void> updateProduct(
    String token,
    String id,
    ProductDraft draft,
  ) async {
    final response = await _http.put(
      Uri.parse('$apiBaseUrl/products/$id'),
      headers: _headers(token),
      body: jsonEncode(draft.toJson()),
    );
    _throwIfBad(response);
  }

  Future<void> deleteProduct(String token, String id) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/products/$id'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<List<BidRecord>> bids(String token) async {
    final response = await _get('/bids', token);
    return _list(response).map((item) => BidRecord.fromJson(item)).toList();
  }

  Future<List<AppNotification>> notifications(String token) async {
    final response = await _get('/notifications', token);
    return _list(
      response,
    ).map((item) => AppNotification.fromJson(item)).toList();
  }

  Future<List<Map<String, dynamic>>> dealers(
    String token, {
    String query = '',
  }) async {
    final response = await _get(
      '/admin/dealers/search?q=${Uri.encodeQueryComponent(query)}',
      token,
    );
    return _list(response);
  }

  Future<List<Map<String, dynamic>>> buyers(
    String token, {
    String query = '',
  }) async {
    final response = await _get(
      '/admin/buyers?q=${Uri.encodeQueryComponent(query)}',
      token,
    );
    return _list(response);
  }

  Future<List<Map<String, dynamic>>> payments(String token) async =>
      _list(await _get('/admin/payments', token));

  Future<List<Map<String, dynamic>>> logs(String token) async =>
      _list(await _get('/admin/logs', token));

  Future<List<Map<String, dynamic>>> reports(String token) async =>
      _list(await _get('/reports', token));

  Future<Map<String, dynamic>> report(String token, String reportId) async =>
      getMap('/reports/$reportId', token);

  Future<Map<String, dynamic>> settings(String token) =>
      getMap('/settings', token);

  Future<void> saveSetting(
    String token,
    String key,
    Map<String, dynamic> value,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/settings/$key'),
      headers: _headers(token),
      body: jsonEncode({'value': value}),
    );
    _throwIfBad(response);
  }

  Future<Map<String, dynamic>> cart(String token) => getMap('/cart', token);

  Future<SessionUser> updateProfile(
    String token,
    Map<String, dynamic> profileData,
  ) async {
    final response = await _http.put(
      Uri.parse('$apiBaseUrl/profile'),
      headers: _headers(token),
      body: jsonEncode(profileData),
    );
    _throwIfBad(response);
    return SessionUser.fromJson(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> fetchProfile(String token) async {
    final response = await _get('/profile', token);
    _throwIfBad(response);
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> buyerLocations(String token) async =>
      _list(await _get('/buyer/locations', token));

  Future<void> saveBuyerLocation(
    String token,
    Map<String, dynamic> location, {
    String? savedId,
  }) async {
    final uri = savedId == null
        ? Uri.parse('$apiBaseUrl/buyer/locations')
        : Uri.parse('$apiBaseUrl/buyer/locations/$savedId');
    final response = savedId == null
        ? await _http.post(
            uri,
            headers: _headers(token),
            body: jsonEncode(location),
          )
        : await _http.put(
            uri,
            headers: _headers(token),
            body: jsonEncode(location),
          );
    _throwIfBad(response);
  }

  Future<void> setDefaultBuyerLocation(String token, String savedId) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/buyer/locations/$savedId/default'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> deleteBuyerLocation(String token, String savedId) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/buyer/locations/$savedId'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> register({
    required String name,
    required String username,
    required String password,
    required String role,
  }) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'name': name,
        'username': username,
        'password': password,
        'role': role,
      }),
    );
    _throwIfBad(response);
  }

  Future<List<Map<String, dynamic>>> getCategories(String token) async {
    final response = await _get('/categories', token);
    _throwIfBad(response);
    return _list(response);
  }

  Future<void> createCategory(
    String token,
    String name,
    String? parentId,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/admin/categories'),
      headers: _headers(token),
      body: jsonEncode({'name': name, 'parent_id': parentId}),
    );
    _throwIfBad(response);
  }

  Future<void> updateCategory(
    String token,
    String id,
    String name,
    String? parentId,
  ) async {
    final response = await _http.put(
      Uri.parse('$apiBaseUrl/admin/categories/$id'),
      headers: _headers(token),
      body: jsonEncode({'name': name, 'parent_id': parentId}),
    );
    _throwIfBad(response);
  }

  Future<void> deleteCategory(String token, String id) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/admin/categories/$id'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<List<Map<String, dynamic>>> dealerRequests(String token) async =>
      _list(await _get('/dealer/requests', token));

  Future<List<Map<String, dynamic>>> buyerRequests(String token) async =>
      _list(await _get('/buyer/requests?include_closed=true', token));

  Future<void> cancelBidRequest(String token, String requestId) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/buyer/requests/$requestId'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> setUserStatus(String token, String userId, String status) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/admin/users/$userId/status'),
      headers: _headers(token),
      body: jsonEncode({'status': status}),
    );
    _throwIfBad(response);
  }

  Future<void> deleteOwnAccount(String token) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/profile'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> setPaymentStatus(
    String token,
    String commissionId,
    String status,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/admin/payments/$commissionId/status'),
      headers: _headers(token),
      body: jsonEncode({'status': status}),
    );
    _throwIfBad(response);
  }

  Future<void> updateReportStatus(
    String token,
    String reportId,
    String status,
    String note,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/reports/$reportId/status'),
      headers: _headers(token),
      body: jsonEncode({'status': status, 'note': note}),
    );
    _throwIfBad(response);
  }

  Future<void> requestReportClosure(
    String token,
    String reportId,
    String reason,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/reports/$reportId/closure-request'),
      headers: _headers(token),
      body: jsonEncode({'reason': reason}),
    );
    _throwIfBad(response);
  }

  Future<void> decideReportClosure(
    String token,
    String reportId,
    String status,
    String reason,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/reports/$reportId/closure-decision'),
      headers: _headers(token),
      body: jsonEncode({'status': status, 'reason': reason}),
    );
    _throwIfBad(response);
  }

  Future<void> addCartItem(String token, String productId, int quantity) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/cart/items'),
      headers: _headers(token),
      body: jsonEncode({'product_id': productId, 'quantity': quantity}),
    );
    _throwIfBad(response);
  }

  Future<void> removeCartItem(String token, String itemId) async {
    final response = await _http.delete(
      Uri.parse('$apiBaseUrl/cart/items/$itemId'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> startBid(
    String token,
    String productId, {
    int quantity = 1,
    String? locationId,
    bool skipFlaggedDealers = true,
    String notes = '',
    int expiryMinutes = 1440,
  }) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/buyer/bids'),
      headers: _headers(token),
      body: jsonEncode({
        'product_id': productId,
        'quantity': quantity,
        'location_id': locationId,
        'skip_flagged_dealers': skipFlaggedDealers,
        'expiry_minutes': expiryMinutes,
        'fields': {
          if (notes.trim().isNotEmpty) 'Notes': notes.trim(),
          'Source': 'Buyer bid setup popup',
        },
      }),
    );
    _throwIfBad(response);
  }

  Future<void> acceptBid(String token, String bidId) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/buyer/bids/$bidId/accept'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> payBid(String token, String bidId) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/dealer/bids/$bidId/pay'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> withdrawBid(String token, String bidId) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/dealer/bids/$bidId/withdraw'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> activateDealerSubscription(String token) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/dealer/subscription/activate'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> markNotificationsRead(String token) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/notifications/mark-read'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<void> markSingleNotificationRead(
    String token,
    String notificationId,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/notifications/$notificationId/mark-read'),
      headers: _headers(token),
    );
    _throwIfBad(response);
  }

  Future<String> createReport(
    String token,
    String bidId,
    String reason,
    String description,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/reports'),
      headers: _headers(token),
      body: jsonEncode({
        'bid_id': bidId,
        'reason': reason,
        'description': description,
      }),
    );
    _throwIfBad(response);
    final data = jsonDecode(response.body);
    return data['id']?.toString() ?? '';
  }

  Future<void> submitDealerBid(
    String token, {
    required String requestId,
    required double amount,
    required double discountAmount,
    required String warrantyText,
    required String deliveryTime,
    required bool installationIncluded,
    required String freeGifts,
    required String extraServices,
    required String notes,
  }) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/dealer/bids'),
      headers: _headers(token),
      body: jsonEncode({
        'bid_request_id': requestId,
        'amount': amount,
        'discount_amount': discountAmount,
        'warranty_text': warrantyText,
        'delivery_time': deliveryTime,
        'installation_included': installationIncluded,
        'free_gifts': freeGifts,
        'extra_services': extraServices,
        'notes': notes,
      }),
    );
    _throwIfBad(response);
  }

  Future<String> exportCsv(String token, String kind) async {
    final response = await _get('/export/$kind.csv', token);
    _throwIfBad(response);
    return response.body;
  }

  Future<List<Map<String, dynamic>>> reportMessages(
    String token,
    String reportId,
  ) async => _list(await _get('/reports/$reportId/messages', token));

  Future<void> sendReportMessage(
    String token,
    String reportId,
    String recipientGroup,
    String message,
  ) async {
    final response = await _http.post(
      Uri.parse('$apiBaseUrl/reports/$reportId/messages'),
      headers: _headers(token),
      body: jsonEncode({'recipient_group': recipientGroup, 'message': message}),
    );
    _throwIfBad(response);
  }

  Future<Map<String, dynamic>> getMap(String path, String token) async {
    final response = await _get(path, token);
    _throwIfBad(response);
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<http.Response> _get(String path, String token) {
    return _http.get(Uri.parse('$apiBaseUrl$path'), headers: _headers(token));
  }

  Map<String, String> _headers(String token) => {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    if (token.isNotEmpty) 'Authorization': 'Bearer $token',
  };

  List<Map<String, dynamic>> _list(http.Response response) {
    _throwIfBad(response);
    final data = jsonDecode(response.body);
    if (data is List) {
      return data.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return [];
  }

  void _throwIfBad(http.Response response) {
    if ((response.headers['content-type'] ?? '').toLowerCase().contains(
          'text/html',
        ) ||
        response.body.trimLeft().startsWith('<')) {
      throw Exception(
        'The server returned a webpage instead of API data. Restart the backend to load the latest routes and check the API address. Then retry.',
      );
    }
    if (response.statusCode >= 400) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
  }
}
