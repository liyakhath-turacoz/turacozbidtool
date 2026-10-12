import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'dart:async';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:geolocator/geolocator.dart';

import 'core/api_client.dart';
import 'core/bid_conversation.dart';
import 'core/csv_download.dart';
import 'core/models.dart';
import 'core/session_store.dart';
import 'core/widgets.dart';

void main() {
  runApp(const TuracozBidToolApp());
}

class TuracozBidToolApp extends StatelessWidget {
  const TuracozBidToolApp({super.key});

  @override
  Widget build(BuildContext context) {
    final startsAtAdmin = Uri.base.path.toLowerCase().startsWith('/admin');
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Turacoz Bid Tool',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      home: AppShell(startsAtAdmin: startsAtAdmin),
    );
  }
}

class AppTheme {
  static ThemeData light() => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xFF6D28D9),
      primary: const Color(0xFF6D28D9),
      secondary: const Color(0xFF16A34A),
      tertiary: const Color(0xFFEC4899),
      surface: Colors.white,
    ),
    scaffoldBackgroundColor: Colors.white,
    cardTheme: _cardTheme(Colors.white, const Color(0xFFEDE9FE)),
    inputDecorationTheme: _inputTheme(Colors.white),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: const Color(0xFF6D28D9),
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    chipTheme: const ChipThemeData(
      backgroundColor: Color(0xFFF5F3FF),
      selectedColor: Color(0xFFE9D5FF),
      labelStyle: TextStyle(color: Color(0xFF3B0764)),
      side: BorderSide(color: Color(0xFFE9D5FF)),
    ),
  );

  static ThemeData dark() => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xFF33B36B),
      brightness: Brightness.dark,
    ),
    cardTheme: _cardTheme(const Color(0xFF111827), const Color(0xFF263244)),
    inputDecorationTheme: _inputTheme(const Color(0xFF111827)),
  );

  static CardThemeData _cardTheme(Color color, Color border) => CardThemeData(
    color: color,
    elevation: 1.5,
    shadowColor: const Color(0x1A6D28D9),
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(16),
      side: BorderSide(color: border),
    ),
  );

  static InputDecorationTheme _inputTheme(Color fill) => InputDecorationTheme(
    filled: true,
    fillColor: fill,
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: Color(0xFFE9D5FF)),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
  );
}

class NavItem {
  const NavItem(this.label, this.icon);
  final String label;
  final IconData icon;
}

const adminNav = [
  NavItem('Dashboard', Icons.dashboard_outlined),
  NavItem('Dealer Management', Icons.storefront_outlined),
  NavItem('Buyer Management', Icons.people_alt_outlined),
  NavItem('Products / Catalog', Icons.inventory_2_outlined),
  NavItem('Bid History', Icons.gavel_outlined),
  NavItem('Reports', Icons.report_outlined),
  NavItem('Platform Rules & Settings', Icons.tune_outlined),
];

const buyerNav = [
  NavItem('Home', Icons.home_outlined),
  NavItem('Bid Page', Icons.bolt_outlined),
  NavItem('Orders / History', Icons.history_outlined),
  NavItem('Cart', Icons.shopping_cart_outlined),
  NavItem('Notifications', Icons.notifications_outlined),
  NavItem('Profile', Icons.person_outline),
  NavItem('Reports / Support', Icons.support_agent_outlined),
];

const buyerMenuIndexes = [0, 1, 2, 6, 5];

const buyerCategories = [
  'Electronics',
  'Accessory',
  'Healthcare Essentials',
  'Home Appliance',
  'Kitchen Appliances',
];

const Map<String, Map<String, List<String>>> categoryHierarchy = {
  'Electronics': {
    'Laptops': ['Apple', 'Dell', 'Lenovo', 'HP', 'Asus', 'Acer', 'Microsoft'],
    'Mobiles': [
      'Apple',
      'Samsung',
      'OnePlus',
      'Xiaomi',
      'Google',
      'Oppo',
      'Vivo',
    ],
    'Tablets': ['Apple', 'Samsung', 'Lenovo', 'Xiaomi', 'Realme'],
    'TVs': ['Sony', 'Samsung', 'LG', 'Xiaomi', 'TCL', 'OnePlus'],
  },
  'Accessory': {
    'Headphones': ['Sony', 'Bose', 'JBL', 'Apple', 'Sennheiser', 'Boat'],
    'Chargers': ['Apple', 'Samsung', 'Anker', 'Mi', 'OnePlus'],
  },
  'Healthcare Essentials': {
    'BP Checker': ['Omron', 'Dr Trust', 'Beurer', 'Accu-Chek'],
    'Thermometer': ['Omron', 'Dr Trust', 'Beurer', 'Philips'],
  },
  'Home Appliance': {
    'Vacuum Cleaner': ['Dyson', 'Eureka Forbes', 'Philips', 'Kent', 'Mi'],
    'Washing Machine': ['LG', 'Samsung', 'IFB', 'Whirlpool', 'Bosch'],
  },
  'Kitchen Appliances': {
    'Cooker': ['Prestige', 'Hawkins', 'Pigeon', 'Butterfly'],
    'Induction Cooktop': ['Prestige', 'Philips', 'Pigeon', 'Bajaj'],
    'Microwave': ['Samsung', 'LG', 'IFB', 'Panasonic', 'Haier'],
  },
};

const dealerNav = [
  NavItem('Dealer Dashboard', Icons.dashboard_outlined),
  NavItem('Incoming Bid Requests', Icons.move_to_inbox_outlined),
  NavItem('Active Bids', Icons.edit_note_outlined),
  NavItem('Bid History / Orders', Icons.history_outlined),
  NavItem('Business Profile', Icons.store_outlined),
  NavItem('Notifications', Icons.notifications_outlined),
  NavItem('Reports / Support', Icons.support_agent_outlined),
];

class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.startsAtAdmin});

  final bool startsAtAdmin;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  final _api = ApiClient();
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _search = TextEditingController();
  final Map<String, BigInt> _snapshotVersions = {};
  int _refreshVersion = 0;

  // Custom search/filter controllers for Admin tabs
  final _dealerSearchController = TextEditingController();
  String? _dealerStatusFilter;
  String? _dealerCountryFilter;
  String? _dealerStateFilter;
  String? _dealerCityFilter;
  String? _dealerPincodeFilter;
  String? _dealerCategoryFilter;

  final _buyerSearchController = TextEditingController();
  String? _buyerLocationFilter;
  String? _buyerCategoryFilter;
  String? _buyerStatusFilter;

  final _productSearchController = TextEditingController();
  String? _productCategoryFilter;
  String? _productBrandFilter;
  String? _productStatusFilter;
  final _productMinPriceFilter = TextEditingController();
  final _productMaxPriceFilter = TextEditingController();

  final _bidSearchController = TextEditingController();
  String? _bidStatusFilter;
  String? _bidCommissionFilter;

  final _reportSearchController = TextEditingController();
  String? _reportStatusFilter;

  bool _showRevenueBreakdown = false;

  // Selection states for admin details popups
  String? _selectedDealerId;
  Map<String, dynamic>? _selectedDealerDetails;

  String? _selectedBuyerId;
  Map<String, dynamic>? _selectedBuyerDetails;

  String? _selectedBidId;
  Map<String, dynamic>? _selectedBidDetails;

  String? _selectedReportId;
  Map<String, dynamic>? _selectedReportDetails;
  List<Map<String, dynamic>> _reportMessages = [];
  final _reportMessageController = TextEditingController();
  String _reportRecipientGroup = 'both';

  final _productName = TextEditingController();
  final _category = TextEditingController(text: 'Electronics');
  final _brand = TextEditingController();
  final _model = TextEditingController();
  final _priceMin = TextEditingController();
  final _priceMax = TextEditingController();
  final _location = TextEditingController(text: 'Mumbai');
  final _filterBrand = TextEditingController();
  final _filterMinPrice = TextEditingController();
  final _filterMaxPrice = TextEditingController();
  final _filterLocation = TextEditingController();
  final List<FieldPairController> _specs = [
    FieldPairController.withText('RAM', '16 GB'),
  ];

  SessionUser? _user;
  WebSocketChannel? _wsChannel;
  Timer? _wsReconnectTimer;
  Timer? _wsRefreshTimer;
  int _wsGeneration = 0;
  int _wsReconnectAttempts = 0;
  bool _loading = false;
  bool _offlinePreview = false;
  bool _isRegistering = false;
  String? _error;
  int _tab = 0;
  String? _buyerCategory;
  String _sortMode = 'Newest';
  ProductItem? _selectedProduct;
  String? _focusedBidId;
  Map<String, dynamic> _dashboard = {};
  Map<String, dynamic> _cart = {};
  Map<String, dynamic> _settings = {};
  List<ProductItem> _products = [];
  List<BidRecord> _bids = [];
  List<AppNotification> _notifications = [];
  List<Map<String, dynamic>> _dealers = [];
  List<Map<String, dynamic>> _buyers = [];
  List<Map<String, dynamic>> _payments = [];
  List<Map<String, dynamic>> _logs = [];
  List<Map<String, dynamic>> _reports = [];
  List<Map<String, dynamic>> _dealerRequests = [];
  List<Map<String, dynamic>> _buyerRequests = [];
  bool _dealerSubscribed = false;
  bool _dismissSubscriptionBanner = false;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  @override
  void dispose() {
    _disconnectWebSocket();
    for (final controller in [
      _username,
      _password,
      _search,
      _dealerSearchController,
      _buyerSearchController,
      _productSearchController,
      _productMinPriceFilter,
      _productMaxPriceFilter,
      _bidSearchController,
      _reportSearchController,
      _reportMessageController,
      _productName,
      _category,
      _brand,
      _model,
      _priceMin,
      _priceMax,
      _location,
      _filterBrand,
      _filterMinPrice,
      _filterMaxPrice,
      _filterLocation,
    ]) {
      controller.dispose();
    }
    for (final field in _specs) {
      field.dispose();
    }
    super.dispose();
  }

  Future<void> _login() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final user = await _api.login(_username.text.trim(), _password.text);
      setState(() {
        _user = user;
        _offlinePreview = false;
        _tab = 0;
      });
      await _saveSession(user);
      await _refresh();
      _connectWebSocket();
    } catch (error) {
      final preview = _previewUser(_username.text.trim(), _password.text);
      if (preview == null) {
        setState(() {
          _error = error is TimeoutException
              ? 'Login timed out. Check the connection and try again.'
              : 'Login failed or backend is unavailable. Start FastAPI and MariaDB, then retry.';
        });
      } else {
        setState(() {
          _user = preview;
          _offlinePreview = true;
          _tab = 0;
          _error = null;
          _loadPreviewData(preview.role);
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _saveSession(SessionUser user) async {
    await saveSession(jsonEncode(user.toJson()));
  }

  Future<void> _clearSavedSession() async {
    await clearSession();
  }

  Future<void> _restoreSession() async {
    setState(() => _loading = true);
    try {
      final raw = await readSavedSession();
      if (raw == null || raw.isEmpty) return;
      final user = SessionUser.fromJson(jsonDecode(raw));
      if (user.accessToken.isEmpty || user.accessToken == 'preview') return;
      setState(() {
        _user = user;
        _offlinePreview = false;
        _tab = 0;
      });
      await _refresh();
      _connectWebSocket();
    } catch (_) {
      await _clearSavedSession();
      if (mounted) {
        setState(() {
          _user = null;
          _offlinePreview = false;
        });
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _refresh({bool silent = false}) async {
    final refreshVersion = ++_refreshVersion;
    final user = _user;
    if (user == null) return;
    if (!silent) setState(() => _loading = true);
    try {
      final productsQuery = (user.role == UserRole.admin)
          ? _productSearchController.text.trim()
          : _search.text.trim();
      final products = await _api.products(
        user.accessToken,
        query: productsQuery,
      );
      final bids = await _api.bids(user.accessToken);
      final notifications = await _api.notifications(user.accessToken);
      final dashboard = await _api.dashboard(user);
      List<Map<String, dynamic>> dealers = _dealers;
      List<Map<String, dynamic>> buyers = _buyers;
      List<Map<String, dynamic>> payments = _payments;
      List<Map<String, dynamic>> logs = _logs;
      List<Map<String, dynamic>> reports = _reports;
      List<Map<String, dynamic>> requests = _dealerRequests;
      List<Map<String, dynamic>> buyerRequests = _buyerRequests;
      Map<String, dynamic> cart = _cart;
      Map<String, dynamic> settings = _settings;
      var dealerSubscribed = false;
      if (user.role == UserRole.admin) {
        dealers = await _api.dealers(
          user.accessToken,
          query: _dealerSearchController.text.trim(),
        );
        buyers = await _api.buyers(
          user.accessToken,
          query: _buyerSearchController.text.trim(),
        );
        payments = await _api.payments(user.accessToken);
        logs = await _api.logs(user.accessToken);
        reports = await _api.reports(user.accessToken);
        settings = await _api.settings(user.accessToken);
      } else if (user.role == UserRole.buyer) {
        cart = await _api.cart(user.accessToken);
        reports = await _api.reports(user.accessToken);
        buyerRequests = await _api.buyerRequests(user.accessToken);
        settings = await _api.settings(user.accessToken);
      } else {
        requests = await _api.dealerRequests(user.accessToken);
        reports = await _api.reports(user.accessToken);
        settings = await _api.settings(user.accessToken);
        try {
          final profile = await _api.fetchProfile(user.accessToken);
          dealerSubscribed =
              profile['subscribed'] == true || profile['subscribed'] == 1;
        } catch (_) {}
      }
      if (!mounted ||
          _user?.accessToken != user.accessToken ||
          refreshVersion != _refreshVersion)
        return;
      setState(() {
        _dashboard = dashboard;
        _products = products;
        _bids = bids;
        liveBidRecords.value = bids;
        _notifications = notifications;
        _dealers = dealers;
        _buyers = buyers;
        _payments = payments;
        _logs = logs;
        _reports = reports;
        _dealerRequests = requests;
        _buyerRequests = buyerRequests;
        _cart = cart;
        _settings = settings;
        _dealerSubscribed = dealerSubscribed;
        _offlinePreview = false;
      });
    } catch (error) {
      if (mounted && _user?.accessToken == user.accessToken) {
        if (error.toString().contains('401')) {
          _logout();
          setState(() {
            _error = 'Session expired. Please log in again.';
          });
          return;
        }
        setState(() => _error = 'Could not load live data: $error');
      }
    } finally {
      if (!silent && mounted && _user?.accessToken == user.accessToken) {
        setState(() => _loading = false);
      }
    }
  }

  void _logout() {
    bidChatSession = null;
    liveBidRecords.value = [];
    liveBidMessages.value = {};
    _snapshotVersions.clear();
    _clearSavedSession();
    setState(() {
      _user = null;
      _loading = false;
      _tab = 0;
      _error = null;
      _products = const [];
      _bids = const [];
      _notifications = const [];
      _dashboard = const {};
      _dealers = const [];
      _buyers = const [];
      _payments = const [];
      _logs = const [];
      _reports = const [];
      _dealerRequests = const [];
      _buyerRequests = const [];
      _cart = const {};
      _settings = const {};
      _focusedBidId = null;
      _selectedReportDetails = null;
      _reportMessages = const [];
      _offlinePreview = false;
    });
    _disconnectWebSocket();
  }

  void _connectWebSocket() {
    _disconnectWebSocket();
    final user = _user;
    if (user == null) return;
    bidChatSession = user;
    final generation = _wsGeneration;

    final apiUri = Uri.parse(apiBaseUrl);
    final wsScheme = apiUri.scheme == 'https' ? 'wss' : 'ws';
    final wsHost = apiUri.host;
    final wsPort = apiUri.port != 0 ? ':${apiUri.port}' : '';
    final wsUri = Uri.parse(
      '$wsScheme://$wsHost$wsPort/ws/${user.id}?token=${Uri.encodeQueryComponent(user.accessToken)}',
    );

    try {
      final channel = WebSocketChannel.connect(wsUri);
      _wsChannel = channel;
      channel.ready
          .then((_) {
            if (!mounted || generation != _wsGeneration) return;
            if (_wsReconnectAttempts > 0) {
              _refresh(silent: true);
              bidChatReconnects.value++;
            }
            _wsReconnectAttempts = 0;
          })
          .catchError((Object error) {});
      channel.stream.listen(
        (message) {
          if (!mounted || generation != _wsGeneration) return;
          dynamic payload;
          try {
            payload = jsonDecode(message.toString());
          } on FormatException {
            return;
          }
          if (payload is! Map || payload['type'] == 'pong') return;
          if (payload['type'] == 'bid_message' && payload['message'] is Map) {
            receiveBidMessage(
              payload['bid_id'].toString(),
              Map<String, dynamic>.from(payload['message']),
            );
            return;
          }
          if (payload['type'] == 'bid_snapshot') {
            final requestId = payload['request_id'].toString();
            final version = BigInt.parse(payload['version'].toString());
            if (version <= (_snapshotVersions[requestId] ?? BigInt.zero))
              return;
            _snapshotVersions[requestId] = version;
            _refreshVersion++;
            final bids = (payload['bids'] as List)
                .map(
                  (row) => BidRecord.fromJson(Map<String, dynamic>.from(row)),
                )
                .toList();
            setState(() {
              _bids = [
                ...bids,
                ..._bids.where((bid) => bid.bidRequestId != requestId),
              ];
              if (user.role == UserRole.buyer)
                _buyerRequests = [
                  Map<String, dynamic>.from(payload['request']),
                  ..._buyerRequests.where(
                    (request) => request['id'] != requestId,
                  ),
                ];
              if (user.role == UserRole.dealer)
                _dealerRequests = [
                  if (payload['dealer_request'] is Map)
                    Map<String, dynamic>.from(payload['dealer_request']),
                  ..._dealerRequests.where(
                    (request) => request['id'] != requestId,
                  ),
                ];
            });
            liveBidRecords.value = _bids;
            if (user.role == UserRole.dealer) {
              final ownBids = _bids.where((bid) => bid.isMine).toList();
              setState(
                () => _dashboard = {
                  ..._dashboard,
                  'metrics': {
                    ...Map<String, dynamic>.from(_dashboard['metrics'] ?? {}),
                    'incoming_requests': _dealerRequests.length,
                    'submitted_bids': ownBids.length,
                    'won_bids': ownBids
                        .where((bid) => bid.status == 'won')
                        .length,
                    'lost_bids': ownBids
                        .where((bid) => bid.status == 'lost')
                        .length,
                    'revenue': ownBids
                        .where((bid) => bid.status == 'won')
                        .fold<double>(0, (sum, bid) => sum + bid.amount),
                  },
                  'requests': _dealerRequests.take(5).toList(),
                },
              );
            }
            _wsRefreshTimer?.cancel();
            _wsRefreshTimer = Timer(
              const Duration(milliseconds: 100),
              () async {
                try {
                  final notifications = await _api.notifications(
                    user.accessToken,
                  );
                  if (mounted && generation == _wsGeneration)
                    setState(() => _notifications = notifications);
                } catch (_) {}
              },
            );
            return;
          }
          if (payload['type'] == 'new_message' &&
              payload['message'] is Map &&
              payload['report_id'] == _selectedReportId) {
            final message = Map<String, dynamic>.from(payload['message']);
            setState(
              () => _reportMessages = mergeBidMessages(_reportMessages, [
                message,
              ]),
            );
          }
          final requestId = (payload['request_id'] ?? payload['bid_request_id'])
              ?.toString();
          if (requestId != null &&
              _snapshotVersions.containsKey(requestId) &&
              payload['refresh_required'] != true)
            return;
          _wsRefreshTimer?.cancel();
          _wsRefreshTimer = Timer(const Duration(milliseconds: 100), () async {
            if (!mounted || generation != _wsGeneration) return;
            await _refresh(silent: true);
            if (mounted &&
                _selectedReportId != null &&
                generation == _wsGeneration) {
              await _fetchReportDetails(_selectedReportId!, silent: true);
            }
          });
        },
        onError: (err) {
          if (mounted && generation == _wsGeneration) _scheduleWsReconnect();
        },
        onDone: () {
          if (!mounted || generation != _wsGeneration) return;
          if (channel.closeCode == 4401 || channel.closeCode == 4403) {
            _logout();
          } else {
            _scheduleWsReconnect();
          }
        },
      );
    } catch (e) {
      _scheduleWsReconnect();
    }
  }

  void _scheduleWsReconnect() {
    _wsReconnectTimer?.cancel();
    final delay = (_wsReconnectAttempts++ < 5)
        ? (1 << (_wsReconnectAttempts - 1))
        : 30;
    _wsReconnectTimer = Timer(Duration(seconds: delay), () {
      if (mounted && _user != null) {
        _connectWebSocket();
      }
    });
  }

  void _disconnectWebSocket() {
    _wsGeneration++;
    _wsRefreshTimer?.cancel();
    _wsReconnectTimer?.cancel();
    _wsReconnectTimer = null;
    try {
      _wsChannel?.sink.close();
    } catch (_) {}
    _wsChannel = null;
  }

  void _openBidHistoryFromNotification(AppNotification notification) {
    final user = _user;
    if (user == null) return;
    final targetTab = switch (user.role) {
      UserRole.buyer => 2,
      UserRole.dealer => 3,
      UserRole.admin => 4,
    };
    setState(() {
      _focusedBidId = notification.targetBidId.isEmpty
          ? null
          : notification.targetBidId;
      _tab = targetTab;
    });
  }

  Future<void> _openReportFromNotification(AppNotification notification) async {
    final user = _user;
    if (user == null) return;
    final targetTab = switch (user.role) {
      UserRole.admin => 5,
      UserRole.buyer => 6,
      UserRole.dealer => 6,
    };
    setState(() => _tab = targetTab);
    if (notification.targetReportId.isNotEmpty) {
      await _fetchReportDetails(notification.targetReportId);
    }
  }

  SessionUser? _previewUser(String username, String password) {
    return null;
  }

  void _loadPreviewData(UserRole role) {
    _products = const [];
    _bids = const [];
    _notifications = const [];
    _dashboard = const {};
    _dealers = const [];
    _buyers = const [];
    _payments = const [];
    _logs = const [];
    _reports = const [];
    _dealerRequests = const [];
  }

  void _changeTab(int newTab) {
    setState(() {
      _tab = newTab;
    });
  }

  Future<void> _markNotificationsAsRead() async {
    final user = _user;
    if (user == null || _offlinePreview) return;
    try {
      await _api.markNotificationsRead(user.accessToken);
      setState(() {
        _notifications = _notifications
            .map(
              (n) => AppNotification(
                id: n.id,
                title: n.title,
                message: n.message,
                eventType: n.eventType,
                targetBidId: n.targetBidId,
                targetReportId: n.targetReportId,
                createdAt: n.createdAt,
                isRead: true,
              ),
            )
            .toList();
      });
    } catch (_) {}
  }

  Future<void> _handleNotificationTap(AppNotification notif) async {
    final user = _user;
    if (user == null) return;

    // Mark as read locally first to be responsive
    setState(() {
      _notifications = _notifications.map((n) {
        if (n.id == notif.id) {
          return AppNotification(
            id: n.id,
            title: n.title,
            message: n.message,
            eventType: n.eventType,
            targetBidId: n.targetBidId,
            targetReportId: n.targetReportId,
            createdAt: n.createdAt,
            isRead: true,
          );
        }
        return n;
      }).toList();
    });

    if (!_offlinePreview) {
      try {
        await _api.markSingleNotificationRead(user.accessToken, notif.id);
      } catch (_) {}
    }

    // Perform redirection based on event type
    if (notif.eventType.startsWith('report_') ||
        notif.targetReportId.isNotEmpty) {
      _openReportFromNotification(notif);
    } else if (notif.eventType == 'new_bid' ||
        notif.eventType == 'bid_request_created') {
      if (user.role == UserRole.buyer) {
        setState(() => _tab = 1); // Active Bids (BuyerBidPage)
      } else if (user.role == UserRole.dealer) {
        setState(() => _tab = 2); // Active Bids (DealerBidSubmissionPage)
      }
    } else if (notif.eventType == 'new_bid_request') {
      if (user.role == UserRole.dealer) {
        setState(() => _tab = 1); // Incoming Requests (IncomingRequestsPage)
      }
    } else if (notif.eventType == 'bid_accepted' ||
        notif.eventType == 'bid_lost' ||
        notif.eventType == 'commission_paid') {
      _openBidHistoryFromNotification(notif);
    } else if (notif.eventType == 'subscription_activated') {
      if (user.role == UserRole.dealer) {
        setState(() => _tab = 4); // Business Profile
      }
    } else {
      // General fallback
      if (user.role == UserRole.buyer) {
        setState(() => _tab = 1); // Active Bids
      } else if (user.role == UserRole.dealer) {
        setState(() => _tab = 2); // Active Bids
      } else if (user.role == UserRole.admin) {
        setState(() => _tab = 0); // Dashboard
      }
    }
  }

  List<NavItem> get _nav {
    final role = _user?.role;
    if (role == UserRole.admin) return adminNav;
    if (role == UserRole.dealer) return dealerNav;
    return buyerNav;
  }

  List<int> get _visibleIndexes => _user?.role == UserRole.buyer
      ? buyerMenuIndexes
      : List.generate(_nav.length, (index) => index);

  List<NavItem> get _visibleNav =>
      _visibleIndexes.map((index) => _nav[index]).toList();

  Future<void> _handleRegister(
    String name,
    String username,
    String password,
    String role,
  ) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _api.register(
        name: name,
        username: username,
        password: password,
        role: role,
      );
      setState(() {
        _loading = false;
        _isRegistering = false;
        _username.text = username;
        _password.text = password;
        _error = 'Registration successful! Please login.';
      });
    } catch (e) {
      setState(() {
        _loading = false;
      });
      rethrow;
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = _user;
    if (user == null) {
      if (_isRegistering) {
        return RegisterPage(
          loading: _loading,
          onRegister: _handleRegister,
          onCancel: () => setState(() => _isRegistering = false),
        );
      }
      return LoginPage(
        username: _username,
        password: _password,
        loading: _loading,
        error: _error,
        directAdmin: widget.startsAtAdmin,
        onLogin: _login,
        onRegisterPressed: () => setState(() {
          _error = null;
          _isRegistering = true;
        }),
        onFill: (username, password) {
          setState(() {
            _username.text = username;
            _password.text = password;
          });
        },
      );
    }
    final isBuyer = user.role == UserRole.buyer;
    final unreadNotificationsCount = _notifications
        .where((n) => !n.isRead)
        .length;

    return Scaffold(
      drawer: isBuyer
          ? _BuyerDrawer(
              nav: _visibleNav,
              selectedTab: _tab,
              indexes: _visibleIndexes,
              onSelect: _changeTab,
              onLogout: _logout,
            )
          : null,
      appBar: AppBar(
        leading: isBuyer
            ? Builder(
                builder: (context) => IconButton(
                  tooltip: 'Menu',
                  onPressed: () => Scaffold.of(context).openDrawer(),
                  icon: const Icon(Icons.menu),
                ),
              )
            : null,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(isBuyer ? 'Turacoz Bid Tool Marketplace' : _nav[_tab].label),
            Text(
              '${user.name} | ${_offlinePreview ? 'offline preview' : 'live API'}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: isBuyer
            ? [
                IconButton(
                  tooltip: 'Cart',
                  onPressed: () => _changeTab(4),
                  icon: const Icon(Icons.shopping_cart_outlined),
                ),
                IconButton(
                  tooltip: 'Notifications',
                  onPressed: () => _changeTab(5),
                  icon: Badge(
                    label: Text('$unreadNotificationsCount'),
                    isLabelVisible: unreadNotificationsCount > 0,
                    child: const Icon(Icons.notifications_outlined),
                  ),
                ),
                IconButton(
                  tooltip: 'Profile',
                  onPressed: () => _changeTab(6),
                  icon: const Icon(Icons.person_outline),
                ),
                const SizedBox(width: 8),
              ]
            : [
                IconButton(
                  tooltip: 'Refresh',
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
                IconButton(
                  tooltip: 'Logout',
                  onPressed: _logout,
                  icon: const Icon(Icons.logout),
                ),
                const SizedBox(width: 8),
              ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final page = _rolePage(user);
          if (constraints.maxWidth >= 920) {
            return Row(
              children: [
                if (!isBuyer)
                  NavigationRail(
                    selectedIndex: _tab,
                    onDestinationSelected: _changeTab,
                    labelType: constraints.maxWidth >= 1180
                        ? NavigationRailLabelType.all
                        : NavigationRailLabelType.selected,
                    destinations: _nav.asMap().entries.map((entry) {
                      final item = entry.value;
                      final isNotificationsTab = item.label == 'Notifications';
                      Widget iconWidget = Icon(item.icon);
                      if (isNotificationsTab && unreadNotificationsCount > 0) {
                        iconWidget = Badge(
                          label: Text('$unreadNotificationsCount'),
                          child: iconWidget,
                        );
                      }
                      return NavigationRailDestination(
                        icon: iconWidget,
                        label: Text(item.label),
                      );
                    }).toList(),
                  ),
                const VerticalDivider(width: 1),
                Expanded(child: page),
              ],
            );
          }
          return Column(
            children: [
              Expanded(child: page),
              if (!isBuyer)
                NavigationBar(
                  selectedIndex: _tab.clamp(0, _nav.length - 1),
                  onDestinationSelected: _changeTab,
                  destinations: _nav.asMap().entries.map((entry) {
                    final item = entry.value;
                    final isNotificationsTab = item.label == 'Notifications';
                    Widget iconWidget = Icon(item.icon);
                    if (isNotificationsTab && unreadNotificationsCount > 0) {
                      iconWidget = Badge(
                        label: Text('$unreadNotificationsCount'),
                        child: iconWidget,
                      );
                    }
                    return NavigationDestination(
                      icon: iconWidget,
                      label: item.label,
                    );
                  }).toList(),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _rolePage(SessionUser user) {
    if (_loading && _products.isEmpty && _dashboard.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    final error = _error;
    if (error != null) {
      return PageScaffold(
        child: DataPanel(
          title: 'Attention',
          children: [
            Text(error),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }
    return switch (user.role) {
      UserRole.admin => _adminPage(user),
      UserRole.buyer => _buyerPage(user),
      UserRole.dealer => _dealerPage(user),
    };
  }

  Widget _adminPage(SessionUser user) {
    switch (_tab) {
      case 0:
        return DashboardPage(
          title: 'Admin Dashboard',
          subtitle:
              'Live control room for platform health, revenue, bids, and alerts.',
          dashboard: _dashboard,
          notifications: _notifications,
          onMetricClick: _onMetricClick,
          extra: const [],
        );
      case 1:
        return AdminUsersPage(
          title: 'Dealer Management',
          rows: _dealers,
          role: 'dealer',
          onStatus: _setUserStatus,
          searchController: _dealerSearchController,
          onSearch: _refresh,
          onDetails: _fetchDealerDetails,
          selectedDetails: _selectedDealerDetails,
          onCloseDetails: () => setState(() => _selectedDealerDetails = null),
        );
      case 2:
        return AdminUsersPage(
          title: 'Buyer Management',
          rows: _buyers,
          role: 'buyer',
          onStatus: _setUserStatus,
          searchController: _buyerSearchController,
          onSearch: _refresh,
          onDetails: _fetchBuyerDetails,
          selectedDetails: _selectedBuyerDetails,
          onCloseDetails: () => setState(() => _selectedBuyerDetails = null),
        );
      case 3:
        return ProductAdminPage(
          products: _products,
          onCreate: _createProduct,
          search: _productSearchController,
          onSearch: _refresh,
          onExport: () => _showExport('products'),
          name: _productName,
          category: _category,
          brand: _brand,
          model: _model,
          priceMin: _priceMin,
          priceMax: _priceMax,
          specs: _specs,
          onAddSpec: () =>
              setState(() => _specs.add(FieldPairController.withText('', ''))),
          token: user.accessToken,
          onUpdateProduct: _updateProduct,
          onDeleteProduct: _deleteProduct,
        );
      case 4:
        return BidHistoryPage(
          bids: _bids,
          payments: _payments,
          logs: _logs,
          onPaymentStatus: _setPaymentStatus,
          onExport: () => _showExport('bids'),
          initialStatusFilter: _bidStatusFilter,
          initialCommissionFilter: _bidCommissionFilter,
          showRevenueBreakdown: _showRevenueBreakdown,
        );
      case 5:
        return ReportsPage(
          reports: _reports,
          onExport: () => _showExport('reports'),
          userRole: 'admin',
          currentUserId: user.id,
          selectedDetails: _selectedReportDetails,
          messages: _reportMessages,
          messageController: _reportMessageController,
          recipientGroup: _reportRecipientGroup,
          onDetails: _fetchReportDetails,
          onCloseDetails: () => setState(() => _selectedReportDetails = null),
          onSendMessage: _sendReportMessage,
          onRecipientGroupChanged: (val) =>
              setState(() => _reportRecipientGroup = val),
          onUpdateReportStatus: _updateReportStatus,
          onClosureDecision: _decideReportClosure,
        );
      case 6:
        return SettingsPage(
          settings: _settings,
          onSaveSetting: _saveSetting,
          token: user.accessToken,
        );
      default:
        return const Center(child: Text('Page not found'));
    }
  }

  Widget _buyerPage(SessionUser user) {
    final filtered = _filteredBuyerProducts();
    switch (_tab) {
      case 0:
        return BuyerHomePage(
          token: user.accessToken,
          api: _api,
          onCart: _addCart,
          onBid: _openBidSetup,
          onSelect: _selectProduct,
          bids: _bids,
        );
      case 1:
        return BuyerBidPage(
          bids: _bids,
          requests: _buyerRequests
              .where((request) => request['status'] == 'active')
              .toList(),
          selectedProduct: _selectedProduct,
          onBid: _openBidSetup,
          onAccept: _acceptBid,
          onRefresh: _refresh,
          onCancelRequest: (reqId) async {
            await _api.cancelBidRequest(user.accessToken, reqId);
            await _refresh();
          },
        );
      case 2:
        return OrdersHistoryPage(
          bids: _bids,
          requests: _buyerRequests,
          focusedBidId: _focusedBidId,
          onReport: (bid) => _showReportDialog(context, bid.id),
          onRebid: (bid) async {
            ProductItem? product;
            for (final item in _products) {
              if (item.id == bid.productId) {
                product = item;
                break;
              }
            }
            try {
              product ??= ProductItem.fromJson(
                await _api.getMap(
                  '/products/${bid.productId}',
                  user.accessToken,
                ),
              );
              await _openBidSetup(product, initialQuantity: bid.quantity);
            } catch (e) {
              if (mounted)
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Could not load this product: $e')),
                );
            }
          },
        );
      case 3:
        return CartPage(
          cart: _cart,
          products: _products,
          onBid: (product, quantity) =>
              _openBidSetup(product, initialQuantity: quantity),
          onAdd: _addCart,
          onRemove: _removeCartItem,
          onContinue: () => setState(() => _tab = 0),
        );
      case 4:
        return NotificationsPage(
          notifications: _notifications,
          onTapNotification: _handleNotificationTap,
        );
      case 6:
        return ReportsPage(
          reports: _reports,
          onExport: () => _showExport('reports'),
          userRole: 'buyer',
          currentUserId: user.id,
          selectedDetails: _selectedReportDetails,
          messages: _reportMessages,
          messageController: _reportMessageController,
          recipientGroup: _reportRecipientGroup,
          onDetails: _fetchReportDetails,
          onCloseDetails: () => setState(() => _selectedReportDetails = null),
          onSendMessage: _sendReportMessage,
          onRecipientGroupChanged: (val) =>
              setState(() => _reportRecipientGroup = val),
          onRequestClosure: _requestReportClosure,
        );
      default:
        return ProfileSettingsPage(
          user: user,
          reports: _reports,
          onSave: _updateProfile,
          onDeleteAccount: _confirmDeleteOwnAccount,
        );
    }
  }

  Widget _dealerPage(SessionUser user) {
    final page = _buildDealerPage(user);
    if (!_dealerSubscribed && !_dismissSubscriptionBanner) {
      return Column(
        children: [
          Container(
            decoration: const BoxDecoration(
              color: Color(0xFFFFF7ED),
              border: Border(bottom: BorderSide(color: Color(0xFFFED7AA))),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  color: Color(0xFFEA580C),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Subscription Required',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Color(0xFFC2410C),
                        ),
                      ),
                      Text(
                        'Subscribe to receive bid requests in your service area — ₹999/month',
                        style: TextStyle(
                          color: Color(0xFF9A3412),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFEA580C),
                    foregroundColor: Colors.white,
                  ),
                  onPressed: _subscribeDealer,
                  child: const Text('Subscribe Now'),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFFEA580C)),
                  onPressed: () {
                    setState(() {
                      _dismissSubscriptionBanner = true;
                    });
                  },
                ),
              ],
            ),
          ),
          Expanded(child: page),
        ],
      );
    }
    return page;
  }

  Widget _buildDealerPage(SessionUser user) {
    switch (_tab) {
      case 0:
        return DashboardPage(
          title: 'Dealer Dashboard',
          subtitle:
              'Live overview of requests, bids, wins, subscription, and account status.',
          dashboard: _dashboard,
          notifications: _notifications,
          status: user.status,
          extra: [
            DealerRequestsPanel(
              requests: _dealerRequests,
              onBid: _submitDealerBid,
            ),
          ],
        );
      case 1:
        return IncomingRequestsPage(
          requests: _dealerRequests,
          onBid: _submitDealerBid,
        );
      case 2:
        return DealerBidSubmissionPage(
          requests: _dealerRequests,
          bids: _bids,
          onBid: _submitDealerBid,
        );
      case 3:
        return DealerBidHistoryPage(
          bids: _bids.where((bid) => bid.isMine).toList(),
          focusedBidId: _focusedBidId,
          onPay: _payBid,
          onReport: (bid) => _showReportDialog(context, bid.id),
          onExport: () => _showExport('bids'),
          onWithdraw: _withdrawBid,
        );
      case 4:
        return BusinessProfilePage(
          user: user,
          onDeleteAccount: _confirmDeleteOwnAccount,
          subscribed: _dealerSubscribed,
        );
      case 5:
        return NotificationsPage(
          notifications: _notifications,
          onTapNotification: _handleNotificationTap,
        );
      default:
        return ReportsPage(
          reports: _reports,
          onExport: () => _showExport('reports'),
          userRole: 'dealer',
          currentUserId: user.id,
          selectedDetails: _selectedReportDetails,
          messages: _reportMessages,
          messageController: _reportMessageController,
          recipientGroup: _reportRecipientGroup,
          onDetails: _fetchReportDetails,
          onCloseDetails: () => setState(() => _selectedReportDetails = null),
          onSendMessage: _sendReportMessage,
          onRecipientGroupChanged: (val) =>
              setState(() => _reportRecipientGroup = val),
          onRequestClosure: _requestReportClosure,
        );
    }
  }

  Future<void> _createProduct() async {
    final user = _user;
    if (user == null) return;
    final specs = <String, String>{};
    for (final field in _specs) {
      if (field.name.text.trim().isNotEmpty) {
        specs[field.name.text.trim()] = field.value.text.trim();
      }
    }
    await _api.createProduct(
      user.accessToken,
      ProductDraft(
        name: _productName.text.trim(),
        category: _category.text.trim(),
        brand: _brand.text.trim(),
        model: _model.text.trim(),
        priceMin: double.tryParse(_priceMin.text.trim()) ?? 0,
        priceMax: double.tryParse(_priceMax.text.trim()) ?? 0,
        location: _location.text.trim(),
        specifications: specs,
      ),
    );
    _productName.clear();
    _brand.clear();
    _model.clear();
    _priceMin.clear();
    _priceMax.clear();
    await _refresh();
  }

  Future<void> _updateProduct(String id, ProductDraft draft) async {
    final user = _user;
    if (user == null) return;
    await _api.updateProduct(user.accessToken, id, draft);
    await _refresh();
  }

  Future<void> _deleteProduct(String id) async {
    final user = _user;
    if (user == null) return;
    await _api.deleteProduct(user.accessToken, id);
    await _refresh();
  }

  Future<void> _addCart(ProductItem product) async {
    final user = _user;
    if (user == null) return;
    await _api.addCartItem(user.accessToken, product.id, 1);
    await _refresh();
  }

  Future<bool> _startBid(
    ProductItem product, {
    int quantity = 1,
    String? locationId,
    bool skipFlaggedDealers = true,
    String notes = '',
    int expiryMinutes = 1440,
  }) async {
    final user = _user;
    if (user == null) return false;
    try {
      await _api.startBid(
        user.accessToken,
        product.id,
        quantity: quantity,
        locationId: locationId,
        skipFlaggedDealers: skipFlaggedDealers,
        notes: notes,
        expiryMinutes: expiryMinutes,
      );
      setState(() {
        _selectedProduct = product;
        _tab = 1;
      });
      await _refresh();
      return true;
    } catch (e) {
      if (mounted) {
        showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Bid Issue'),
            content: Text(
              e
                  .toString()
                  .replaceAll('Exception: ', '')
                  .replaceAll('HttpException: ', ''),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }
    return false;
  }

  Future<void> _removeCartItem(String itemId) async {
    final user = _user;
    if (user == null) return;
    await _api.removeCartItem(user.accessToken, itemId);
    await _refresh();
  }

  Future<void> _acceptBid(BidRecord bid) async {
    final user = _user;
    if (user == null) return;
    await _api.acceptBid(user.accessToken, bid.id);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Accepted bid for ${bid.product}')),
      );
    }
    await _refresh();
  }

  Future<void> _payBid(BidRecord bid) async {
    final user = _user;
    if (user == null) return;
    try {
      await _api.payBid(user.accessToken, bid.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Mock commission payment of ${money(bid.commission)} completed successfully.',
            ),
          ),
        );
      }
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Payment failed: $e')));
      }
    }
  }

  Future<void> _subscribeDealer() async {
    final user = _user;
    if (user == null || _offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.activateDealerSubscription(user.accessToken);
      setState(() {
        _dealerSubscribed = true;
      });
      await _refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Subscription activated successfully! Welcome to Turacoz Bid Tool.',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Subscription failed: $e')));
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _withdrawBid(BidRecord bid) async {
    final user = _user;
    if (user == null) return;
    try {
      await _api.withdrawBid(user.accessToken, bid.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Bid successfully withdrawn.')),
        );
      }
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Withdrawal failed: $e')));
      }
    }
  }

  Future<void> _submitReport(
    String bidId,
    String reason,
    String description,
  ) async {
    final user = _user;
    if (user == null) return;
    try {
      final reportId = await _api.createReport(
        user.accessToken,
        bidId,
        reason,
        description,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Dispute report submitted successfully! Admin will moderate.',
            ),
          ),
        );
      }
      await _refresh();
      if (reportId.isNotEmpty) {
        await _fetchReportDetails(reportId);
        setState(() {
          _tab = user.role == UserRole.dealer ? 6 : 7;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to submit report: $e')));
      }
    }
  }

  void _showReportDialog(BuildContext context, String bidId) {
    final reasonController = TextEditingController();
    final descController = TextEditingController();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.report_problem, color: Colors.red),
            SizedBox(width: 8),
            Text('File Dispute / Report'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reason for Dispute',
                hintText: 'e.g. Delayed Delivery / Incorrect Specs',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: descController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Detailed Description',
                hintText: 'Provide details about the issue...',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final reason = reasonController.text.trim();
              final desc = descController.text.trim();
              if (reason.isEmpty) return;
              Navigator.pop(ctx);
              _submitReport(bidId, reason, desc);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Submit Dispute'),
          ),
        ],
      ),
    );
  }

  void _updateProfile(SessionUser updated) {
    if (!mounted) return;
    setState(() => _user = updated);
    _refresh();
  }

  void _selectProduct(ProductItem product) {
    setState(() {
      _selectedProduct = product;
      _tab = 1;
    });
  }

  void _selectBuyerCategory(String category) {
    setState(() {
      _buyerCategory = category;
      _tab = 1;
      _search.text = category;
    });
    _refresh();
  }

  void _clearBuyerFilters() {
    setState(() {
      _buyerCategory = null;
      _sortMode = 'Newest';
      _filterBrand.clear();
      _filterMinPrice.clear();
      _filterMaxPrice.clear();
      _filterLocation.clear();
      _search.clear();
    });
    _refresh();
  }

  Future<void> _openBidSetup(
    ProductItem product, {
    int initialQuantity = 1,
  }) async {
    final quantity = TextEditingController(text: initialQuantity.toString());
    final notes = TextEditingController();
    var skipFlagged = true;
    var loadingLocations = true;
    var savedLocations = <Map<String, dynamic>>[];
    String? selectedSavedLocationId;
    final bidRules = Map<String, dynamic>.from(_settings['bid_rules'] ?? {});
    var expiryMinutes = (parseDouble(bidRules['expiry_hours'] ?? 24) * 60)
        .round();
    final minMinutes =
        (parseDouble(bidRules['min_time_hours'] ?? (1 / 60)) * 60).ceil();
    final maxMinutes = (parseDouble(bidRules['max_time_hours'] ?? 72) * 60)
        .floor();
    final expiryOptions =
        {expiryMinutes, 1, 30, 60, 120, 180, 240, 720, 1440, 2880, 4320}
            .where((value) => value >= minMinutes && value <= maxMinutes)
            .toList()
          ..sort();
    var submitting = false;
    try {
      final user = _user;
      if (user != null) {
        savedLocations = await _api.buyerLocations(user.accessToken);
        if (savedLocations.isNotEmpty) {
          final defaultLocation = savedLocations.firstWhere(
            (item) => item['is_default'] == true || item['is_default'] == 1,
            orElse: () => savedLocations.first,
          );
          selectedSavedLocationId = defaultLocation['location_id']?.toString();
        }
      }
    } finally {
      loadingLocations = false;
    }
    await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Start bid for ${product.name}'),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      InfoChip('Category', product.category),
                      InfoChip(
                        'Range',
                        '${money(product.priceMin)} - ${money(product.priceMax)}',
                      ),
                      InfoChip('Location', product.location),
                    ],
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: quantity,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Quantity'),
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: selectedSavedLocationId,
                    decoration: const InputDecoration(
                      labelText: 'Select Saved Location',
                    ),
                    items: savedLocations
                        .map(
                          (loc) => DropdownMenuItem<String>(
                            value: loc['location_id']?.toString(),
                            child: Text(
                              '${loc['label'] ?? 'Saved location'} - ${loc['area'] ?? ''}, ${loc['city'] ?? ''}',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: loadingLocations
                        ? null
                        : (value) => setDialogState(
                            () => selectedSavedLocationId = value,
                          ),
                  ),
                  if (savedLocations.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        'Add a saved map-pinned location in Profile before starting a bid.',
                        style: TextStyle(color: Colors.red[700]),
                      ),
                    ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<int>(
                    value: expiryMinutes,
                    decoration: const InputDecoration(
                      labelText: 'Bid Expiry Duration',
                    ),
                    items: expiryOptions
                        .map(
                          (value) => DropdownMenuItem<int>(
                            value: value,
                            child: Text('$value minutes'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        setDialogState(() => expiryMinutes = value);
                      }
                    },
                  ),
                  const SizedBox(height: 10),
                  SwitchListTile(
                    value: skipFlagged,
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Skip flagged dealers'),
                    onChanged: (value) =>
                        setDialogState(() => skipFlagged = value),
                  ),
                  TextField(
                    controller: notes,
                    minLines: 2,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Optional notes',
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton.icon(
              onPressed: selectedSavedLocationId == null || submitting
                  ? null
                  : () async {
                      final requestedQuantity = int.tryParse(
                        quantity.text.trim(),
                      );
                      if (requestedQuantity == null ||
                          requestedQuantity < 1 ||
                          requestedQuantity > 100000) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Quantity must be a whole number from 1 to 100000.',
                            ),
                          ),
                        );
                        return;
                      }
                      setDialogState(() => submitting = true);
                      final saved = await _startBid(
                        product,
                        quantity: requestedQuantity,
                        locationId: selectedSavedLocationId,
                        skipFlaggedDealers: skipFlagged,
                        notes: notes.text.trim(),
                        expiryMinutes: expiryMinutes,
                      );
                      if (context.mounted) {
                        if (saved) {
                          Navigator.pop(context, true);
                        } else {
                          setDialogState(() => submitting = false);
                        }
                      }
                    },
              icon: const Icon(Icons.bolt_outlined),
              label: const Text('Start Bid'),
            ),
          ],
        ),
      ),
    );
    quantity.dispose();
    notes.dispose();
  }

  void _openFilterDrawer() {
    showGeneralDialog<void>(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Filters',
      pageBuilder: (context, _, __) {
        return Align(
          alignment: Alignment.centerRight,
          child: Material(
            color: Colors.white,
            child: SizedBox(
              width: MediaQuery.of(
                context,
              ).size.width.clamp(320, 420).toDouble(),
              height: double.infinity,
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: ListView(
                    children: [
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Product filters',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          IconButton(
                            onPressed: () => Navigator.pop(context),
                            icon: const Icon(Icons.close),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _FilterField(label: 'Brand', controller: _filterBrand),
                      _FilterField(
                        label: 'Min price',
                        controller: _filterMinPrice,
                        number: true,
                      ),
                      _FilterField(
                        label: 'Max price',
                        controller: _filterMaxPrice,
                        number: true,
                      ),
                      _FilterField(
                        label: 'Location',
                        controller: _filterLocation,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: buyerCategories.map((category) {
                          final selected = _buyerCategory == category;
                          return FilterChip(
                            label: Text(category),
                            selected: selected,
                            onSelected: (_) => setState(
                              () => _buyerCategory = selected ? null : category,
                            ),
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Electronics filters',
                        style: TextStyle(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final label in [
                            'RAM',
                            'Storage',
                            'Processor',
                            'Screen size',
                            'Refresh rate',
                            'Battery',
                            'OS',
                            'Connectivity',
                            'Warranty',
                            'Delivery time',
                            'Service radius',
                          ])
                            ActionChip(
                              label: Text(label),
                              onPressed: () => setState(() {
                                _search.text = label;
                              }),
                            ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _clearBuyerFilters,
                              child: const Text('Clear Filters'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: FilledButton(
                              onPressed: () {
                                setState(() {});
                                Navigator.pop(context);
                              },
                              child: const Text('Apply'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  List<ProductItem> _filteredBuyerProducts() {
    Iterable<ProductItem> items = _products;
    final query = _search.text.trim().toLowerCase();
    final category = _buyerCategory?.toLowerCase();
    final brand = _filterBrand.text.trim().toLowerCase();
    final location = _filterLocation.text.trim().toLowerCase();
    final minPrice = double.tryParse(_filterMinPrice.text.trim());
    final maxPrice = double.tryParse(_filterMaxPrice.text.trim());
    if (query.isNotEmpty) {
      items = items.where((item) {
        final specs = item.specifications.entries
            .map((entry) => '${entry.key} ${entry.value}')
            .join(' ')
            .toLowerCase();
        return '${item.name} ${item.brand} ${item.model} ${item.category} ${item.location} $specs'
            .toLowerCase()
            .contains(query);
      });
    }
    if (category != null && category.isNotEmpty) {
      items = items.where(
        (item) =>
            item.category.toLowerCase().contains(category) ||
            item.name.toLowerCase().contains(category),
      );
    }
    if (brand.isNotEmpty) {
      items = items.where((item) => item.brand.toLowerCase().contains(brand));
    }
    if (location.isNotEmpty) {
      items = items.where(
        (item) => item.location.toLowerCase().contains(location),
      );
    }
    if (minPrice != null) {
      items = items.where((item) => item.priceMax >= minPrice);
    }
    if (maxPrice != null) {
      items = items.where((item) => item.priceMin <= maxPrice);
    }
    final sorted = items.toList();
    switch (_sortMode) {
      case 'Price Low':
        sorted.sort((a, b) => a.priceMin.compareTo(b.priceMin));
      case 'Price High':
        sorted.sort((a, b) => b.priceMax.compareTo(a.priceMax));
      case 'A-Z':
        sorted.sort((a, b) => a.name.compareTo(b.name));
      default:
        break;
    }
    return sorted;
  }

  Future<void> _submitDealerBid(String requestId, {BidRecord? editBid}) async {
    final user = _user;
    if (user == null) return;

    final amountController = TextEditingController(
      text: editBid != null ? editBid.amount.toString() : '',
    );
    final discountController = TextEditingController(
      text: editBid != null ? editBid.discountAmount.toString() : '',
    );
    final warrantyController = TextEditingController(
      text: editBid != null ? editBid.warrantyText : '',
    );
    final deliveryController = TextEditingController(
      text: editBid != null ? '${editBid.deliveryTime}' : '',
    );
    bool installationIncluded = editBid?.installationIncluded ?? false;
    var submitting = false;
    final giftsController = TextEditingController(
      text: editBid != null ? editBid.freeGifts : '',
    );
    final servicesController = TextEditingController(
      text: editBid != null ? editBid.extraServices : '',
    );
    final notesController = TextEditingController(
      text: editBid != null ? editBid.notes : '',
    );

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: Text(
                editBid != null ? 'Edit Bid Offer' : 'Submit Customized Bid',
              ),
              content: SizedBox(
                width: 460,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: amountController,
                        decoration: const InputDecoration(
                          labelText: 'Final total for all units (Rs.)',
                          helperText:
                              'After discount, for the full request quantity.',
                          prefixText: 'Rs. ',
                        ),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: discountController,
                        decoration: const InputDecoration(
                          labelText: 'Savings already included (Rs.)',
                          prefixText: 'Rs. ',
                        ),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: warrantyController,
                        decoration: const InputDecoration(
                          labelText:
                              'Warranty Period (e.g., 2 Years Manufacturer)',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: deliveryController,
                        decoration: const InputDecoration(
                          labelText: 'Delivery Time (e.g., 24 hours, 3 days)',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: giftsController,
                        decoration: const InputDecoration(
                          labelText: 'Free Gifts / Bundles',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: servicesController,
                        decoration: const InputDecoration(
                          labelText: 'Extra Services / Value Adds',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: notesController,
                        decoration: const InputDecoration(
                          labelText: 'Dealer Notes',
                        ),
                        maxLines: 2,
                      ),
                      const SizedBox(height: 12),
                      SwitchListTile(
                        title: const Text('Installation Included'),
                        value: installationIncluded,
                        onChanged: (val) =>
                            setState(() => installationIncluded = val),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: submitting
                      ? null
                      : () async {
                          final amt = double.tryParse(
                            amountController.text.trim(),
                          );
                          final discount =
                              discountController.text.trim().isEmpty
                              ? 0.0
                              : double.tryParse(discountController.text.trim());
                          if (amt == null ||
                              !amt.isFinite ||
                              amt <= 0 ||
                              discount == null ||
                              !discount.isFinite ||
                              discount < 0) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Please enter a valid bid amount',
                                ),
                              ),
                            );
                            return;
                          }
                          setState(() => submitting = true);
                          try {
                            await _api.submitDealerBid(
                              user.accessToken,
                              requestId: requestId,
                              amount: amt,
                              discountAmount: discount,
                              warrantyText: warrantyController.text.trim(),
                              deliveryTime: deliveryController.text.trim(),
                              installationIncluded: installationIncluded,
                              freeGifts: giftsController.text.trim(),
                              extraServices: servicesController.text.trim(),
                              notes: notesController.text.trim(),
                            );
                            if (!context.mounted) return;
                            Navigator.pop(context);
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              const SnackBar(
                                content: Text('Bid submitted successfully!'),
                              ),
                            );
                          } catch (e) {
                            if (!context.mounted) return;
                            setState(() => submitting = false);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Failed to submit bid: $e'),
                              ),
                            );
                          }
                        },
                  child: const Text('Submit Bid'),
                ),
              ],
            );
          },
        );
      },
    );
    await _refresh();
  }

  Future<void> _setUserStatus(String userId, String status) async {
    final user = _user;
    if (user == null) return;
    await _api.setUserStatus(user.accessToken, userId, status);
    await _refresh();
  }

  Future<void> _setPaymentStatus(String commissionId, String status) async {
    final user = _user;
    if (user == null) return;
    await _api.setPaymentStatus(user.accessToken, commissionId, status);
    await _refresh();
  }

  void _confirmDeleteOwnAccount() {
    final user = _user;
    if (user == null) return;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Account?'),
        content: Text(
          'This removes access for ${user.name} and closes active requests or offers. Existing bid and payment history is retained.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () async {
              Navigator.pop(ctx);
              await _api.deleteOwnAccount(user.accessToken);
              await _clearSavedSession();
              _disconnectWebSocket();
              if (mounted) {
                setState(() {
                  _user = null;
                  _tab = 0;
                  _error = null;
                });
              }
            },
            child: const Text('Delete Permanently'),
          ),
        ],
      ),
    );
  }

  void _onMetricClick(String key) {
    setState(() {
      _showRevenueBreakdown = false;
      if (key == 'dealers') {
        _tab = 1;
        _dealerStatusFilter = null;
        _dealerSearchController.clear();
      } else if (key == 'buyers') {
        _tab = 2;
        _buyerSearchController.clear();
      } else if (key == 'products') {
        _tab = 3;
        _productSearchController.clear();
      } else if (key == 'completed_bids') {
        _tab = 4;
        _bidStatusFilter = 'Completed';
        _bidCommissionFilter = null;
        _bidSearchController.clear();
      } else if (key == 'pending_reports') {
        _tab = 5;
        _reportStatusFilter = 'Pending';
        _reportSearchController.clear();
      } else if (key == 'revenue') {
        _tab = 4;
        _bidStatusFilter = 'Completed';
        _bidCommissionFilter = null;
        _showRevenueBreakdown = true;
      } else if (key == 'commission_due') {
        _tab = 4;
        _bidStatusFilter = null;
        _bidCommissionFilter = 'pending';
      } else if (key == 'held_dealers') {
        _tab = 1;
        _dealerStatusFilter = 'held';
      } else if (key == 'banned_dealers') {
        _tab = 1;
        _dealerStatusFilter = 'banned';
      }
    });
    _refresh();
  }

  Future<void> _fetchDealerDetails(String id) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      final res = await _api.getMap(
        '/admin/dealers/$id/details',
        _user!.accessToken,
      );
      setState(() {
        _selectedDealerId = id;
        _selectedDealerDetails = res;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load dealer details: $e')),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _fetchBuyerDetails(String id) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      final res = await _api.getMap(
        '/admin/buyers/$id/details',
        _user!.accessToken,
      );
      setState(() {
        _selectedBuyerId = id;
        _selectedBuyerDetails = res;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load buyer details: $e')),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _fetchReportDetails(String id, {bool silent = false}) async {
    if (_offlinePreview) return;
    final activeUser = _user;
    if (activeUser == null) return;
    if (!silent) setState(() => _loading = true);
    try {
      final report = _reports.firstWhere(
        (r) => r['id'] == id,
        orElse: () => <String, dynamic>{},
      );
      final detail = report.isNotEmpty
          ? report
          : await _api.report(activeUser.accessToken, id);
      final msgs = await _api.reportMessages(activeUser.accessToken, id);
      if (!mounted || _user?.accessToken != activeUser.accessToken) return;
      setState(() {
        final sameReport = _selectedReportId == id;
        _selectedReportId = id;
        _selectedReportDetails = detail;
        _reportMessages = mergeBidMessages(
          sameReport ? _reportMessages : [],
          msgs,
        );
      });
    } catch (e) {
      if (!mounted || _user?.accessToken != activeUser.accessToken) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load report messages: $e')),
      );
    } finally {
      if (!silent && mounted && _user?.accessToken == activeUser.accessToken)
        setState(() => _loading = false);
    }
  }

  Future<void> _sendReportMessage() async {
    final id = _selectedReportId;
    if (id == null || _reportMessageController.text.trim().isEmpty) return;
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.sendReportMessage(
        _user!.accessToken,
        id,
        _reportRecipientGroup,
        _reportMessageController.text.trim(),
      );
      _reportMessageController.clear();
      await _fetchReportDetails(id);
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to send message: $e')));
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _updateReportStatus(
    String reportId,
    String status,
    String note,
  ) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.updateReportStatus(_user!.accessToken, reportId, status, note);
      await _refresh();
      if (_selectedReportId == reportId) {
        await _fetchReportDetails(reportId);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Report status updated to $status.')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update report status: $e')),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _saveSetting(String key, Map<String, dynamic> value) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.saveSetting(_user!.accessToken, key, value);
      await _refresh();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Setting saved successfully!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to save setting: $e')));
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _requestReportClosure(String reportId, String reason) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.requestReportClosure(_user!.accessToken, reportId, reason);
      await _refresh();
      await _fetchReportDetails(reportId);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Report cancelled.')));
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to cancel report: $e')));
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _decideReportClosure(
    String reportId,
    String status,
    String note,
  ) async {
    if (_offlinePreview) return;
    setState(() => _loading = true);
    try {
      await _api.decideReportClosure(
        _user!.accessToken,
        reportId,
        status,
        note,
      );
      await _refresh();
      await _fetchReportDetails(reportId);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Closure request $status.')));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update closure request: $e')),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _showExport(String kind) async {
    final user = _user;
    if (user == null) return;
    try {
      final contents = await _api.exportCsv(user.accessToken, kind);
      final date = DateTime.now().toIso8601String().substring(0, 10);
      final filename = 'turacoz-$kind-$date.csv';
      final downloaded = await downloadCsvFile(filename, contents);
      if (!downloaded) {
        await Clipboard.setData(ClipboardData(text: contents));
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              downloaded ? 'CSV downloaded.' : 'CSV copied to the clipboard.',
            ),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('CSV export failed: $error')));
      }
    }
  }
}

class LoginPage extends StatelessWidget {
  const LoginPage({
    super.key,
    required this.username,
    required this.password,
    required this.loading,
    required this.error,
    required this.directAdmin,
    required this.onLogin,
    required this.onRegisterPressed,
    required this.onFill,
  });

  final TextEditingController username;
  final TextEditingController password;
  final bool loading;
  final String? error;
  final bool directAdmin;
  final VoidCallback onLogin;
  final VoidCallback onRegisterPressed;
  final void Function(String username, String password) onFill;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(22),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    directAdmin
                        ? Icons.admin_panel_settings_outlined
                        : Icons.hub_outlined,
                    size: 46,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    directAdmin ? 'Admin Login' : 'Turacoz Bid Tool Login',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'One Flutter app for Web and Android. Role decides the dashboard.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    controller: username,
                    decoration: const InputDecoration(
                      labelText: 'Username',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: password,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Password',
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                    onSubmitted: (_) => onLogin(),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 10),
                    Text(error!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: loading ? null : onLogin,
                      icon: loading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.login),
                      label: const Text('Sign in'),
                    ),
                  ),
                  if (!directAdmin) ...[
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: onRegisterPressed,
                      child: const Text('Need an account? Register here'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class RegisterPage extends StatefulWidget {
  const RegisterPage({
    super.key,
    required this.loading,
    required this.onRegister,
    required this.onCancel,
  });

  final bool loading;
  final Future<void> Function(
    String name,
    String username,
    String password,
    String role,
  )
  onRegister;
  final VoidCallback onCancel;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _password = TextEditingController();
  String _role = 'buyer';
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty ||
        _username.text.trim().isEmpty ||
        _password.text.isEmpty) {
      setState(() => _error = 'All fields are required');
      return;
    }
    setState(() => _error = null);
    try {
      await widget.onRegister(
        _name.text.trim(),
        _username.text.trim(),
        _password.text,
        _role,
      );
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.person_add_outlined,
                      size: 46,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Create Account',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Register to join the Turacoz Bid Tool bidding marketplace.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 18),
                    TextField(
                      controller: _name,
                      decoration: const InputDecoration(
                        labelText: 'Full Name',
                        prefixIcon: Icon(Icons.badge_outlined),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _username,
                      decoration: const InputDecoration(
                        labelText: 'Username (Email)',
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _password,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Password',
                        prefixIcon: Icon(Icons.lock_outline),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _role,
                      decoration: const InputDecoration(
                        labelText: 'Role',
                        prefixIcon: Icon(Icons.assignment_ind_outlined),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'buyer', child: Text('Buyer')),
                        DropdownMenuItem(
                          value: 'dealer',
                          child: Text('Dealer'),
                        ),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _role = val);
                      },
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        _error!,
                        style: const TextStyle(color: Colors.red),
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: widget.loading ? null : _submit,
                        child: widget.loading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Text('Register'),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextButton(
                      onPressed: widget.loading ? null : widget.onCancel,
                      child: const Text('Back to Login'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class PageScaffold extends StatelessWidget {
  const PageScaffold({super.key, required this.child, this.scrollable = true});
  final Widget child;
  final bool scrollable;
  @override
  Widget build(BuildContext context) => scrollable
      ? ListView(padding: const EdgeInsets.all(16), children: [child])
      : Padding(
          padding: const EdgeInsets.all(16),
          child: SizedBox.expand(child: child),
        );
}

class _BuyerDrawer extends StatelessWidget {
  const _BuyerDrawer({
    required this.nav,
    required this.indexes,
    required this.selectedTab,
    required this.onSelect,
    required this.onLogout,
  });

  final List<NavItem> nav;
  final List<int> indexes;
  final int selectedTab;
  final ValueChanged<int> onSelect;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            ListTile(
              leading: Icon(
                Icons.local_mall_outlined,
                color: Theme.of(context).colorScheme.primary,
              ),
              title: const Text(
                'Turacoz Bid Tool',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
              subtitle: const Text('Buyer marketplace'),
            ),
            const Divider(),
            Expanded(
              child: ListView.builder(
                itemCount: nav.length,
                itemBuilder: (context, index) {
                  final item = nav[index];
                  final tab = indexes[index];
                  return ListTile(
                    selected: selectedTab == tab,
                    leading: Icon(item.icon),
                    title: Text(item.label),
                    onTap: () {
                      Navigator.pop(context);
                      onSelect(tab);
                    },
                  );
                },
              ),
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('Logout'),
              onTap: onLogout,
            ),
          ],
        ),
      ),
    );
  }
}

class BuyerHomePage extends StatefulWidget {
  const BuyerHomePage({
    super.key,
    required this.token,
    required this.api,
    required this.onCart,
    required this.onBid,
    required this.onSelect,
    required this.bids,
  });

  final String token;
  final ApiClient api;
  final Future<void> Function(ProductItem product) onCart;
  final Future<void> Function(ProductItem product) onBid;
  final ValueChanged<ProductItem> onSelect;
  final List<BidRecord> bids;

  @override
  State<BuyerHomePage> createState() => _BuyerHomePageState();
}

class _BuyerHomePageState extends State<BuyerHomePage> {
  final _search = TextEditingController();
  final _minPrice = TextEditingController();
  final _maxPrice = TextEditingController();

  List<ProductItem> _allItems = [];
  bool _loading = false;

  final Set<String> _selectedCategories = {};
  final Set<String> _selectedSubcategories = {};
  final Set<String> _selectedBrands = {};
  bool _onlyAvailable = false;
  String _sortMode = 'Newest';

  @override
  void initState() {
    super.initState();
    _fetchProducts();
  }

  Future<void> _fetchProducts() async {
    if (!mounted) return;
    setState(() => _loading = true);
    try {
      final list = await widget.api.products(
        widget.token,
        query: _search.text.trim(),
      );
      if (mounted) {
        setState(() {
          _allItems = list;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _clearFilters() {
    setState(() {
      _selectedCategories.clear();
      _selectedSubcategories.clear();
      _selectedBrands.clear();
      _minPrice.clear();
      _maxPrice.clear();
      _onlyAvailable = false;
    });
  }

  List<ProductItem> _getFilteredProducts() {
    Iterable<ProductItem> items = _allItems;

    if (_selectedCategories.isNotEmpty) {
      items = items.where(
        (item) => _selectedCategories.contains(item.category),
      );
    }
    if (_selectedSubcategories.isNotEmpty) {
      items = items.where(
        (item) => _selectedSubcategories.contains(item.subcategory),
      );
    }
    if (_selectedBrands.isNotEmpty) {
      items = items.where((item) => _selectedBrands.contains(item.brand));
    }

    final minVal = double.tryParse(_minPrice.text);
    if (minVal != null) {
      items = items.where((item) => item.priceMax >= minVal);
    }
    final maxVal = double.tryParse(_maxPrice.text);
    if (maxVal != null) {
      items = items.where((item) => item.priceMin <= maxVal);
    }

    if (_onlyAvailable) {
      items = items.where((item) => item.status == 'active');
    }

    final list = items.toList();
    if (_sortMode == 'Price Low') {
      list.sort((a, b) => a.priceMin.compareTo(b.priceMin));
    } else if (_sortMode == 'Price High') {
      list.sort((a, b) => b.priceMax.compareTo(a.priceMax));
    } else if (_sortMode == 'A-Z') {
      list.sort((a, b) => a.name.compareTo(b.name));
    } else {
      list.sort((a, b) => b.id.compareTo(a.id));
    }
    return list;
  }

  List<ProductItem> _getRecommendations() {
    final wonCategories = widget.bids
        .where((b) => b.status == 'won')
        .map((b) {
          final found = _allItems.firstWhere(
            (p) => p.name == b.product,
            orElse: () => const ProductItem(
              id: '',
              name: '',
              category: 'None',
              subcategory: '',
              brand: '',
              model: '',
              priceMin: 0,
              priceMax: 0,
              location: '',
              status: '',
              specifications: {},
            ),
          );
          return found.category;
        })
        .where((cat) => cat != 'None')
        .toSet();

    if (wonCategories.isNotEmpty) {
      final recs = _allItems
          .where((p) => wonCategories.contains(p.category))
          .toList();
      if (recs.isNotEmpty) return recs;
    }

    final list = [..._allItems]..shuffle();
    return list.take(4).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _getFilteredProducts();
    final recommendations = _getRecommendations();

    final allSubcategories = _selectedCategories.isEmpty
        ? <String>[]
        : _allItems
              .where((p) => _selectedCategories.contains(p.category))
              .map((p) => p.subcategory)
              .where((s) => s.isNotEmpty)
              .toSet()
              .toList();

    final allBrands = _selectedSubcategories.isNotEmpty
        ? _allItems
              .where((p) => _selectedSubcategories.contains(p.subcategory))
              .map((p) => p.brand)
              .where((b) => b.isNotEmpty)
              .toSet()
              .toList()
        : (_selectedCategories.isNotEmpty
              ? _allItems
                    .where((p) => _selectedCategories.contains(p.category))
                    .map((p) => p.brand)
                    .where((b) => b.isNotEmpty)
                    .toSet()
                    .toList()
              : <String>[]);

    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1000;

    Widget filtersWidget() {
      return Scrollbar(
        child: ListView(
          shrinkWrap: true,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Filters',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                TextButton(
                  onPressed: _clearFilters,
                  child: const Text('Reset'),
                ),
              ],
            ),
            const Divider(),

            const Text(
              'Price Range',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _minPrice,
                    decoration: const InputDecoration(labelText: 'Min Rs'),
                    keyboardType: TextInputType.number,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _maxPrice,
                    decoration: const InputDecoration(labelText: 'Max Rs'),
                    keyboardType: TextInputType.number,
                    onChanged: (_) => setState(() {}),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            const Text(
              'Categories',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            ...buyerCategories.map(
              (cat) => CheckboxListTile(
                title: Text(cat),
                value: _selectedCategories.contains(cat),
                dense: true,
                contentPadding: EdgeInsets.zero,
                onChanged: (val) {
                  setState(() {
                    if (val == true) {
                      _selectedCategories.add(cat);
                    } else {
                      _selectedCategories.remove(cat);
                      _selectedSubcategories.clear();
                      _selectedBrands.clear();
                    }
                  });
                },
              ),
            ),
            const SizedBox(height: 16),

            if (allSubcategories.isNotEmpty) ...[
              const Text(
                'Subcategories',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              ...allSubcategories.map(
                (sub) => CheckboxListTile(
                  title: Text(sub),
                  value: _selectedSubcategories.contains(sub),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  onChanged: (val) {
                    setState(() {
                      if (val == true) {
                        _selectedSubcategories.add(sub);
                      } else {
                        _selectedSubcategories.remove(sub);
                        _selectedBrands.clear();
                      }
                    });
                  },
                ),
              ),
              const SizedBox(height: 16),
            ],

            if (allBrands.isNotEmpty) ...[
              const Text(
                'Brands',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              ...allBrands.map(
                (brand) => CheckboxListTile(
                  title: Text(brand),
                  value: _selectedBrands.contains(brand),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  onChanged: (val) {
                    setState(() {
                      if (val == true) {
                        _selectedBrands.add(brand);
                      } else {
                        _selectedBrands.remove(brand);
                      }
                    });
                  },
                ),
              ),
              const SizedBox(height: 16),
            ],

            SwitchListTile(
              title: const Text(
                'Only Available',
                style: TextStyle(fontSize: 14),
              ),
              value: _onlyAvailable,
              contentPadding: EdgeInsets.zero,
              onChanged: (val) => setState(() => _onlyAvailable = val),
            ),
          ],
        ),
      );
    }

    return PageScaffold(
      scrollable: false,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _search,
                  decoration: const InputDecoration(
                    hintText: 'Search brand, model, specifications...',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onSubmitted: (_) => _fetchProducts(),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: _fetchProducts,
                child: const Text('Search'),
              ),
              if (!isDesktop) ...[
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.tune),
                  onPressed: () {
                    showModalBottomSheet<void>(
                      context: context,
                      builder: (context) {
                        return Padding(
                          padding: const EdgeInsets.all(16),
                          child: StatefulBuilder(
                            builder: (context, setModalState) {
                              return filtersWidget();
                            },
                          ),
                        );
                      },
                    );
                  },
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isDesktop)
                  Container(
                    width: 240,
                    margin: const EdgeInsets.only(right: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border.all(color: Colors.grey.shade200),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: filtersWidget(),
                  ),
                Expanded(
                  child: _loading
                      ? const Center(child: CircularProgressIndicator())
                      : Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: Row(
                                children: [
                                  Text(
                                    '${filtered.length} products found',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const Spacer(),
                                  const Text('Sort: '),
                                  DropdownButton<String>(
                                    value: _sortMode,
                                    items:
                                        const [
                                              'Newest',
                                              'Price Low',
                                              'Price High',
                                              'A-Z',
                                            ]
                                            .map(
                                              (s) => DropdownMenuItem(
                                                value: s,
                                                child: Text(s),
                                              ),
                                            )
                                            .toList(),
                                    onChanged: (val) {
                                      if (val != null)
                                        setState(() => _sortMode = val);
                                    },
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: ListView(
                                children: [
                                  ProductList(
                                    products: filtered,
                                    onCart: widget.onCart,
                                    onBid: widget.onBid,
                                    onSelect: widget.onSelect,
                                    grid: true,
                                  ),
                                  if (recommendations.isNotEmpty) ...[
                                    const Padding(
                                      padding: EdgeInsets.only(
                                        top: 24,
                                        bottom: 12,
                                      ),
                                      child: Text(
                                        'Recommended for You',
                                        style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                    ProductList(
                                      products: recommendations,
                                      onCart: widget.onCart,
                                      onBid: widget.onBid,
                                      onSelect: widget.onSelect,
                                      grid: true,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ],
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class CategoryStrip extends StatelessWidget {
  const CategoryStrip({
    super.key,
    required this.selected,
    required this.onCategory,
  });

  final String? selected;
  final ValueChanged<String> onCategory;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 42,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: buyerCategories.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final category = buyerCategories[index];
          return ChoiceChip(
            selected: selected == category,
            label: Text(category),
            onSelected: (_) => onCategory(category),
          );
        },
      ),
    );
  }
}

class DashboardPage extends StatelessWidget {
  const DashboardPage({
    super.key,
    required this.title,
    required this.subtitle,
    required this.dashboard,
    required this.notifications,
    this.extra = const [],
    this.status = 'active',
    this.onMetricClick,
  });

  final String title;
  final String subtitle;
  final Map<String, dynamic> dashboard;
  final List<AppNotification> notifications;
  final List<Widget> extra;
  final String status;
  final ValueChanged<String>? onMetricClick;

  @override
  Widget build(BuildContext context) {
    final metrics = Map<String, dynamic>.from(dashboard['metrics'] ?? {});
    final charts = Map<String, dynamic>.from(dashboard['charts'] ?? {});

    final revenueByMonth = List<Map<String, dynamic>>.from(
      charts['revenue_by_month'] ?? [],
    );
    final dealersByState = List<Map<String, dynamic>>.from(
      charts['dealers_by_state'] ?? [],
    );
    final dealersByCategory = List<Map<String, dynamic>>.from(
      charts['dealers_by_category'] ?? [],
    );
    final buyersByState = List<Map<String, dynamic>>.from(
      charts['buyers_by_state'] ?? [],
    );
    final productsByCategory = List<Map<String, dynamic>>.from(
      charts['products_by_category'] ?? [],
    );
    final bidSuccessRate = List<Map<String, dynamic>>.from(
      charts['bid_success_rate'] ?? [],
    );
    final topCategories = List<Map<String, dynamic>>.from(
      charts['top_categories'] ?? [],
    );
    final topCities = List<Map<String, dynamic>>.from(
      charts['top_cities'] ?? [],
    );
    final recentReports = List<Map<String, dynamic>>.from(
      charts['recent_reports'] ?? [],
    );

    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (['held', 'flagged', 'suspended', 'banned'].contains(status))
            WarningBanner(status: status),
          SectionHeader(
            title: title,
            subtitle: subtitle,
            icon: Icons.dashboard_outlined,
          ),
          const SizedBox(height: 12),
          ResponsiveMetricGrid(
            metrics: metrics.entries
                .map(
                  (entry) => MetricCard(
                    label: _title(entry.key),
                    value: _formatMetric(entry.value),
                    icon: _metricIcon(entry.key),
                    onTap: onMetricClick == null
                        ? null
                        : () => onMetricClick!(entry.key),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 20),
          if (charts.isNotEmpty) ...[
            const Text(
              'Platform Analytics Dashboard',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w900,
                color: Color(0xFF3B0764),
              ),
            ),
            const SizedBox(height: 12),
            LayoutBuilder(
              builder: (context, constraints) {
                final double width = constraints.maxWidth;
                final isWide = width >= 800;
                return Column(
                  children: [
                    if (revenueByMonth.isNotEmpty) ...[
                      BarChartWidget(
                        title: 'Revenue by Month (Commission Paid)',
                        data: revenueByMonth,
                      ),
                      const SizedBox(height: 12),
                    ],
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: ListComparisonChart(
                            title: 'Dealers by State',
                            data: dealersByState,
                          ),
                        ),
                        if (isWide) const SizedBox(width: 12),
                        if (isWide)
                          Expanded(
                            child: ListComparisonChart(
                              title: 'Dealers by Category',
                              data: dealersByCategory,
                            ),
                          ),
                      ],
                    ),
                    if (!isWide) const SizedBox(height: 12),
                    if (!isWide)
                      ListComparisonChart(
                        title: 'Dealers by Category',
                        data: dealersByCategory,
                      ),
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: ListComparisonChart(
                            title: 'Buyers by State',
                            data: buyersByState,
                          ),
                        ),
                        if (isWide) const SizedBox(width: 12),
                        if (isWide)
                          Expanded(
                            child: ListComparisonChart(
                              title: 'Products by Category',
                              data: productsByCategory,
                            ),
                          ),
                      ],
                    ),
                    if (!isWide) const SizedBox(height: 12),
                    if (!isWide)
                      ListComparisonChart(
                        title: 'Products by Category',
                        data: productsByCategory,
                      ),
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: ListComparisonChart(
                            title: 'Bid Success Rate (Status)',
                            data: bidSuccessRate,
                          ),
                        ),
                        if (isWide) const SizedBox(width: 12),
                        if (isWide)
                          Expanded(
                            child: ListComparisonChart(
                              title: 'Top Cities',
                              data: topCities,
                            ),
                          ),
                      ],
                    ),
                    if (!isWide) const SizedBox(height: 12),
                    if (!isWide)
                      ListComparisonChart(title: 'Top Cities', data: topCities),
                    const SizedBox(height: 12),
                    if (recentReports.isNotEmpty) ...[
                      DataPanel(
                        title: 'Recent Reports',
                        children: recentReports.map((row) {
                          return ListTile(
                            leading: const Icon(
                              Icons.report_problem_outlined,
                              color: Colors.red,
                            ),
                            title: Text(row['reason']?.toString() ?? ''),
                            subtitle: Text(
                              'Reporter: ${row['reporter']} | Reported: ${row['reported_party']}',
                            ),
                            trailing: StatusPill(
                              text: row['status']?.toString() ?? 'open',
                            ),
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 12),
                    ],
                  ],
                );
              },
            ),
          ],
        ],
      ),
    );
  }
}

class BarChartWidget extends StatelessWidget {
  const BarChartWidget({super.key, required this.title, required this.data});
  final String title;
  final List<Map<String, dynamic>> data;

  @override
  Widget build(BuildContext context) {
    double maxValue = 0;
    for (final item in data) {
      final val = parseDouble(item['value']);
      if (val > maxValue) maxValue = val;
    }
    if (maxValue == 0) maxValue = 1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: Color(0xFF3B0764),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 180,
              child: data.isEmpty
                  ? const Center(child: Text('No data available'))
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: data.map((item) {
                        final val = parseDouble(item['value']);
                        final heightFactor = val / maxValue;
                        return Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              Text(
                                val > 999 ? money(val) : val.toStringAsFixed(0),
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Container(
                                height: 110 * heightFactor,
                                width: 24,
                                decoration: BoxDecoration(
                                  color: Theme.of(context).colorScheme.primary,
                                  borderRadius: const BorderRadius.only(
                                    topLeft: Radius.circular(4),
                                    topRight: Radius.circular(4),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              FittedBox(
                                child: Text(
                                  item['label']?.toString() ?? '',
                                  style: const TextStyle(fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class ListComparisonChart extends StatelessWidget {
  const ListComparisonChart({
    super.key,
    required this.title,
    required this.data,
  });
  final String title;
  final List<Map<String, dynamic>> data;

  @override
  Widget build(BuildContext context) {
    double total = 0;
    double maxVal = 0;
    for (final item in data) {
      final val = parseDouble(item['value']);
      total += val;
      if (val > maxVal) maxVal = val;
    }
    if (total == 0) total = 1;
    if (maxVal == 0) maxVal = 1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: Color(0xFF3B0764),
              ),
            ),
            const SizedBox(height: 12),
            data.isEmpty
                ? const SizedBox(
                    height: 100,
                    child: Center(child: Text('No data available')),
                  )
                : Column(
                    children: data.map((item) {
                      final val = parseDouble(item['value']);
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            Expanded(
                              flex: 3,
                              child: Text(
                                item['label']?.toString() ?? '',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            Expanded(
                              flex: 5,
                              child: LinearProgressIndicator(
                                value: val / maxVal,
                                backgroundColor: const Color(0xFFEDE9FE),
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              '${val.toStringAsFixed(0)} (${(val / total * 100).round()}%)',
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ],
        ),
      ),
    );
  }
}

class QuickActions extends StatelessWidget {
  const QuickActions({super.key, required this.actions});
  final List<ActionSpec> actions;
  @override
  Widget build(BuildContext context) => DataPanel(
    title: 'Quick actions',
    children: [
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: actions
            .map(
              (item) => FilledButton.tonalIcon(
                onPressed: item.onPressed,
                icon: Icon(item.icon),
                label: Text(item.label),
              ),
            )
            .toList(),
      ),
    ],
  );
}

class ActionSpec {
  const ActionSpec(this.label, this.icon, this.onPressed);
  final String label;
  final IconData icon;
  final VoidCallback onPressed;
}

class AdminUsersPage extends StatefulWidget {
  const AdminUsersPage({
    super.key,
    required this.title,
    required this.rows,
    required this.role,
    required this.onStatus,
    required this.searchController,
    required this.onSearch,
    required this.onDetails,
    required this.selectedDetails,
    required this.onCloseDetails,
  });

  final String title;
  final List<Map<String, dynamic>> rows;
  final String role;
  final Future<void> Function(String userId, String status) onStatus;
  final TextEditingController searchController;
  final Future<void> Function() onSearch;
  final Future<void> Function(String id) onDetails;
  final Map<String, dynamic>? selectedDetails;
  final VoidCallback onCloseDetails;

  @override
  State<AdminUsersPage> createState() => _AdminUsersPageState();
}

class _AdminUsersPageState extends State<AdminUsersPage> {
  // Local filters
  String? _statusFilter;
  String? _stateFilter;
  String? _cityFilter;
  String? _categoryFilter;
  bool _showDrawer = false;

  void _clearFilters() {
    setState(() {
      _statusFilter = null;
      _stateFilter = null;
      _cityFilter = null;
      _categoryFilter = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    // 1. Apply local filters to rows
    final filteredRows = widget.rows.where((row) {
      if (_statusFilter != null &&
          row['status']?.toString().toLowerCase() !=
              _statusFilter!.toLowerCase()) {
        return false;
      }
      if (_stateFilter != null) {
        final stateStr = (row['state'] ?? row['states'] ?? '')
            .toString()
            .toLowerCase();
        if (!stateStr.contains(_stateFilter!.toLowerCase())) return false;
      }
      if (_cityFilter != null) {
        final cityStr = (row['city'] ?? row['cities'] ?? '')
            .toString()
            .toLowerCase();
        if (!cityStr.contains(_cityFilter!.toLowerCase())) return false;
      }
      if (_categoryFilter != null) {
        final catStr = (row['categories'] ?? row['category'] ?? '')
            .toString()
            .toLowerCase();
        if (!catStr.contains(_categoryFilter!.toLowerCase())) return false;
      }
      return true;
    }).toList();

    // Extract unique states and cities from live rows for dropdowns
    final states = widget.rows
        .map((r) => (r['state'] ?? r['states'] ?? '').toString())
        .where((s) => s.isNotEmpty)
        .toSet()
        .toList();
    final cities = widget.rows
        .map((r) => (r['city'] ?? r['cities'] ?? '').toString())
        .where((c) => c.isNotEmpty)
        .toSet()
        .toList();
    final categories = widget.rows
        .map((r) => (r['categories'] ?? r['category'] ?? '').toString())
        .where((c) => c.isNotEmpty)
        .toSet()
        .toList();

    // 2. Search Analytics Box
    Widget? analyticsBox;
    if (widget.searchController.text.isNotEmpty ||
        _stateFilter != null ||
        _cityFilter != null) {
      final activeLoc =
          _stateFilter ?? _cityFilter ?? widget.searchController.text;
      final totalMatch = filteredRows.length;
      final verifiedCount = filteredRows
          .where((r) => r['status'] == 'verified' || r['status'] == 'active')
          .length;
      final flaggedCount = filteredRows
          .where((r) => r['status'] == 'flagged')
          .length;
      final bannedCount = filteredRows
          .where((r) => r['status'] == 'banned')
          .length;
      final pendingCount = filteredRows
          .where((r) => r['status'] == 'pending')
          .length;

      // Category breakdown
      final Map<String, int> catCounts = {};
      for (final r in filteredRows) {
        final cats = (r['categories'] ?? r['category'] ?? '').toString().split(
          ',',
        );
        for (final c in cats) {
          final trimmed = c.trim();
          if (trimmed.isNotEmpty) {
            catCounts[trimmed] = (catCounts[trimmed] ?? 0) + 1;
          }
        }
      }

      // City breakdown for search terms like "Laptop" or status matching
      final Map<String, int> cityCounts = {};
      for (final r in filteredRows) {
        final city = (r['city'] ?? r['cities'] ?? '').toString();
        if (city.isNotEmpty) {
          cityCounts[city] = (cityCounts[city] ?? 0) + 1;
        }
      }

      analyticsBox = Card(
        color: const Color(0xFFF5F3FF),
        margin: const EdgeInsets.only(bottom: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFFE9D5FF)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Search Analytics: "$activeLoc"',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF3B0764),
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                children: [
                  Text(
                    'Total matching: $totalMatch',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(
                    'Verified: $verifiedCount',
                    style: const TextStyle(
                      color: Colors.green,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Flagged: $flaggedCount',
                    style: const TextStyle(
                      color: Colors.orange,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Banned: $bannedCount',
                    style: const TextStyle(
                      color: Colors.red,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Pending: $pendingCount',
                    style: const TextStyle(
                      color: Colors.blue,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              if (catCounts.isNotEmpty) ...[
                const SizedBox(height: 10),
                const Divider(),
                const Text(
                  'Categories:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 10,
                  children: catCounts.entries
                      .map(
                        (e) => Chip(
                          label: Text('${e.key}: ${e.value}'),
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        ),
                      )
                      .toList(),
                ),
              ],
              if (cityCounts.isNotEmpty && cityCounts.length > 1) ...[
                const SizedBox(height: 10),
                const Divider(),
                const Text(
                  'Cities:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 10,
                  children: cityCounts.entries
                      .map(
                        (e) => Chip(
                          label: Text('${e.key}: ${e.value}'),
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        ),
                      )
                      .toList(),
                ),
              ],
            ],
          ),
        ),
      );
    }

    return PageScaffold(
      scrollable: false,
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeader(
                title: widget.title,
                subtitle:
                    'Search, filter, audit, and moderate live registered ${widget.role} profiles.',
                icon: widget.role == 'dealer'
                    ? Icons.storefront_outlined
                    : Icons.people_alt_outlined,
              ),
              const SizedBox(height: 12),
              // Search & filter tools bar
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: widget.searchController,
                      decoration: InputDecoration(
                        prefixIcon: const Icon(Icons.search),
                        hintText: widget.role == 'dealer'
                            ? 'Search Name, Business, Phone, Category, State, District, Brand...'
                            : 'Search Name, ID, Phone, Email, Pincode...',
                      ),
                      onSubmitted: (_) => widget.onSearch(),
                    ),
                  ),
                  const SizedBox(width: 10),
                  FilledButton.icon(
                    onPressed: widget.onSearch,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Search'),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: () => setState(() => _showDrawer = !_showDrawer),
                    icon: const Icon(Icons.filter_list),
                    label: const Text('Filters'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (_showDrawer) _buildFiltersDrawer(states, cities, categories),
              if (analyticsBox != null) analyticsBox,
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${filteredRows.length} ${widget.role}s found',
                          style: const TextStyle(
                            fontWeight: FontWeight.w900,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Expanded(
                          child: filteredRows.isEmpty
                              ? const Center(
                                  child: Text('No matching records.'),
                                )
                              : ListView.builder(
                                  itemCount: filteredRows.length,
                                  itemBuilder: (context, index) {
                                    final row = filteredRows[index];
                                    final id = row['id']?.toString() ?? '';
                                    final name =
                                        row['business_name']
                                                ?.toString()
                                                .isNotEmpty ==
                                            true
                                        ? row['business_name'].toString()
                                        : row['full_name']?.toString() ?? '';
                                    final subtitleStr = widget.role == 'dealer'
                                        ? '${row['email'] ?? ''} | ${row['city'] ?? ''}, ${row['state'] ?? ''} | categories: ${row['categories'] ?? row['category'] ?? ''}'
                                        : '${row['email'] ?? ''} | Bids: ${row['bid_count'] ?? 0} | Purchases: ${row['purchase_count'] ?? 0}';
                                    return Card(
                                      margin: const EdgeInsets.only(bottom: 10),
                                      child: ListTile(
                                        onTap: () => widget.onDetails(id),
                                        title: Text(
                                          name,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        subtitle: Text(subtitleStr),
                                        leading: CircleAvatar(
                                          backgroundColor: const Color(
                                            0xFFF5F3FF,
                                          ),
                                          child: Icon(
                                            widget.role == 'dealer'
                                                ? Icons.storefront
                                                : Icons.person,
                                            color: Theme.of(
                                              context,
                                            ).colorScheme.primary,
                                          ),
                                        ),
                                        trailing: Wrap(
                                          spacing: 6,
                                          crossAxisAlignment:
                                              WrapCrossAlignment.center,
                                          children: [
                                            StatusPill(
                                              text:
                                                  row['status']?.toString() ??
                                                  'active',
                                            ),
                                            PopupMenuButton<String>(
                                              tooltip: 'Moderate Status',
                                              onSelected: (status) {
                                                if (status == 'deleted') {
                                                  _showDeleteConfirm(
                                                    context,
                                                    name,
                                                    id,
                                                  );
                                                } else {
                                                  widget.onStatus(id, status);
                                                }
                                              },
                                              itemBuilder: (_) =>
                                                  [
                                                        'verified',
                                                        'flagged',
                                                        'banned',
                                                        'deleted',
                                                      ]
                                                      .map(
                                                        (
                                                          status,
                                                        ) => PopupMenuItem(
                                                          value: status,
                                                          child: Text(
                                                            status
                                                                .toUpperCase(),
                                                          ),
                                                        ),
                                                      )
                                                      .toList(),
                                            ),
                                          ],
                                        ),
                                      ),
                                    );
                                  },
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
          if (widget.selectedDetails != null) _buildDetailsOverlay(),
        ],
      ),
    );
  }

  Widget _buildFiltersDrawer(
    List<String> states,
    List<String> cities,
    List<String> categories,
  ) {
    return Card(
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Filter Drawer',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Color(0xFF3B0764),
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 12,
              runSpacing: 10,
              children: [
                DropdownButton<String>(
                  hint: const Text('Status'),
                  value: _statusFilter,
                  onChanged: (val) => setState(() => _statusFilter = val),
                  items: ['verified', 'flagged', 'banned', 'pending', 'active']
                      .map(
                        (e) => DropdownMenuItem(
                          value: e,
                          child: Text(e.toUpperCase()),
                        ),
                      )
                      .toList(),
                ),
                if (states.isNotEmpty)
                  DropdownButton<String>(
                    hint: const Text('State'),
                    value: _stateFilter,
                    onChanged: (val) => setState(() => _stateFilter = val),
                    items: states
                        .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                        .toList(),
                  ),
                if (cities.isNotEmpty)
                  DropdownButton<String>(
                    hint: const Text('City'),
                    value: _cityFilter,
                    onChanged: (val) => setState(() => _cityFilter = val),
                    items: cities
                        .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                        .toList(),
                  ),
                if (categories.isNotEmpty)
                  DropdownButton<String>(
                    hint: const Text('Category'),
                    value: _categoryFilter,
                    onChanged: (val) => setState(() => _categoryFilter = val),
                    items: categories
                        .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                        .toList(),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _clearFilters,
                  child: const Text('Reset Filters'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => setState(() => _showDrawer = false),
                  child: const Text('Close'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showDeleteConfirm(BuildContext context, String name, String id) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Account?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'This action cannot be undone and will permanently restrict access.',
              style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red),
            ),
            const SizedBox(height: 12),
            Text('Account Name: $name'),
            Text('Account ID: $id'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              widget.onStatus(id, 'deleted');
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailsOverlay() {
    final details = widget.selectedDetails!;
    final basic = Map<String, dynamic>.from(details['basic'] ?? {});
    final isDealer = widget.role == 'dealer';

    return Container(
      color: Colors.white,
      width: double.infinity,
      height: double.infinity,
      child: Column(
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFFF5F3FF),
              border: Border(bottom: BorderSide(color: Color(0xFFE9D5FF))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isDealer
                            ? (basic['business_name']?.toString() ??
                                  'Dealer Profile')
                            : (basic['full_name']?.toString() ??
                                  'Buyer Profile'),
                        style: const TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 18,
                          color: Color(0xFF3B0764),
                        ),
                      ),
                      Text(
                        'Account ID: ${basic['id'] ?? ''}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Close Details',
                  icon: const Icon(Icons.close),
                  onPressed: widget.onCloseDetails,
                ),
              ],
            ),
          ),
          // Scrollable Body
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: isDealer
                  ? _buildDealerDetails(details)
                  : _buildBuyerDetails(details),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDealerDetails(Map<String, dynamic> details) {
    final basic = Map<String, dynamic>.from(details['basic'] ?? {});
    final locations = List<Map<String, dynamic>>.from(
      details['locations'] ?? [],
    );
    final categories = List<Map<String, dynamic>>.from(
      details['categories'] ?? [],
    );
    final bids = List<Map<String, dynamic>>.from(details['bids'] ?? []);
    final commissions = List<Map<String, dynamic>>.from(
      details['commissions'] ?? [],
    );
    final reports = List<Map<String, dynamic>>.from(details['reports'] ?? []);
    final documents = List<Map<String, dynamic>>.from(
      details['documents'] ?? [],
    );
    final timeline = List<Map<String, dynamic>>.from(details['timeline'] ?? []);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Business info card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Business & Owner Information',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Color(0xFF3B0764),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Owner Name: ${basic['owner_name'] ?? basic['full_name'] ?? ''}',
                ),
                Text('Email Address: ${basic['email'] ?? ''}'),
                Text('Phone Number: ${basic['phone'] ?? ''}'),
                Text('GST Number: ${basic['gst_number'] ?? ''}'),
                Text('Registered Address: ${basic['business_address'] ?? ''}'),
                Row(
                  children: [
                    const Text('Rating: '),
                    Icon(Icons.star, color: Colors.amber, size: 16),
                    Text(' ${basic['rating'] ?? '0.0'}'),
                  ],
                ),
                Text('Account Status: ${basic['status'] ?? ''}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        // Locations & Categories row
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: DataPanel(
                title: 'Service Areas',
                children: locations.isEmpty
                    ? [const Text('No service areas defined.')]
                    : locations
                          .map(
                            (l) => ListTile(
                              dense: true,
                              title: Text(
                                '${l['area'] ?? ''}, ${l['city'] ?? ''}',
                              ),
                              subtitle: Text(
                                'State: ${l['state'] ?? ''} | Radius: ${l['radius_km'] ?? '15'} km',
                              ),
                            ),
                          )
                          .toList(),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DataPanel(
                title: 'Categories Served',
                children: categories.isEmpty
                    ? [const Text('No categories served.')]
                    : categories
                          .map(
                            (c) =>
                                Chip(label: Text(c['name']?.toString() ?? '')),
                          )
                          .toList(),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // Bid History
        DataPanel(
          title: 'Bids History',
          children: bids.isEmpty
              ? [const Text('No bid history recorded.')]
              : bids
                    .map(
                      (b) => ListTile(
                        dense: true,
                        title: Text(b['product']?.toString() ?? ''),
                        subtitle: Text(
                          'Amount: ${money(parseDouble(b['amount']))} | Date: ${b['created_at']}',
                        ),
                        trailing: StatusPill(
                          text: b['status']?.toString() ?? '',
                        ),
                      ),
                    )
                    .toList(),
        ),
        const SizedBox(height: 12),
        // Commission History
        DataPanel(
          title: 'Commission Records',
          children: commissions.isEmpty
              ? [const Text('No commissions recorded.')]
              : commissions
                    .map(
                      (c) => ListTile(
                        dense: true,
                        title: Text(c['product']?.toString() ?? ''),
                        subtitle: Text(
                          'Amount: ${money(parseDouble(c['amount']))} | Date: ${c['created_at']}',
                        ),
                        trailing: StatusPill(
                          text: c['payment_status']?.toString() ?? '',
                        ),
                      ),
                    )
                    .toList(),
        ),
        const SizedBox(height: 12),
        // Reports
        DataPanel(
          title: 'Reports Filed Against Dealer',
          children: reports.isEmpty
              ? [const Text('No reports filed.')]
              : reports
                    .map(
                      (r) => ListTile(
                        dense: true,
                        title: Text(r['reason']?.toString() ?? ''),
                        subtitle: Text(
                          'Reporter: ${r['reporter']} | Description: ${r['description'] ?? ''}',
                        ),
                        trailing: StatusPill(
                          text: r['status']?.toString() ?? '',
                        ),
                      ),
                    )
                    .toList(),
        ),

        const SizedBox(height: 12),
        // Activity Log Timeline
        DataPanel(
          title: 'Status & Action Timeline Logs',
          children: timeline.isEmpty
              ? [const Text('No log entries.')]
              : timeline
                    .map(
                      (t) => ListTile(
                        dense: true,
                        title: Text(
                          'Status Changed: ${t['old_status'] ?? ''} -> ${t['new_status'] ?? ''}',
                        ),
                        subtitle: Text(
                          'Reason: ${t['reason'] ?? 'N/A'} | By: ${t['changed_by'] ?? 'System'}',
                        ),
                        trailing: Text(t['created_at']?.toString() ?? ''),
                      ),
                    )
                    .toList(),
        ),
      ],
    );
  }

  Widget _buildBuyerDetails(Map<String, dynamic> details) {
    final basic = Map<String, dynamic>.from(details['basic'] ?? {});
    final addresses = List<Map<String, dynamic>>.from(
      details['addresses'] ?? [],
    );
    final bids = List<Map<String, dynamic>>.from(details['bids'] ?? []);
    final reports = List<Map<String, dynamic>>.from(details['reports'] ?? []);
    final timeline = List<Map<String, dynamic>>.from(details['timeline'] ?? []);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Personal info card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Personal Contact Information',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Color(0xFF3B0764),
                  ),
                ),
                const SizedBox(height: 10),
                Text('Full Name: ${basic['full_name'] ?? ''}'),
                Text('Email Address: ${basic['email'] ?? ''}'),
                Text('Phone Number: ${basic['phone'] ?? ''}'),
                Text('Account Status: ${basic['status'] ?? ''}'),
                Text('Joined Date: ${basic['created_at'] ?? ''}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        // Addresses Panel
        DataPanel(
          title: 'Locations Used in Bidding',
          children: addresses.isEmpty
              ? [const Text('No addresses recorded.')]
              : addresses
                    .map(
                      (a) => ListTile(
                        dense: true,
                        leading: const Icon(Icons.location_on_outlined),
                        title: Text('${a['area'] ?? ''}, ${a['city'] ?? ''}'),
                        subtitle: Text(
                          'Pincode: ${a['pincode'] ?? ''} | State: ${a['state'] ?? ''}',
                        ),
                      ),
                    )
                    .toList(),
        ),
        const SizedBox(height: 12),
        // Bid Requests & Orders
        DataPanel(
          title: 'Bid Requests History (Orders)',
          children: bids.isEmpty
              ? [const Text('No bid requests recorded.')]
              : bids
                    .map(
                      (b) => ListTile(
                        dense: true,
                        title: Text(b['product']?.toString() ?? ''),
                        subtitle: Text(
                          'Quantity: ${b['quantity'] ?? 1} | Awarded Dealer: ${b['dealer'] ?? 'None'}',
                        ),
                        trailing: StatusPill(
                          text: b['status']?.toString() ?? '',
                        ),
                      ),
                    )
                    .toList(),
        ),
        const SizedBox(height: 12),
        // Reports
        DataPanel(
          title: 'Reports Filed By Buyer',
          children: reports.isEmpty
              ? [const Text('No reports filed by this buyer.')]
              : reports
                    .map(
                      (r) => ListTile(
                        dense: true,
                        title: Text(r['reason']?.toString() ?? ''),
                        subtitle: Text(
                          'Reported Party: ${r['reported_party']} | Description: ${r['description'] ?? ''}',
                        ),
                        trailing: StatusPill(
                          text: r['status']?.toString() ?? '',
                        ),
                      ),
                    )
                    .toList(),
        ),
        const SizedBox(height: 12),
        // Timeline
        DataPanel(
          title: 'Audit Logs Activity Logs',
          children: timeline.isEmpty
              ? [const Text('No activity recorded.')]
              : timeline.map((t) {
                  final meta = Map<String, dynamic>.from(
                    jsonDecode(t['metadata_json']?.toString() ?? '{}'),
                  );
                  return ListTile(
                    dense: true,
                    title: Text(t['action']?.toString() ?? ''),
                    subtitle: Text(
                      'Entity: ${t['entity_type']} | Metadata: $meta',
                    ),
                    trailing: Text(t['created_at']?.toString() ?? ''),
                  );
                }).toList(),
        ),
      ],
    );
  }
}

class ProductAdminPage extends StatefulWidget {
  const ProductAdminPage({
    super.key,
    required this.products,
    required this.onCreate,
    required this.search,
    required this.onSearch,
    required this.onExport,
    required this.name,
    required this.category,
    required this.brand,
    required this.model,
    required this.priceMin,
    required this.priceMax,
    required this.specs,
    required this.onAddSpec,
    required this.token,
    required this.onUpdateProduct,
    required this.onDeleteProduct,
  });

  final List<ProductItem> products;
  final Future<void> Function() onCreate;
  final TextEditingController search;
  final Future<void> Function() onSearch;
  final VoidCallback onExport;
  final TextEditingController name;
  final TextEditingController category;
  final TextEditingController brand;
  final TextEditingController model;
  final TextEditingController priceMin;
  final TextEditingController priceMax;
  final List<FieldPairController> specs;
  final VoidCallback onAddSpec;
  final String token;
  final Future<void> Function(String id, ProductDraft draft) onUpdateProduct;
  final Future<void> Function(String id) onDeleteProduct;

  @override
  State<ProductAdminPage> createState() => _ProductAdminPageState();
}

class _ProductAdminPageState extends State<ProductAdminPage> {
  String _selectedCategory = 'All';
  String? _statusFilter;
  String? _brandFilter;
  double? _minPriceFilter;
  double? _maxPriceFilter;
  String _sortMode = 'Newest';
  bool _showFilters = false;

  // Bulk Upload Overlay State
  bool _showUploadOverlay = false;
  String _uploadFormat = 'CSV';
  final _uploadTextController = TextEditingController();
  List<Map<String, dynamic>> _parsedPreviewRows = [];
  String? _validationError;
  List<Map<String, dynamic>> _categoryTree = [];
  bool _loadingCategories = true;

  // Detail / Edit Form States
  ProductItem? _editingProduct;
  final _editName = TextEditingController();
  final _editCategory = TextEditingController();
  final _editBrand = TextEditingController();
  final _editModel = TextEditingController();
  final _editPriceMin = TextEditingController();
  final _editPriceMax = TextEditingController();
  final _editLocation = TextEditingController();
  List<FieldPairController> _editSpecs = [];

  @override
  void initState() {
    super.initState();
    _loadCategoryTree();
  }

  Future<void> _loadCategoryTree() async {
    try {
      final rows = await ApiClient().getCategories(widget.token);
      if (mounted) {
        setState(() {
          _categoryTree = rows;
          _loadingCategories = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _loadingCategories = false);
      }
    }
  }

  List<String> get _dynamicCategories {
    final fromAdmin = _categoryTree
        .map((row) => row['name']?.toString() ?? '')
        .where((name) => name.isNotEmpty)
        .toList();
    if (fromAdmin.isNotEmpty) return fromAdmin;
    return widget.products.map((p) => p.category).toSet().toList();
  }

  List<String> _dynamicItemsFor(String category) {
    final parent = _categoryTree.firstWhere(
      (row) => row['name']?.toString() == category,
      orElse: () => <String, dynamic>{},
    );
    final items = parent['items'];
    if (items is List) {
      return items
          .map((item) => (item as Map)['name']?.toString() ?? '')
          .where((name) => name.isNotEmpty)
          .toList();
    }
    return widget.products
        .where((p) => p.category == category)
        .map((p) => p.name)
        .toSet()
        .toList();
  }

  List<String> get _knownBrands =>
      widget.products
          .map((p) => p.brand)
          .where((brand) => brand.trim().isNotEmpty)
          .toSet()
          .toList()
        ..sort();

  void _setupEdit(ProductItem product) {
    setState(() {
      _editingProduct = product;
      _editName.text = product.name;
      _editCategory.text = product.category;
      _editBrand.text = product.brand;
      _editModel.text = product.model;
      _editPriceMin.text = product.priceMin.toStringAsFixed(0);
      _editPriceMax.text = product.priceMax.toStringAsFixed(0);
      _editLocation.text = product.location;
      _editSpecs = product.specifications.entries
          .map((e) => FieldPairController.withText(e.key, e.value.toString()))
          .toList();
    });
  }

  void _addEditSpec() {
    setState(() {
      _editSpecs.add(FieldPairController.withText('', ''));
    });
  }

  @override
  void dispose() {
    _uploadTextController.dispose();
    _editName.dispose();
    _editCategory.dispose();
    _editBrand.dispose();
    _editModel.dispose();
    _editPriceMin.dispose();
    _editPriceMax.dispose();
    _editLocation.dispose();
    for (final s in _editSpecs) {
      s.dispose();
    }
    super.dispose();
  }

  // Parse simulated bulk text data
  void _runValidation() {
    final text = _uploadTextController.text.trim();
    if (text.isEmpty) {
      setState(() {
        _validationError = 'Input text cannot be empty';
        _parsedPreviewRows = [];
      });
      return;
    }

    try {
      if (_uploadFormat == 'JSON') {
        final parsed = jsonDecode(text);
        if (parsed is List) {
          setState(() {
            _parsedPreviewRows = parsed
                .map((item) => Map<String, dynamic>.from(item))
                .toList();
            _validationError = null;
          });
        } else if (parsed is Map) {
          setState(() {
            _parsedPreviewRows = [Map<String, dynamic>.from(parsed)];
            _validationError = null;
          });
        }
      } else {
        // CSV or Excel text simulation: split lines, use first line as headers
        final lines = text.split('\n');
        if (lines.length < 2) {
          setState(() {
            _validationError =
                'CSV must have at least a header row and one data row';
            _parsedPreviewRows = [];
          });
          return;
        }
        final headers = lines[0]
            .split(',')
            .map((h) => h.trim().toLowerCase())
            .toList();
        final rows = <Map<String, dynamic>>[];
        for (int i = 1; i < lines.length; i++) {
          final line = lines[i].trim();
          if (line.isEmpty) continue;
          final cells = line.split(',').map((c) => c.trim()).toList();
          final rowMap = <String, dynamic>{};
          for (int j = 0; j < headers.length; j++) {
            if (j < cells.length) {
              rowMap[headers[j]] = cells[j];
            }
          }
          rows.add(rowMap);
        }
        setState(() {
          _parsedPreviewRows = rows;
          _validationError = null;
        });
      }
    } catch (e) {
      setState(() {
        _validationError = 'Failed to parse format: $e';
        _parsedPreviewRows = [];
      });
    }
  }

  Future<void> _importValidatedRows() async {
    if (_parsedPreviewRows.isEmpty) return;
    final api = ApiClient();
    int successCount = 0;
    for (final row in _parsedPreviewRows) {
      try {
        final name =
            row['name']?.toString() ??
            row['product_name']?.toString() ??
            'Unnamed Product';
        final category = row['category']?.toString() ?? 'General';
        final brand = row['brand']?.toString() ?? 'Generic';
        final model = row['model']?.toString() ?? 'Model-X';
        final minPrice = parseDouble(
          row['price_min'] ?? row['min_price'] ?? 100,
        );
        final maxPrice = parseDouble(
          row['price_max'] ?? row['max_price'] ?? 500,
        );
        final loc = row['location']?.toString() ?? 'Mumbai';

        final draft = ProductDraft(
          name: name,
          category: category,
          brand: brand,
          model: model,
          priceMin: minPrice,
          priceMax: maxPrice,
          location: loc,
          specifications: {},
        );
        await api.createProduct(widget.token, draft);
        successCount++;
      } catch (e) {
        // Log individual errors, continue others
      }
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Successfully imported $successCount products.')),
    );
    setState(() {
      _showUploadOverlay = false;
      _parsedPreviewRows = [];
      _uploadTextController.clear();
    });
    widget.onSearch(); // Refresh list
  }

  @override
  Widget build(BuildContext context) {
    // 1. Calculate stats from live list
    final Map<String, int> catDistribution = {};
    for (final p in widget.products) {
      catDistribution[p.category] = (catDistribution[p.category] ?? 0) + 1;
    }

    // 2. Apply filtering & sorting
    var filtered = widget.products.where((p) {
      if (_selectedCategory != 'All' &&
          p.category.toLowerCase() != _selectedCategory.toLowerCase()) {
        return false;
      }
      if (_statusFilter != null &&
          p.status.toLowerCase() != _statusFilter!.toLowerCase()) {
        return false;
      }
      if (_brandFilter != null &&
          p.brand.toLowerCase() != _brandFilter!.toLowerCase()) {
        return false;
      }
      if (_minPriceFilter != null && p.priceMin < _minPriceFilter!) {
        return false;
      }
      if (_maxPriceFilter != null && p.priceMax > _maxPriceFilter!) {
        return false;
      }
      return true;
    }).toList();

    // Sorting
    filtered.sort((a, b) {
      if (_sortMode == 'Newest') {
        return b.id.compareTo(a.id);
      } else if (_sortMode == 'Lowest Price') {
        return a.priceMin.compareTo(b.priceMin);
      } else if (_sortMode == 'Highest Price') {
        return b.priceMax.compareTo(a.priceMax);
      } else {
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      }
    });

    final uniqueBrands = widget.products
        .map((p) => p.brand)
        .where((b) => b.isNotEmpty)
        .toSet()
        .toList();
    final categories = ['All', ...catDistribution.keys];

    return PageScaffold(
      scrollable: false,
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionHeader(
                title: 'Products Catalog Management',
                subtitle:
                    'Amazon-style grid interface for managing dynamic product items, categories, and bulk imports.',
                icon: Icons.inventory_2_outlined,
              ),
              const SizedBox(height: 12),
              // Category statistics block
              _buildStatsBlock(catDistribution),
              const SizedBox(height: 12),
              // Top Search and Buttons Bar
              _buildCatalogToolsBar(),
              const SizedBox(height: 12),
              // Category horizontal selector
              _buildCategorySelector(categories),
              const SizedBox(height: 12),
              if (_showFilters) _buildFiltersRow(uniqueBrands),
              // Catalog grid
              Expanded(
                child: filtered.isEmpty
                    ? const Center(
                        child: Text('No products match the filters.'),
                      )
                    : GridView.builder(
                        itemCount: filtered.length,
                        gridDelegate:
                            const SliverGridDelegateWithMaxCrossAxisExtent(
                              maxCrossAxisExtent: 320,
                              mainAxisExtent: 380,
                              crossAxisSpacing: 12,
                              mainAxisSpacing: 12,
                            ),
                        itemBuilder: (context, index) {
                          final product = filtered[index];
                          return _buildAmazonStyleCard(product);
                        },
                      ),
              ),
            ],
          ),
          if (_showUploadOverlay) _buildBulkUploadOverlay(),
          if (_editingProduct != null) _buildEditProductOverlay(),
        ],
      ),
    );
  }

  Widget _buildStatsBlock(Map<String, int> distribution) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Product Catalog Statistics',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: Color(0xFF3B0764),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: distribution.entries.map((e) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.circle,
                      size: 10,
                      color: Color(0xFF6D28D9),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '${e.key}: ',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    Text(
                      '${e.value} products',
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ],
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCatalogToolsBar() {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: widget.search,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search products by SKU, Name, brand, model, spec...',
            ),
            onSubmitted: (_) => widget.onSearch(),
          ),
        ),
        const SizedBox(width: 8),
        FilledButton.icon(
          onPressed: widget.onSearch,
          icon: const Icon(Icons.search),
          label: const Text('Search'),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: () => setState(() => _showFilters = !_showFilters),
          icon: const Icon(Icons.filter_alt_outlined),
          label: const Text('Filters'),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: () => setState(() => _showUploadOverlay = true),
          icon: const Icon(Icons.upload_file_outlined),
          label: const Text('Bulk Upload'),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: widget.onExport,
          icon: const Icon(Icons.download_outlined),
          label: const Text('Download CSV'),
        ),
        const SizedBox(width: 8),
        FilledButton.icon(
          onPressed: _openAddProductDialog,
          icon: const Icon(Icons.add),
          label: const Text('+ Add Product'),
        ),
      ],
    );
  }

  Future<void> _openAddProductDialog() async {
    final nameCtrl = TextEditingController();
    final modelCtrl = TextEditingController();
    final priceMinCtrl = TextEditingController();
    final priceMaxCtrl = TextEditingController();
    final descCtrl = TextEditingController();

    if (_loadingCategories) {
      await _loadCategoryTree();
    }
    final categories = _dynamicCategories;
    String selectedCategory = categories.isNotEmpty ? categories.first : '';
    String? selectedSubcategory;
    final brandCtrl = TextEditingController();
    String status = 'active';

    final List<FieldPairController> customSpecs = [
      FieldPairController.withText('Warranty', '1 year'),
    ];

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            final subcategories = _dynamicItemsFor(selectedCategory);
            if (selectedSubcategory == null ||
                !subcategories.contains(selectedSubcategory)) {
              selectedSubcategory = subcategories.isNotEmpty
                  ? subcategories.first
                  : null;
            }
            final brandsList = _knownBrands;

            return AlertDialog(
              title: const Text('Add Product to Catalog'),
              content: SizedBox(
                width: 500,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: nameCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Product Name (Required)',
                        ),
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: selectedCategory.isEmpty
                            ? null
                            : selectedCategory,
                        decoration: const InputDecoration(
                          labelText: 'Category (Required)',
                        ),
                        items: categories
                            .map(
                              (c) => DropdownMenuItem(value: c, child: Text(c)),
                            )
                            .toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setState(() {
                              selectedCategory = val;
                              selectedSubcategory = null;
                            });
                          }
                        },
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: selectedSubcategory,
                        decoration: const InputDecoration(
                          labelText: 'Subcategory / Item (Required)',
                        ),
                        items: subcategories
                            .map(
                              (s) => DropdownMenuItem(value: s, child: Text(s)),
                            )
                            .toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setState(() {
                              selectedSubcategory = val;
                            });
                          }
                        },
                      ),
                      const SizedBox(height: 8),
                      Autocomplete<String>(
                        optionsBuilder: (value) {
                          final q = value.text.trim().toLowerCase();
                          if (q.isEmpty) return brandsList;
                          return brandsList.where(
                            (brand) => brand.toLowerCase().contains(q),
                          );
                        },
                        onSelected: (value) => brandCtrl.text = value,
                        fieldViewBuilder:
                            (context, controller, focusNode, onSubmit) {
                              if (controller.text != brandCtrl.text) {
                                controller.text = brandCtrl.text;
                              }
                              controller.addListener(
                                () => brandCtrl.text = controller.text,
                              );
                              return TextField(
                                controller: controller,
                                focusNode: focusNode,
                                decoration: const InputDecoration(
                                  labelText: 'Brand Name (select or type new)',
                                ),
                              );
                            },
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: modelCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Model Name / Number',
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: priceMinCtrl,
                              decoration: const InputDecoration(
                                labelText: 'Min Price (Rs.)',
                              ),
                              keyboardType: TextInputType.number,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: priceMaxCtrl,
                              decoration: const InputDecoration(
                                labelText: 'Max Price (Rs.)',
                              ),
                              keyboardType: TextInputType.number,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: descCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Product Description',
                        ),
                        maxLines: 3,
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: status,
                        decoration: const InputDecoration(labelText: 'Status'),
                        items: const [
                          DropdownMenuItem(
                            value: 'active',
                            child: Text('Active'),
                          ),
                          DropdownMenuItem(
                            value: 'inactive',
                            child: Text('Inactive'),
                          ),
                        ],
                        onChanged: (val) {
                          if (val != null) setState(() => status = val);
                        },
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Specifications',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          TextButton.icon(
                            icon: const Icon(Icons.add, size: 16),
                            label: const Text('Add Spec'),
                            onPressed: () {
                              setState(() {
                                customSpecs.add(
                                  FieldPairController.withText('', ''),
                                );
                              });
                            },
                          ),
                        ],
                      ),
                      ...customSpecs
                          .map(
                            (spec) => Padding(
                              padding: const EdgeInsets.only(bottom: 6),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: spec.name,
                                      decoration: const InputDecoration(
                                        labelText: 'Spec Key',
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: TextField(
                                      controller: spec.value,
                                      decoration: const InputDecoration(
                                        labelText: 'Spec Value',
                                      ),
                                    ),
                                  ),
                                  IconButton(
                                    icon: const Icon(
                                      Icons.delete_outline,
                                      color: Colors.red,
                                    ),
                                    onPressed: () {
                                      setState(() {
                                        customSpecs.remove(spec);
                                        spec.dispose();
                                      });
                                    },
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () async {
                    if (nameCtrl.text.trim().isEmpty ||
                        selectedCategory.isEmpty ||
                        (selectedSubcategory ?? '').isEmpty ||
                        brandCtrl.text.trim().isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Please fill all required fields'),
                        ),
                      );
                      return;
                    }

                    final minP =
                        double.tryParse(priceMinCtrl.text.trim()) ?? 0.0;
                    final maxP =
                        double.tryParse(priceMaxCtrl.text.trim()) ?? 0.0;

                    final specMap = <String, String>{};
                    if (descCtrl.text.trim().isNotEmpty) {
                      specMap['Description'] = descCtrl.text.trim();
                    }
                    for (final spec in customSpecs) {
                      if (spec.name.text.trim().isNotEmpty) {
                        specMap[spec.name.text.trim()] = spec.value.text.trim();
                      }
                    }

                    Navigator.pop(context);

                    try {
                      final draft = ProductDraft(
                        name: nameCtrl.text.trim(),
                        category: selectedCategory,
                        subcategory: selectedSubcategory!,
                        brand: brandCtrl.text.trim(),
                        model: modelCtrl.text.trim(),
                        priceMin: minP,
                        priceMax: maxP,
                        location: '',
                        specifications: specMap,
                      );

                      await ApiClient().createProduct(widget.token, draft);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Product added successfully!'),
                        ),
                      );
                      widget.onSearch();
                    } catch (e) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Failed to add product: $e')),
                      );
                    }
                  },
                  child: const Text('Save Product'),
                ),
              ],
            );
          },
        );
      },
    );
    brandCtrl.dispose();
  }

  Widget _buildCategorySelector(List<String> categories) {
    return SizedBox(
      height: 40,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: categories.length,
        itemBuilder: (context, index) {
          final cat = categories[index];
          final isSelected = _selectedCategory == cat;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text(cat),
              selected: isSelected,
              onSelected: (val) {
                if (val) {
                  setState(() => _selectedCategory = cat);
                }
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildFiltersRow(List<String> brands) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Wrap(
          spacing: 16,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            DropdownButton<String>(
              hint: const Text('Brand'),
              value: _brandFilter,
              onChanged: (val) => setState(() => _brandFilter = val),
              items: brands
                  .map((b) => DropdownMenuItem(value: b, child: Text(b)))
                  .toList(),
            ),
            DropdownButton<String>(
              hint: const Text('Status'),
              value: _statusFilter,
              onChanged: (val) => setState(() => _statusFilter = val),
              items: ['active', 'archived']
                  .map(
                    (s) => DropdownMenuItem(
                      value: s,
                      child: Text(s.toUpperCase()),
                    ),
                  )
                  .toList(),
            ),
            SizedBox(
              width: 120,
              child: TextField(
                decoration: const InputDecoration(
                  labelText: 'Min Price',
                  isDense: true,
                ),
                keyboardType: TextInputType.number,
                onChanged: (val) =>
                    setState(() => _minPriceFilter = double.tryParse(val)),
              ),
            ),
            SizedBox(
              width: 120,
              child: TextField(
                decoration: const InputDecoration(
                  labelText: 'Max Price',
                  isDense: true,
                ),
                keyboardType: TextInputType.number,
                onChanged: (val) =>
                    setState(() => _maxPriceFilter = double.tryParse(val)),
              ),
            ),
            DropdownButton<String>(
              hint: const Text('Sort By'),
              value: _sortMode,
              onChanged: (val) {
                if (val != null) setState(() => _sortMode = val);
              },
              items: [
                'Newest',
                'Lowest Price',
                'Highest Price',
                'Name',
              ].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  _brandFilter = null;
                  _statusFilter = null;
                  _minPriceFilter = null;
                  _maxPriceFilter = null;
                  _sortMode = 'Newest';
                });
              },
              child: const Text('Reset'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAmazonStyleCard(ProductItem product) {
    final specsList = product.specifications.entries.toList();
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Simulated Product Image
          Container(
            height: 130,
            width: double.infinity,
            decoration: const BoxDecoration(
              color: Color(0xFFF5F3FF),
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: Icon(
              Icons.inventory_2_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          // Product Details
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.brand.toUpperCase(),
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    product.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${money(product.priceMin)} - ${money(product.priceMax)}',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF16A34A),
                        ),
                      ),
                      StatusPill(text: product.status),
                    ],
                  ),
                  const SizedBox(height: 6),
                  // Specs Highlight
                  Expanded(
                    child: ListView.builder(
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: specsList.length > 3 ? 3 : specsList.length,
                      itemBuilder: (context, idx) {
                        final s = specsList[idx];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 2),
                          child: Text(
                            'â€¢ ${s.key}: ${s.value}',
                            style: const TextStyle(
                              fontSize: 11,
                              color: Colors.grey,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          const Divider(height: 1),
          // Actions Row
          Padding(
            padding: const EdgeInsets.all(6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                IconButton(
                  tooltip: 'View specifications',
                  icon: const Icon(Icons.info_outline, size: 18),
                  onPressed: () => _showSpecsDialog(product),
                ),
                IconButton(
                  tooltip: 'Edit product details',
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  onPressed: () => _setupEdit(product),
                ),
                IconButton(
                  tooltip: 'Duplicate product',
                  icon: const Icon(Icons.copy_all_outlined, size: 18),
                  onPressed: () => _duplicateProduct(product),
                ),
                IconButton(
                  tooltip: 'Archive product',
                  icon: const Icon(Icons.archive_outlined, size: 18),
                  onPressed: () => _archiveProduct(product),
                ),
                IconButton(
                  tooltip: 'Delete product',
                  icon: const Icon(
                    Icons.delete_outline,
                    color: Colors.red,
                    size: 18,
                  ),
                  onPressed: () => _deleteProductConfirm(product),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showSpecsDialog(ProductItem product) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(product.name),
        content: SizedBox(
          width: 320,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Brand: ${product.brand}'),
              Text('Model: ${product.model}'),
              Text('Category: ${product.category}'),
              Text('Location: ${product.location}'),
              const Divider(),
              const Text(
                'Full Specifications:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              ...product.specifications.entries
                  .map((e) => Text('â€¢ ${e.key}: ${e.value}'))
                  .toList(),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Future<void> _duplicateProduct(ProductItem product) async {
    final draft = ProductDraft(
      name: '${product.name} (Copy)',
      category: product.category,
      brand: product.brand,
      model: product.model,
      priceMin: product.priceMin,
      priceMax: product.priceMax,
      location: product.location,
      specifications: Map<String, String>.from(product.specifications),
    );
    setState(() => _showUploadOverlay = false);
    final api = ApiClient();
    try {
      await api.createProduct(widget.token, draft);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Product duplicated successfully!')),
      );
      widget.onSearch();
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to duplicate: $e')));
    }
  }

  Future<void> _archiveProduct(ProductItem product) async {
    final draft = ProductDraft(
      name: product.name,
      category: product.category,
      brand: product.brand,
      model: product.model,
      priceMin: product.priceMin,
      priceMax: product.priceMax,
      location: product.location,
      specifications: Map<String, String>.from(product.specifications),
    );
    try {
      await widget.onUpdateProduct(product.id, draft);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Product archived.')));
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to archive: $e')));
    }
  }

  void _deleteProductConfirm(ProductItem product) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Product?'),
        content: Text(
          'Are you sure you want to delete ${product.name}? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              widget.onDeleteProduct(product.id);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Widget _buildBulkUploadOverlay() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Bulk Catalog Import',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                    color: Color(0xFF3B0764),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => setState(() => _showUploadOverlay = false),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            'Select file format and paste bulk records or simulated columns (CSV or JSON).',
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Text('Format: '),
              DropdownButton<String>(
                value: _uploadFormat,
                onChanged: (val) {
                  if (val != null) setState(() => _uploadFormat = val);
                },
                items: ['CSV', 'JSON']
                    .map((f) => DropdownMenuItem(value: f, child: Text(f)))
                    .toList(),
              ),
              const SizedBox(width: 20),
              ElevatedButton(
                onPressed: () {
                  if (_uploadFormat == 'CSV') {
                    _uploadTextController.text =
                        'name,category,brand,model,price_min,price_max,location\n'
                        'OnePlus Nord CE4,Electronics,OnePlus,CE4,24999,26999,Delhi\n'
                        'Stethoscope Classic,Medical,3M Littmann,Classic III,8500,9200,Mumbai\n'
                        'Executive Desk,Office,Godrej Interio,Executive,15000,18000,Karnataka';
                  } else {
                    _uploadTextController.text =
                        const JsonEncoder.withIndent('  ').convert([
                          {
                            "name": "OnePlus Nord CE4",
                            "category": "Electronics",
                            "brand": "OnePlus",
                            "model": "CE4",
                            "price_min": 24999,
                            "price_max": 26999,
                            "location": "Delhi",
                          },
                          {
                            "name": "Stethoscope Classic",
                            "category": "Medical",
                            "brand": "3M Littmann",
                            "model": "Classic III",
                            "price_min": 8500,
                            "price_max": 9200,
                            "location": "Mumbai",
                          },
                        ]);
                  }
                },
                child: const Text('Load Demo Template'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Expanded(
            child: TextField(
              controller: _uploadTextController,
              maxLines: null,
              keyboardType: TextInputType.multiline,
              decoration: const InputDecoration(
                hintText: 'Paste CSV or JSON contents here...',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          if (_validationError != null) ...[
            const SizedBox(height: 8),
            Text(
              _validationError!,
              style: const TextStyle(
                color: Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
          if (_parsedPreviewRows.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              height: 120,
              decoration: BoxDecoration(border: Border.all(color: Colors.grey)),
              child: ListView.builder(
                itemCount: _parsedPreviewRows.length,
                itemBuilder: (context, idx) {
                  final row = _parsedPreviewRows[idx];
                  return ListTile(
                    dense: true,
                    title: Text(
                      row['name']?.toString() ??
                          row['product_name']?.toString() ??
                          'Unnamed',
                    ),
                    subtitle: Text(
                      'Category: ${row['category'] ?? ''} | Brand: ${row['brand'] ?? ''} | Min Price: ${row['price_min'] ?? row['min_price'] ?? ''}',
                    ),
                    trailing: const Icon(
                      Icons.check_circle,
                      color: Colors.green,
                    ),
                  );
                },
              ),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton(
                onPressed: _runValidation,
                child: const Text('Validate & Preview'),
              ),
              const SizedBox(width: 10),
              FilledButton(
                onPressed: _parsedPreviewRows.isEmpty
                    ? null
                    : _importValidatedRows,
                child: const Text('Import Catalog'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEditProductOverlay() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Edit Product Details',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: Color(0xFF3B0764),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => setState(() => _editingProduct = null),
              ),
            ],
          ),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  TextField(
                    controller: _editName,
                    decoration: const InputDecoration(
                      labelText: 'Product Name',
                    ),
                  ),
                  TextField(
                    controller: _editCategory,
                    decoration: const InputDecoration(labelText: 'Category'),
                  ),
                  TextField(
                    controller: _editBrand,
                    decoration: const InputDecoration(labelText: 'Brand'),
                  ),
                  TextField(
                    controller: _editModel,
                    decoration: const InputDecoration(labelText: 'Model'),
                  ),
                  TextField(
                    controller: _editPriceMin,
                    decoration: const InputDecoration(labelText: 'Price Min'),
                  ),
                  TextField(
                    controller: _editPriceMax,
                    decoration: const InputDecoration(labelText: 'Price Max'),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Specifications',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  ..._editSpecs.map(
                    (s) => Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: s.name,
                            decoration: const InputDecoration(
                              labelText: 'Label',
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: s.value,
                            decoration: const InputDecoration(
                              labelText: 'Value',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _addEditSpec,
                    child: const Text('Add Spec Field'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () async {
              final Map<String, String> finalSpecs = {};
              for (final s in _editSpecs) {
                if (s.name.text.isNotEmpty) {
                  finalSpecs[s.name.text] = s.value.text;
                }
              }
              final draft = ProductDraft(
                name: _editName.text,
                category: _editCategory.text,
                brand: _editBrand.text,
                model: _editModel.text,
                priceMin: parseDouble(_editPriceMin.text),
                priceMax: parseDouble(_editPriceMax.text),
                location: '',
                specifications: finalSpecs,
              );
              await widget.onUpdateProduct(_editingProduct!.id, draft);
              setState(() => _editingProduct = null);
            },
            child: const Text('Save Changes'),
          ),
        ],
      ),
    );
  }
}

class BuyerCatalogPage extends StatelessWidget {
  const BuyerCatalogPage({
    super.key,
    required this.products,
    required this.search,
    required this.onSearch,
    required this.onCart,
    required this.onBid,
    required this.onSelect,
    required this.selectedProduct,
    required this.selectedCategory,
    required this.onCategory,
    required this.onOpenFilters,
    required this.onClearFilters,
    required this.sortMode,
    required this.onSort,
  });
  final List<ProductItem> products;
  final TextEditingController search;
  final Future<void> Function() onSearch;
  final Future<void> Function(ProductItem product) onCart;
  final Future<void> Function(ProductItem product) onBid;
  final ValueChanged<ProductItem> onSelect;
  final ProductItem? selectedProduct;
  final String? selectedCategory;
  final ValueChanged<String> onCategory;
  final VoidCallback onOpenFilters;
  final VoidCallback onClearFilters;
  final String sortMode;
  final ValueChanged<String> onSort;
  @override
  Widget build(BuildContext context) => PageScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Product Browser',
          subtitle:
              'Amazon-style browsing with product search, sort, category, and right-side filters.',
          icon: Icons.search_outlined,
          trailing: IconButton(
            tooltip: 'Filters',
            onPressed: onOpenFilters,
            icon: const Icon(Icons.tune_outlined),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: search,
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search),
            labelText: 'Keyword, category, brand, specs',
          ),
          onSubmitted: (_) => onSearch(),
        ),
        const SizedBox(height: 12),
        CategoryStrip(selected: selectedCategory, onCategory: onCategory),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            FilledButton.icon(
              onPressed: onSearch,
              icon: const Icon(Icons.search),
              label: const Text('Search'),
            ),
            OutlinedButton.icon(
              onPressed: onOpenFilters,
              icon: const Icon(Icons.tune_outlined),
              label: const Text('Filter'),
            ),
            OutlinedButton.icon(
              onPressed: onClearFilters,
              icon: const Icon(Icons.clear),
              label: const Text('Clear Filters'),
            ),
            DropdownButton<String>(
              value: sortMode,
              items: const ['Newest', 'Price Low', 'Price High', 'A-Z']
                  .map(
                    (item) => DropdownMenuItem(value: item, child: Text(item)),
                  )
                  .toList(),
              onChanged: (value) {
                if (value != null) onSort(value);
              },
            ),
          ],
        ),
        const SizedBox(height: 12),
        ProductList(
          products: products,
          onCart: onCart,
          onBid: onBid,
          onSelect: onSelect,
          selectedProduct: selectedProduct,
          grid: true,
        ),
      ],
    ),
  );
}

class ProductList extends StatelessWidget {
  const ProductList({
    super.key,
    required this.products,
    this.onCart,
    this.onBid,
    this.onSelect,
    this.selectedProduct,
    this.grid = false,
  });
  final List<ProductItem> products;
  final Future<void> Function(ProductItem product)? onCart;
  final Future<void> Function(ProductItem product)? onBid;
  final ValueChanged<ProductItem>? onSelect;
  final ProductItem? selectedProduct;
  final bool grid;
  @override
  Widget build(BuildContext context) {
    if (products.isEmpty) {
      return const EmptyState(
        icon: Icons.inventory_2_outlined,
        title: 'No products',
        message: 'Try another search or clear filters.',
      );
    }
    if (!grid) {
      return Column(
        children: products
            .map(
              (product) => ProductCard(
                product: product,
                selected: selectedProduct?.id == product.id,
                onSelect: onSelect == null ? null : () => onSelect!(product),
                onCart: onCart == null ? null : () => onCart!(product),
                onBid: onBid == null ? null : () => onBid!(product),
              ),
            )
            .toList(),
      );
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1100
            ? 5
            : constraints.maxWidth >= 760
            ? 3
            : 2;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: products.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: columns == 5
                ? 0.54
                : (columns == 3 ? 0.50 : 0.46),
          ),
          itemBuilder: (context, index) {
            final product = products[index];
            return ProductCard(
              product: product,
              selected: selectedProduct?.id == product.id,
              onSelect: onSelect == null ? null : () => onSelect!(product),
              onCart: onCart == null ? null : () => onCart!(product),
              onBid: onBid == null ? null : () => onBid!(product),
            );
          },
        );
      },
    );
  }
}

class BuyerBidPage extends StatelessWidget {
  const BuyerBidPage({
    super.key,
    required this.bids,
    required this.requests,
    required this.selectedProduct,
    required this.onBid,
    required this.onAccept,
    required this.onRefresh,
    this.onCancelRequest,
  });

  final List<BidRecord> bids;
  final List<Map<String, dynamic>> requests;
  final ProductItem? selectedProduct;
  final Future<void> Function(ProductItem product) onBid;
  final Future<void> Function(BidRecord bid) onAccept;
  final Future<void> Function() onRefresh;
  final Future<void> Function(String requestId)? onCancelRequest;

  @override
  Widget build(BuildContext context) {
    final live = bids
        .where(
          (bid) =>
              (bid.status == 'active' || bid.status == 'updated') &&
              bid.selectable,
        )
        .toList();
    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          DataPanel(
            title: 'Finalized winning offers',
            children: bids
                .where((bid) => bid.status == 'won')
                .map(
                  (bid) => ListTile(
                    title: Text('${bid.product}: ${money(bid.amount)}'),
                    subtitle: Text('Request ${bid.bidRequestId}'),
                    trailing: TextButton(
                      onPressed: () => showLiveBidDialog(context, bid),
                      child: const Text('Contacts & Chat'),
                    ),
                  ),
                )
                .toList(),
          ),

          SectionHeader(
            title: 'Active Bids & Live Offers',
            subtitle:
                'Monitor your active bid requests and choose the winning dealer offer.',
            icon: Icons.bolt_outlined,
            trailing: IconButton(
              tooltip: 'Refresh bids',
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh),
            ),
          ),
          const SizedBox(height: 12),
          DataPanel(
            title: 'My Active Bid Requests (${requests.length})',
            children: requests.isEmpty
                ? [
                    const Text(
                      'You have no active bid requests. Go to Home to request bids.',
                    ),
                  ]
                : requests.map((req) {
                    final offersCount = req['offers_count'] ?? 0;
                    return ListTile(
                      onTap: () => _showRequestDetailsDialog(context, req),
                      leading: Icon(
                        offersCount == 0
                            ? Icons.warning_amber_rounded
                            : Icons.hourglass_empty,
                        color: offersCount == 0 ? Colors.orange : Colors.blue,
                      ),
                      title: Text(
                        '${req['product']} (Qty: ${req['quantity']})',
                      ),
                      subtitle: Text(
                        offersCount == 0
                            ? 'Status: ${req['status']} | No dealer offers received yet.'
                            : 'Status: ${req['status']} | Received Offers: $offersCount | Ends: ${req['expires_at'] ?? ''}',
                      ),
                      trailing: offersCount == 0
                          ? TextButton.icon(
                              onPressed: () {
                                showDialog<void>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('No Offers Received'),
                                    content: const Text(
                                      'No dealers have responded to this bid request yet. You can cancel it and re-broadcast with a different saved location, product options, or notes.',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(ctx),
                                        child: const Text('Back'),
                                      ),
                                      TextButton(
                                        onPressed: () async {
                                          Navigator.pop(ctx);
                                          if (onCancelRequest != null) {
                                            try {
                                              await onCancelRequest!(req['id']);
                                              ScaffoldMessenger.of(
                                                context,
                                              ).showSnackBar(
                                                const SnackBar(
                                                  content: Text(
                                                    'Bid request cancelled successfully.',
                                                  ),
                                                ),
                                              );
                                            } catch (e) {
                                              ScaffoldMessenger.of(
                                                context,
                                              ).showSnackBar(
                                                SnackBar(
                                                  content: Text(
                                                    'Failed to cancel: $e',
                                                  ),
                                                ),
                                              );
                                            }
                                          }
                                        },
                                        child: const Text(
                                          'Cancel Request',
                                          style: TextStyle(color: Colors.red),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                              icon: const Icon(
                                Icons.cancel_outlined,
                                color: Colors.red,
                                size: 16,
                              ),
                              label: const Text(
                                'Change/Cancel',
                                style: TextStyle(color: Colors.red),
                              ),
                            )
                          : null,
                    );
                  }).toList(),
          ),
          const SizedBox(height: 12),
          DataPanel(
            title: 'Live Bid Offers (${live.length})',
            children: live.isEmpty
                ? [
                    const Text(
                      'No active bids or dealer offers currently open.',
                    ),
                  ]
                : live
                      .map(
                        (bid) => ListTile(
                          leading: const Icon(
                            Icons.bolt_outlined,
                            color: Colors.amber,
                          ),
                          title: Text('${bid.product} | ${money(bid.amount)}'),
                          subtitle: const Text(
                            'Dealer identity is hidden until you accept this bid | Terms: Warranty & Delivery included',
                          ),
                          trailing: FilledButton(
                            onPressed: () async {
                              try {
                                await onAccept(bid);
                              } catch (e) {
                                if (context.mounted)
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Could not accept offer: $e',
                                      ),
                                    ),
                                  );
                              }
                            },
                            child: const Text('Accept Offer'),
                          ),
                        ),
                      )
                      .toList(),
          ),
        ],
      ),
    );
  }

  void _showRequestDetailsDialog(
    BuildContext context,
    Map<String, dynamic> request,
  ) {
    showDialog<void>(
      context: context,
      builder: (ctx) => ValueListenableBuilder<List<BidRecord>>(
        valueListenable: liveBidRecords,
        builder: (context, records, _) {
          final reqBids = records
              .where(
                (bid) =>
                    bid.bidRequestId == request['id'] &&
                    bid.status != 'withdrawn',
              )
              .toList();
          return Dialog(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 700, maxHeight: 600),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            'Bid Request: ${request['product']}',
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: const Color(0xFF6D28D9),
                                ),
                          ),
                        ),
                        IconButton(
                          onPressed: () => Navigator.pop(ctx),
                          icon: const Icon(Icons.close),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    Row(
                      children: [
                        _infoBadge(
                          'Quantity: ${request['quantity']}',
                          Icons.production_quantity_limits,
                        ),
                        const SizedBox(width: 8),
                        _infoBadge(
                          'Status: ${request['status']}',
                          Icons.info_outline,
                        ),
                        if (onCancelRequest != null)
                          TextButton(
                            onPressed: () async {
                              try {
                                await onCancelRequest!(
                                  request['id'].toString(),
                                );
                                if (ctx.mounted) Navigator.pop(ctx);
                              } catch (e) {
                                if (ctx.mounted)
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Could not cancel request: $e',
                                      ),
                                    ),
                                  );
                              }
                            },
                            child: const Text('Cancel Request'),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Dealer Offers (${reqBids.length})',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: reqBids.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.hourglass_empty,
                                    size: 48,
                                    color: Colors.grey[400],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'No dealer offers received yet.',
                                    style: TextStyle(color: Colors.grey[600]),
                                  ),
                                ],
                              ),
                            )
                          : ListView.builder(
                              itemCount: reqBids.length,
                              itemBuilder: (context, idx) {
                                final bid = reqBids[idx];
                                return Card(
                                  elevation: 0,
                                  margin: const EdgeInsets.only(bottom: 12),
                                  shape: RoundedRectangleBorder(
                                    side: BorderSide(color: Colors.grey[300]!),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  const Icon(
                                                    Icons.bolt,
                                                    color: Colors.amber,
                                                    size: 20,
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    bid.dealer,
                                                    style: const TextStyle(
                                                      fontWeight:
                                                          FontWeight.bold,
                                                    ),
                                                  ),
                                                  const Spacer(),
                                                  Text(
                                                    money(bid.amount),
                                                    style: const TextStyle(
                                                      fontWeight:
                                                          FontWeight.bold,
                                                      color: Colors.green,
                                                      fontSize: 16,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                              const SizedBox(height: 8),
                                              if (bid.discountAmount > 0)
                                                Text(
                                                  'Includes Discount: -${money(bid.discountAmount)}',
                                                  style: const TextStyle(
                                                    color: Colors.red,
                                                    fontSize: 13,
                                                  ),
                                                ),
                                              Text(
                                                'Delivery Time: ${bid.deliveryTime}',
                                                style: const TextStyle(
                                                  fontSize: 13,
                                                ),
                                              ),
                                              Text(
                                                'Warranty: ${bid.warrantyText}',
                                                style: const TextStyle(
                                                  fontSize: 13,
                                                ),
                                              ),
                                              if (bid.freeGifts.isNotEmpty)
                                                Text(
                                                  'Free Gifts: ${bid.freeGifts}',
                                                  style: const TextStyle(
                                                    fontSize: 13,
                                                  ),
                                                ),
                                              if (bid.extraServices.isNotEmpty)
                                                Text(
                                                  'Extra Services: ${bid.extraServices}',
                                                  style: const TextStyle(
                                                    fontSize: 13,
                                                  ),
                                                ),
                                              if (bid.notes.isNotEmpty)
                                                Text(
                                                  'Notes: ${bid.notes}',
                                                  style: const TextStyle(
                                                    fontSize: 13,
                                                    fontStyle: FontStyle.italic,
                                                  ),
                                                ),
                                            ],
                                          ),
                                        ),
                                        const SizedBox(width: 16),
                                        Column(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            FilledButton(
                                              onPressed:
                                                  ![
                                                        'active',
                                                        'updated',
                                                      ].contains(bid.status) ||
                                                      !bid.selectable
                                                  ? null
                                                  : () async {
                                                      try {
                                                        await onAccept(bid);
                                                        if (ctx.mounted)
                                                          Navigator.pop(ctx);
                                                      } catch (e) {
                                                        if (ctx.mounted)
                                                          ScaffoldMessenger.of(
                                                            ctx,
                                                          ).showSnackBar(
                                                            SnackBar(
                                                              content: Text(
                                                                'Could not accept offer: $e',
                                                              ),
                                                            ),
                                                          );
                                                      }
                                                    },
                                              child: Text(
                                                ![
                                                      'active',
                                                      'updated',
                                                    ].contains(bid.status)
                                                    ? bid.status.toUpperCase()
                                                    : bid.selectable
                                                    ? 'Accept Offer'
                                                    : 'Dealer unavailable',
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _infoBadge(String label, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF3E8FF),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: const Color(0xFF6D28D9)),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF6D28D9),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class OrdersHistoryPage extends StatelessWidget {
  const OrdersHistoryPage({
    super.key,
    required this.bids,
    this.requests = const [],
    this.focusedBidId,
    required this.onReport,
    required this.onRebid,
  });

  final List<BidRecord> bids;
  final List<Map<String, dynamic>> requests;
  final String? focusedBidId;
  final ValueChanged<BidRecord> onReport;
  final ValueChanged<BidRecord> onRebid;

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeader(
            title: 'Orders / History',
            subtitle:
                'Orders, bid history, purchased products, expired bids, cancelled bids, and cart history.',
            icon: Icons.history_outlined,
          ),
          const SizedBox(height: 12),
          DefaultTabController(
            length: 4,
            child: DataPanel(
              title: 'Order History Activity',
              children: [
                const TabBar(
                  isScrollable: true,
                  tabs: [
                    Tab(text: 'Accepted (Won)'),
                    Tab(text: 'Expired'),
                    Tab(text: 'Cancelled'),
                    Tab(text: 'All Orders'),
                  ],
                ),
                SizedBox(
                  height: 360,
                  child: TabBarView(
                    children: [
                      _HistoryList(
                        bids: bids.where((bid) => bid.status == 'won').toList(),
                        focusedBidId: focusedBidId,
                        onReport: onReport,
                        onRebid: onRebid,
                      ),
                      _HistoryList(
                        bids: bids
                            .where(
                              (bid) =>
                                  bid.status == 'expired' &&
                                  bid.requestStatus != 'cancelled',
                            )
                            .toList(),
                        focusedBidId: focusedBidId,
                        onReport: onReport,
                        onRebid: onRebid,
                      ),
                      _HistoryList(
                        bids: bids
                            .where((bid) => bid.requestStatus == 'cancelled')
                            .toList(),
                        focusedBidId: focusedBidId,
                        onReport: onReport,
                        onRebid: onRebid,
                      ),
                      // All bids that are not active/updated
                      _HistoryList(
                        bids: bids
                            .where(
                              (bid) =>
                                  bid.status != 'active' &&
                                  bid.status != 'updated',
                            )
                            .toList(),
                        focusedBidId: focusedBidId,
                        onReport: onReport,
                        onRebid: onRebid,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          DataPanel(
            title: 'Closed Request History',
            children: requests
                .where((request) => request['status'] != 'active')
                .map(
                  (request) => ListTile(
                    title: Text(
                      '${request['product']} (Qty: ${request['quantity']})',
                    ),
                    subtitle: Text('Request: ${request['id']}'),
                    trailing: StatusPill(text: request['status'].toString()),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _HistoryList extends StatelessWidget {
  const _HistoryList({
    required this.bids,
    this.focusedBidId,
    required this.onRebid,
    this.onReport,
  });

  final List<BidRecord> bids;
  final String? focusedBidId;
  final ValueChanged<BidRecord> onRebid;
  final ValueChanged<BidRecord>? onReport;

  @override
  Widget build(BuildContext context) {
    if (bids.isEmpty) {
      return const Center(child: Text('No records in this tab.'));
    }
    return ListView(
      children: bids
          .map(
            (bid) => Card(
              color: bid.id == focusedBidId ? const Color(0xFFF3E8FF) : null,
              shape: bid.id == focusedBidId
                  ? RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(
                        color: Color(0xFF7C3AED),
                        width: 1.4,
                      ),
                    )
                  : null,
              margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header row
                    Row(
                      children: [
                        StatusPill(text: bid.status),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            bid.product,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                        ),
                        Text(
                          money(bid.amount),
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            color: Color(0xFF2563EB),
                          ),
                        ),
                      ],
                    ),
                    // Show dealer contact once won
                    if (bid.status == 'won' || bid.status == 'completed') ...[
                      const Divider(height: 14),
                      const Text(
                        'Dealer Contact Details',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF16A34A),
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 4),
                      if (bid.ownerName.isNotEmpty)
                        _infoRow(Icons.person_outline, bid.ownerName),
                      if (bid.dealerPhone.isNotEmpty)
                        _infoRow(Icons.phone_outlined, bid.dealerPhone),
                      if (bid.dealerEmail.isNotEmpty)
                        _infoRow(Icons.email_outlined, bid.dealerEmail),
                      if (bid.businessAddress.isNotEmpty)
                        _infoRow(
                          Icons.location_on_outlined,
                          bid.businessAddress,
                        ),
                      if (bid.gstNumber.isNotEmpty)
                        _infoRow(
                          Icons.receipt_long_outlined,
                          'GST: ${bid.gstNumber}',
                        ),
                    ],
                    const SizedBox(height: 10),
                    // Action buttons
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: [
                        // Details dialog
                        OutlinedButton.icon(
                          icon: const Icon(Icons.info_outline, size: 14),
                          label: const Text('Details'),
                          onPressed: () => showDialog<void>(
                            context: context,
                            builder: (_) => AlertDialog(
                              title: Text(bid.product),
                              content: SingleChildScrollView(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    _kv('Bid ID', bid.id),
                                    _kv('Amount', money(bid.amount)),
                                    _kv('Discount', money(bid.discountAmount)),
                                    _kv('Delivery', '${bid.deliveryTime}'),
                                    _kv('Warranty', bid.warrantyText),
                                    _kv('Status', bid.status.toUpperCase()),
                                    _kv('Dealer', bid.dealer),
                                    if (bid.freeGifts.isNotEmpty)
                                      _kv('Free Gifts', bid.freeGifts),
                                    if (bid.notes.isNotEmpty)
                                      _kv('Notes', bid.notes),
                                    if (bid.status == 'won' ||
                                        bid.status == 'completed') ...[
                                      const Divider(),
                                      const Text(
                                        'Dealer Contact',
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: Color(0xFF2563EB),
                                        ),
                                      ),
                                      if (bid.ownerName.isNotEmpty)
                                        _kv('Owner', bid.ownerName),
                                      if (bid.dealerPhone.isNotEmpty)
                                        _kv('Phone', bid.dealerPhone),
                                      if (bid.dealerEmail.isNotEmpty)
                                        _kv('Email', bid.dealerEmail),
                                      if (bid.businessAddress.isNotEmpty)
                                        _kv('Address', bid.businessAddress),
                                      if (bid.gstNumber.isNotEmpty)
                                        _kv('GST', bid.gstNumber),
                                    ],
                                  ],
                                ),
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(context),
                                  child: const Text('Close'),
                                ),
                              ],
                            ),
                          ),
                        ),
                        // Report button for bid-bound dispute flow
                        if (onReport != null && bid.status != 'lost')
                          OutlinedButton.icon(
                            icon: const Icon(
                              Icons.flag_outlined,
                              size: 14,
                              color: Colors.red,
                            ),
                            label: const Text(
                              'Report',
                              style: TextStyle(color: Colors.red, fontSize: 12),
                            ),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: Colors.red),
                            ),
                            onPressed: () => onReport!(bid),
                          ),
                        FilledButton.tonal(
                          onPressed: () => onRebid(bid),
                          child: const Text('Rebid'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(),
    );
  }

  void _showDealerReveal(BuildContext context, BidRecord bid) {
    showLiveBidDialog(context, bid, isMine: bid.isMine);
  }

  void _showBuyerReveal(BuildContext context, BidRecord bid) {
    showLiveBidDialog(context, bid, isMine: bid.isMine);
  }

  Widget _infoRow(IconData icon, String text) => Padding(
    padding: const EdgeInsets.only(top: 3),
    child: Row(
      children: [
        Icon(icon, size: 14, color: Colors.grey),
        const SizedBox(width: 6),
        Flexible(child: Text(text, style: const TextStyle(fontSize: 13))),
      ],
    ),
  );

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 82,
          child: Text(
            '$label:',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
        ),
        Flexible(child: Text(value, style: const TextStyle(fontSize: 13))),
      ],
    ),
  );
}

class CartPage extends StatelessWidget {
  const CartPage({
    super.key,
    required this.cart,
    required this.products,
    required this.onBid,
    required this.onAdd,
    required this.onRemove,
    required this.onContinue,
  });

  final Map<String, dynamic> cart;
  final List<ProductItem> products;
  final Future<void> Function(ProductItem product, int quantity) onBid;
  final Future<void> Function(ProductItem product) onAdd;
  final Future<void> Function(String itemId) onRemove;
  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) {
    final items = List<Map<String, dynamic>>.from(cart['items'] ?? []);
    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
            title: 'Cart',
            subtitle:
                'Products added by the buyer. Adjust quantity, remove items, or start bidding.',
            icon: Icons.shopping_cart_outlined,
            trailing: OutlinedButton(
              onPressed: onContinue,
              child: const Text('Continue Browsing'),
            ),
          ),
          const SizedBox(height: 12),
          DataPanel(
            title: '${items.length} cart items',
            children: items.isEmpty
                ? [const Text('Cart is empty. Add products from catalog.')]
                : items.map((item) {
                    final productId = item['product_id']?.toString() ?? '';
                    ProductItem? product;
                    for (final candidate in products) {
                      if (candidate.id == productId) {
                        product = candidate;
                        break;
                      }
                    }
                    final selectedProduct = product;
                    return ListTile(
                      title: Text(item['name']?.toString() ?? ''),
                      subtitle: Text(
                        'Quantity ${item['quantity']} | ${item['brand'] ?? ''} ${item['model'] ?? ''}',
                      ),
                      leading: const Icon(Icons.shopping_bag_outlined),
                      trailing: Wrap(
                        spacing: 6,
                        children: [
                          IconButton(
                            tooltip: 'Remove item',
                            onPressed: () => onRemove(item['id'].toString()),
                            icon: const Icon(Icons.remove_circle_outline),
                          ),
                          IconButton(
                            tooltip: 'Quantity +',
                            onPressed: product == null
                                ? null
                                : () => onAdd(product!),
                            icon: const Icon(Icons.add_circle_outline),
                          ),
                          OutlinedButton(
                            onPressed: () => onRemove(item['id'].toString()),
                            child: const Text('Remove'),
                          ),
                          FilledButton(
                            onPressed: selectedProduct == null
                                ? null
                                : () => onBid(
                                    selectedProduct,
                                    int.tryParse(item['quantity'].toString()) ??
                                        1,
                                  ),
                            child: const Text('Start Bid'),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
          ),
        ],
      ),
    );
  }
}

class BidHistoryPage extends StatefulWidget {
  const BidHistoryPage({
    super.key,
    required this.bids,
    required this.payments,
    required this.logs,
    required this.onPaymentStatus,
    required this.onExport,
    this.initialStatusFilter,
    this.initialCommissionFilter,
    this.showRevenueBreakdown = false,
  });

  final List<BidRecord> bids;
  final List<Map<String, dynamic>> payments;
  final List<Map<String, dynamic>> logs;
  final Future<void> Function(String commissionId, String status)
  onPaymentStatus;
  final VoidCallback onExport;
  final String? initialStatusFilter;
  final String? initialCommissionFilter;
  final bool showRevenueBreakdown;

  @override
  State<BidHistoryPage> createState() => _BidHistoryPageState();
}

class _BidHistoryPageState extends State<BidHistoryPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _searchController = TextEditingController();
  String? _statusFilter;
  String? _commissionFilter;

  // Selected bid detail modal state
  BidRecord? _selectedBid;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _statusFilter = widget.initialStatusFilter;
    _commissionFilter = widget.initialCommissionFilter;

    // Automatically switch tabs if commission filtering is active
    if (widget.initialCommissionFilter != null) {
      _tabController.index = 1;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 1. Search & Filter Bid records
    final filteredBids = widget.bids.where((b) {
      final query = _searchController.text.trim().toLowerCase();
      if (query.isNotEmpty) {
        final matchesProd = b.product.toLowerCase().contains(query);
        final matchesDealer = b.dealer.toLowerCase().contains(query);
        final matchesId = b.id.toLowerCase().contains(query);
        if (!matchesProd && !matchesDealer && !matchesId) return false;
      }
      if (_statusFilter != null) {
        final selected = _statusFilter!.toLowerCase();
        final actual = b.requestStatus == 'cancelled' ? 'cancelled' : b.status;
        if (selected == 'winning' || selected == 'completed') {
          if (actual != 'won') return false;
        } else if (selected == 'active') {
          if (actual != 'active' && actual != 'updated') return false;
        } else if (actual != selected) {
          return false;
        }
      }
      return true;
    }).toList();

    // 2. Search & Filter Commissions (payments)
    final filteredPayments = widget.payments.where((p) {
      final query = _searchController.text.trim().toLowerCase();
      if (query.isNotEmpty) {
        final prod = (p['product'] ?? '').toString().toLowerCase();
        final dealer = (p['dealer'] ?? '').toString().toLowerCase();
        if (!prod.contains(query) && !dealer.contains(query)) return false;
      }
      if (_commissionFilter != null &&
          p['payment_status']?.toString().toLowerCase() !=
              _commissionFilter!.toLowerCase()) {
        return false;
      }
      return true;
    }).toList();

    // 3. Filter logs
    final filteredLogs = widget.logs.where((l) {
      final query = _searchController.text.trim().toLowerCase();
      if (query.isNotEmpty) {
        final act = (l['action'] ?? '').toString().toLowerCase();
        final ent = (l['entity_type'] ?? '').toString().toLowerCase();
        if (!act.contains(query) && !ent.contains(query)) return false;
      }
      return true;
    }).toList();

    return PageScaffold(
      scrollable: false,
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeader(
                title: 'Bids History & Financial Auditing',
                subtitle:
                    'Auditing trail for bid requests, commission payments, and low-level action logs.',
                icon: Icons.gavel_outlined,
                trailing: OutlinedButton.icon(
                  onPressed: widget.onExport,
                  icon: const Icon(Icons.download_outlined),
                  label: const Text('Export Records'),
                ),
              ),
              const SizedBox(height: 12),
              // Search input
              TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText:
                      'Search within history (products, dealer/buyer names, IDs, actions)...',
                ),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              // Optional Revenue Breakdown Card
              if (widget.showRevenueBreakdown) _buildRevenueBreakdownCard(),
              // Tab Header
              TabBar(
                controller: _tabController,
                tabs: const [
                  Tab(text: 'Bid History'),
                  Tab(text: 'Commissions & Payments'),
                  Tab(text: 'Audit Logs'),
                ],
              ),
              const SizedBox(height: 12),
              // Tab View Contents
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildBidHistoryTab(filteredBids),
                    _buildCommissionsTab(filteredPayments),
                    _buildAuditLogsTab(filteredLogs),
                  ],
                ),
              ),
            ],
          ),
          if (_selectedBid != null) _buildBidDetailsOverlay(),
        ],
      ),
    );
  }

  Widget _buildRevenueBreakdownCard() {
    double totalCommission = 0;
    double paidCommission = 0;
    double pendingCommission = 0;
    for (final p in widget.payments) {
      final amt = parseDouble(p['amount']);
      totalCommission += amt;
      if (p['payment_status'] == 'paid') {
        paidCommission += amt;
      } else {
        pendingCommission += amt;
      }
    }
    return Card(
      color: const Color(0xFFF0FDF4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFBBF7D0)),
      ),
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Revenue & Commission Summary',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: Color(0xFF166534),
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 24,
              runSpacing: 10,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Total Commission Due',
                      style: TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                    Text(
                      money(totalCommission),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Color(0xFF166534),
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Collected Revenue (Paid)',
                      style: TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                    Text(
                      money(paidCommission),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Color(0xFF16A34A),
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Pending Commission (Outstanding)',
                      style: TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                    Text(
                      money(pendingCommission),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Colors.orange,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBidHistoryTab(List<BidRecord> filtered) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Filter status: '),
            DropdownButton<String>(
              value: _statusFilter,
              hint: const Text('All'),
              onChanged: (val) => setState(() => _statusFilter = val),
              items:
                  [
                        'All',
                        'Winning',
                        'Active',
                        'Updated',
                        'Lost',
                        'Expired',
                        'Withdrawn',
                        'Completed',
                        'Cancelled',
                      ]
                      .map(
                        (e) => DropdownMenuItem(
                          value: e == 'All' ? null : e,
                          child: Text(e),
                        ),
                      )
                      .toList(),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: filtered.isEmpty
              ? const Center(child: Text('No matching bid records.'))
              : ListView.builder(
                  itemCount: filtered.length,
                  itemBuilder: (context, idx) {
                    final bid = filtered[idx];
                    return Card(
                      child: ListTile(
                        onTap: () => setState(() => _selectedBid = bid),
                        title: Text(
                          bid.product,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Text(
                          'Dealer: ${bid.dealer} | Amount: ${money(bid.amount)} | Code: ${bid.id}',
                        ),
                        leading: CircleAvatar(
                          backgroundColor: const Color(0xFFEDE9FE),
                          child: Icon(
                            Icons.gavel,
                            color: Theme.of(context).colorScheme.primary,
                            size: 18,
                          ),
                        ),
                        trailing: Wrap(
                          spacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            StatusPill(text: bid.status),
                            const Icon(
                              Icons.arrow_forward_ios,
                              size: 14,
                              color: Colors.grey,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildCommissionsTab(List<Map<String, dynamic>> filtered) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Filter payment status: '),
            DropdownButton<String>(
              value: _commissionFilter,
              hint: const Text('All'),
              onChanged: (val) => setState(() => _commissionFilter = val),
              items: ['All', 'pending', 'paid', 'failed', 'waived', 'refunded']
                  .map(
                    (e) => DropdownMenuItem(
                      value: e == 'All' ? null : e,
                      child: Text(e.toUpperCase()),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: filtered.isEmpty
              ? const Center(child: Text('No commission/payment logs.'))
              : ListView.builder(
                  itemCount: filtered.length,
                  itemBuilder: (context, idx) {
                    final p = filtered[idx];
                    final amt = parseDouble(p['amount']);
                    final id = p['id']?.toString() ?? '';
                    return Card(
                      child: ListTile(
                        title: Text(
                          p['product']?.toString() ?? 'Commission Payment',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Text(
                          'Dealer: ${p['dealer'] ?? ''} | Date: ${p['created_at']}',
                        ),
                        leading: CircleAvatar(
                          backgroundColor: const Color(0xFFF5F3FF),
                          child: Icon(
                            Icons.currency_rupee,
                            color: Theme.of(context).colorScheme.primary,
                            size: 18,
                          ),
                        ),
                        trailing: Wrap(
                          spacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              money(amt),
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                            StatusPill(
                              text: p['payment_status']?.toString() ?? '',
                            ),
                            PopupMenuButton<String>(
                              tooltip: 'Update status',
                              onSelected: (status) =>
                                  widget.onPaymentStatus(id, status),
                              itemBuilder: (_) =>
                                  [
                                        'pending',
                                        'paid',
                                        'failed',
                                        'waived',
                                        'refunded',
                                      ]
                                      .map(
                                        (s) => PopupMenuItem(
                                          value: s,
                                          child: Text(s.toUpperCase()),
                                        ),
                                      )
                                      .toList(),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildAuditLogsTab(List<Map<String, dynamic>> filtered) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Low-level Platform Activity Trails',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 13,
            color: Colors.grey,
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: filtered.isEmpty
              ? const Center(child: Text('No audit logs recorded.'))
              : ListView.builder(
                  itemCount: filtered.length,
                  itemBuilder: (context, idx) {
                    final log = filtered[idx];
                    final meta = Map<String, dynamic>.from(
                      jsonDecode(log['metadata_json']?.toString() ?? '{}'),
                    );
                    return Card(
                      child: ListTile(
                        dense: true,
                        title: Text(
                          '[${log['entity_type']?.toString().toUpperCase()}] ${log['action']}',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Text(
                          'Metadata: $meta | Date: ${log['created_at']}',
                        ),
                        leading: const Icon(
                          Icons.receipt_long_outlined,
                          size: 18,
                        ),
                        trailing: Text(
                          log['id']?.toString() ?? '',
                          style: const TextStyle(
                            fontSize: 10,
                            color: Colors.grey,
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildBidDetailsOverlay() {
    final bid = _selectedBid!;
    // Locate linked reports or timeline
    final linkedPayments = widget.payments
        .where((p) => p['bid_id']?.toString() == bid.id)
        .toList();

    return Container(
      color: Colors.white,
      width: double.infinity,
      height: double.infinity,
      child: Column(
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFFF5F3FF),
              border: Border(bottom: BorderSide(color: Color(0xFFE9D5FF))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        bid.product,
                        style: const TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 18,
                          color: Color(0xFF3B0764),
                        ),
                      ),
                      Text(
                        'Bid ID: ${bid.id}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Close details',
                  icon: const Icon(Icons.close),
                  onPressed: () => setState(() => _selectedBid = null),
                ),
              ],
            ),
          ),
          // Scrollable Body
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Detail cards
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Bid Specifications & Parameters',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                              color: Color(0xFF3B0764),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text('Dealer: ${bid.dealer}'),
                          Text('Buyer: ${bid.buyer}'),
                          Text('Bid Amount: ${money(bid.amount)}'),
                          Text('Bid Status: ${bid.status.toUpperCase()}'),
                          Text('Ends/Ended At: ${bid.endsAt}'),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Location markers map panel
                  const Text(
                    'Delivery Location Marker',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: Color(0xFF3B0764),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 240,
                    child: LocationMapPanel(
                      title: 'Delivery Location Marker',
                      subtitle: 'Delivery Target Area: Mumbai',
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Linked payments / invoice details
                  DataPanel(
                    title: 'Linked Financial Invoices',
                    children: linkedPayments.isEmpty
                        ? [
                            const Text(
                              'No commission payment logs associated with this bid.',
                            ),
                          ]
                        : linkedPayments
                              .map(
                                (p) => ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.receipt_outlined),
                                  title: Text(
                                    'Commission: ${money(parseDouble(p['amount']))}',
                                  ),
                                  subtitle: Text(
                                    'Status: ${p['payment_status']} | ID: ${p['id']}',
                                  ),
                                ),
                              )
                              .toList(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AnalyticsPage extends StatelessWidget {
  const AnalyticsPage({
    super.key,
    required this.dashboard,
    required this.products,
    required this.bids,
    required this.payments,
  });
  final Map<String, dynamic> dashboard;
  final List<ProductItem> products;
  final List<BidRecord> bids;
  final List<Map<String, dynamic>> payments;
  @override
  Widget build(BuildContext context) => DashboardPage(
    title: 'Analytics',
    subtitle:
        'Revenue trends, dealer performance, buyer activity, category demand, and commission health.',
    dashboard: dashboard,
    notifications: const [],
    extra: const [
      DataPanel(
        title: 'MVP visual summaries',
        children: [
          _ProgressRow(label: 'Winning percentage', value: 0.64),
          _ProgressRow(label: 'Dealer performance', value: 0.78),
          _ProgressRow(label: 'Buyer activity', value: 0.52),
          _ProgressRow(label: 'Pending payments', value: 0.31),
        ],
      ),
    ],
  );
}

class ReportsPage extends StatelessWidget {
  const ReportsPage({
    super.key,
    required this.reports,
    required this.onExport,
    required this.userRole,
    required this.currentUserId,
    this.selectedDetails,
    this.messages = const [],
    this.messageController,
    this.recipientGroup = 'both',
    this.onDetails,
    this.onCloseDetails,
    this.onSendMessage,
    this.onRecipientGroupChanged,
    this.onUpdateReportStatus,
    this.onRequestClosure,
    this.onClosureDecision,
  });

  final List<Map<String, dynamic>> reports;
  final VoidCallback onExport;
  final String userRole;
  final String currentUserId;
  final Map<String, dynamic>? selectedDetails;
  final List<Map<String, dynamic>> messages;
  final TextEditingController? messageController;
  final String recipientGroup;
  final ValueChanged<String>? onDetails;
  final VoidCallback? onCloseDetails;
  final VoidCallback? onSendMessage;
  final ValueChanged<String>? onRecipientGroupChanged;
  final Future<void> Function(String reportId, String status, String note)?
  onUpdateReportStatus;
  final Future<void> Function(String reportId, String reason)? onRequestClosure;
  final Future<void> Function(String reportId, String status, String note)?
  onClosureDecision;

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      scrollable: false,
      child: selectedDetails != null
          ? _buildConversationOverlay(context)
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SectionHeader(
                  title: 'Reports & Dispute Center',
                  subtitle:
                      'Moderate dispute logs, selective broadcast message threads, and resolve client complaints.',
                  icon: Icons.report_outlined,
                  trailing: OutlinedButton.icon(
                    onPressed: onExport,
                    icon: const Icon(Icons.download_outlined),
                    label: const Text('Export CSV'),
                  ),
                ),
                const SizedBox(height: 12),
                Expanded(
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${reports.length} report records',
                            style: const TextStyle(
                              fontWeight: FontWeight.w900,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Expanded(
                            child: reports.isEmpty
                                ? const Center(child: Text('No reports filed.'))
                                : ListView.builder(
                                    itemCount: reports.length,
                                    itemBuilder: (context, idx) {
                                      final row = reports[idx];
                                      final id = row['id']?.toString() ?? '';
                                      return Card(
                                        margin: const EdgeInsets.only(
                                          bottom: 10,
                                        ),
                                        child: ListTile(
                                          onTap: onDetails == null
                                              ? null
                                              : () => onDetails!(id),
                                          leading: const CircleAvatar(
                                            backgroundColor: Color(0xFFFEE2E2),
                                            child: Icon(
                                              Icons.report_problem,
                                              color: Colors.red,
                                              size: 18,
                                            ),
                                          ),
                                          title: Text(
                                            row['reason']?.toString() ??
                                                'General Dispute',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                          subtitle: Text(
                                            [
                                              'Reporter: ${row['reporter']}',
                                              'Reported Party: ${row['reported_party']}',
                                              if ((row['closure_requested_status'] ??
                                                          'none')
                                                      .toString() ==
                                                  'requested')
                                                'Requested by: ${row['closure_requested_by_name'] ?? 'Reporter'}',
                                              if ((row['closure_reason'] ?? '')
                                                  .toString()
                                                  .isNotEmpty)
                                                'Reason: ${row['closure_reason']}',
                                              if ((row['closure_requested_status'] ??
                                                          'none')
                                                      .toString() ==
                                                  'requested')
                                                'Requested Status: Resolved by Buyer/Dealer',
                                            ].join(' | '),
                                          ),
                                          trailing: Wrap(
                                            spacing: 6,
                                            crossAxisAlignment:
                                                WrapCrossAlignment.center,
                                            children: [
                                              StatusPill(
                                                text:
                                                    row['status']?.toString() ??
                                                    'open',
                                              ),
                                              const Icon(
                                                Icons.arrow_forward_ios,
                                                size: 14,
                                                color: Colors.grey,
                                              ),
                                            ],
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildConversationOverlay(BuildContext context) {
    final report = selectedDetails!;
    final id = report['id']?.toString() ?? '';
    final reason = report['reason']?.toString() ?? 'Dispute';
    final reportStatus = report['status']?.toString() ?? '';
    final closureStatus =
        report['closure_requested_status']?.toString() ?? 'none';
    final closureReason = report['closure_reason']?.toString() ?? '';
    final closureRequestedBy =
        report['closure_requested_by_name']?.toString() ?? '';

    final bidId = report['bid_id'];
    final relatedReports = reports.where((r) => r['bid_id'] == bidId).toList();

    return Container(
      color: Colors.white,
      width: double.infinity,
      height: double.infinity,
      child: Column(
        children: [
          // Overlay Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFFF5F3FF),
              border: Border(bottom: BorderSide(color: Color(0xFFE9D5FF))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        reason,
                        style: const TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 18,
                          color: Color(0xFF3B0764),
                        ),
                      ),
                      Text(
                        'Report ID: $id | Bid ID: ${report['bid_id'] ?? 'N/A'} | Status: ${reportStatus.toUpperCase()}',
                        style: const TextStyle(fontSize: 12),
                      ),
                      if (closureStatus != 'none') ...[
                        const SizedBox(height: 4),
                        Text(
                          'Closure request: $closureStatus | Requested by: ${closureRequestedBy.isEmpty ? 'Reporter' : closureRequestedBy}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (closureReason.isNotEmpty)
                          Text(
                            'Reason: $closureReason',
                            style: const TextStyle(fontSize: 12),
                          ),
                      ],
                    ],
                  ),
                ),
                if (userRole == 'admin' &&
                    report['contacts_unlocked'] == 1 &&
                    bidChatSession != null)
                  TextButton(
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Winning bid conversation'),
                        content: SizedBox(
                          width: 520,
                          child: SingleChildScrollView(
                            child: BidConversation(
                              bidId: bidId.toString(),
                              user: bidChatSession!,
                            ),
                          ),
                        ),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(ctx),
                            child: const Text('Close'),
                          ),
                        ],
                      ),
                    ),
                    child: const Text('View bid conversation'),
                  ),
                if (onUpdateReportStatus != null)
                  DropdownButton<String>(
                    underline: const SizedBox(),
                    icon: const Icon(Icons.edit_note, color: Color(0xFF6D28D9)),
                    hint: const Text('Update Status'),
                    onChanged: (status) {
                      if (status != null) {
                        _showStatusChangeDialog(context, id, status);
                      }
                    },
                    items: ['resolved', 'rejected', 'closed', 'escalated']
                        .map(
                          (s) => DropdownMenuItem(
                            value: s,
                            child: Text(s.toUpperCase()),
                          ),
                        )
                        .toList(),
                  ),
                if (onRequestClosure != null &&
                    reportStatus != 'closed' &&
                    report['reporter_id'] == currentUserId)
                  OutlinedButton.icon(
                    onPressed: () => _showClosureRequestDialog(context, id),
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('Cancel Report'),
                  ),
                if (onClosureDecision != null &&
                    closureStatus == 'requested') ...[
                  FilledButton.tonal(
                    onPressed: () =>
                        _showClosureDecisionDialog(context, id, 'approved'),
                    child: const Text('Approve Closure'),
                  ),
                  OutlinedButton(
                    onPressed: () =>
                        _showClosureDecisionDialog(context, id, 'rejected'),
                    child: const Text('Reject'),
                  ),
                ],
                const SizedBox(width: 8),
                IconButton(
                  tooltip: 'Close Conversation',
                  icon: const Icon(Icons.close),
                  onPressed: onCloseDetails,
                ),
              ],
            ),
          ),
          if (relatedReports.length > 1)
            Container(
              width: double.infinity,
              decoration: const BoxDecoration(
                color: Color(0xFFFEF2F2),
                border: Border(bottom: BorderSide(color: Color(0xFFFCA5A5))),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              margin: const EdgeInsets.only(bottom: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(
                        Icons.warning_amber_rounded,
                        color: Colors.red,
                        size: 16,
                      ),
                      SizedBox(width: 6),
                      Text(
                        'Note: Both Buyer and Dealer have reported this Bid.',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.red,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  ...relatedReports.map((r) {
                    final rId = r['id'];
                    final isCurrent = rId == id;
                    return Padding(
                      padding: const EdgeInsets.only(left: 22, top: 2),
                      child: InkWell(
                        onTap: isCurrent || onDetails == null
                            ? null
                            : () => onDetails!(rId),
                        child: Text(
                          '- Report by ${r['reporter']}: "${r['reason']}" (${r['status']})${isCurrent ? ' [Currently Viewing]' : ' [Click to View Chat]'}',
                          style: TextStyle(
                            fontSize: 12,
                            color: isCurrent
                                ? Colors.black87
                                : Colors.blue[800],
                            decoration: isCurrent
                                ? TextDecoration.none
                                : TextDecoration.underline,
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          // Product & Order Details Banner (Collapsible/compact metadata card)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF9FAFB),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE5E7EB)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Flexible(
                      child: Text(
                        'Product: ${report['product'] ?? 'N/A'}',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    if (report['product_brand'] != null &&
                        report['product_brand'].toString().isNotEmpty)
                      Text(
                        'Brand: ${report['product_brand']}',
                        style: TextStyle(
                          color: Colors.grey[800],
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Quantity: ${report['quantity'] ?? 1} pcs',
                      style: const TextStyle(fontSize: 13),
                    ),
                    Text(
                      'Deal Amount: ${money(parseDouble(report['bid_amount']))}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF16A34A),
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Warranty: ${report['warranty'] ?? 'N/A'}',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    Text(
                      'Delivery: ${report['delivery'] ?? 'N/A'} days',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
                if (report['description'] != null &&
                    report['description'].toString().isNotEmpty) ...[
                  const Divider(height: 12),
                  const Text(
                    'Dispute Description:',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${report['description']}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ],
            ),
          ),
          // Thread Messages List
          Expanded(
            child: messages.isEmpty
                ? const Center(child: Text('No messages in this chat yet.'))
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final msg = messages[index];
                      final isAgent =
                          msg['sender_role'] == 'admin' ||
                          msg['sender_role'] == 'agent';
                      final sender = msg['sender_name']?.toString() ?? 'System';
                      final text = msg['message']?.toString() ?? '';
                      final time = msg['created_at']?.toString() ?? '';
                      final group =
                          msg['recipient_group']?.toString() ?? 'both';

                      return Align(
                        alignment: isAgent
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 6),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isAgent
                                ? const Color(0xFFF5F3FF)
                                : const Color(0xFFF3F4F6),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isAgent
                                  ? const Color(0xFFDDD6FE)
                                  : const Color(0xFFE5E7EB),
                            ),
                          ),
                          constraints: const BoxConstraints(maxWidth: 500),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    sender,
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                      color: isAgent
                                          ? const Color(0xFF6D28D9)
                                          : Colors.black87,
                                    ),
                                  ),
                                  Text(
                                    'To: ${group.toUpperCase()}',
                                    style: const TextStyle(
                                      fontSize: 10,
                                      color: Colors.grey,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(text, style: const TextStyle(fontSize: 13)),
                              const SizedBox(height: 4),
                              Align(
                                alignment: Alignment.bottomRight,
                                child: Text(
                                  time,
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: Colors.grey,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          // Selective Broadcast message box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Color(0xFFE5E7EB))),
            ),
            child: Row(
              children: [
                // Broadcast Dropdown
                DropdownButton<String>(
                  value: recipientGroup,
                  onChanged: onRecipientGroupChanged == null
                      ? null
                      : (val) {
                          if (val != null) onRecipientGroupChanged!(val);
                        },
                  items: userRole == 'admin'
                      ? const [
                          DropdownMenuItem(value: 'both', child: Text('Both')),
                          DropdownMenuItem(
                            value: 'buyer',
                            child: Text('Buyer Only'),
                          ),
                          DropdownMenuItem(
                            value: 'dealer',
                            child: Text('Dealer Only'),
                          ),
                        ]
                      : userRole == 'buyer'
                      ? const [
                          DropdownMenuItem(
                            value: 'both',
                            child: Text('To Everyone (Public)'),
                          ),
                          DropdownMenuItem(
                            value: 'admin',
                            child: Text('To Admin Only (Private)'),
                          ),
                        ]
                      : const [
                          DropdownMenuItem(
                            value: 'both',
                            child: Text('To Everyone (Public)'),
                          ),
                          DropdownMenuItem(
                            value: 'admin',
                            child: Text('To Admin Only (Private)'),
                          ),
                        ],
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: messageController,
                    decoration: const InputDecoration(
                      hintText: 'Type your message/resolution details here...',
                    ),
                    onSubmitted: onSendMessage == null
                        ? null
                        : (_) => onSendMessage!(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send, color: Color(0xFF6D28D9)),
                  onPressed: onSendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showStatusChangeDialog(
    BuildContext context,
    String reportId,
    String status,
  ) {
    final noteController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Change Report Status to ${status.toUpperCase()}?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Add an internal moderation resolution note:'),
            const SizedBox(height: 8),
            TextField(
              controller: noteController,
              decoration: const InputDecoration(hintText: 'Note details...'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: onUpdateReportStatus == null
                ? null
                : () {
                    Navigator.pop(ctx);
                    onUpdateReportStatus!(
                      reportId,
                      status,
                      noteController.text.trim(),
                    );
                  },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  void _showClosureRequestDialog(BuildContext context, String reportId) {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Report'),
        content: TextField(
          controller: reasonController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Cancellation reason',
            hintText: 'Explain why you are cancelling this report.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: onRequestClosure == null
                ? null
                : () {
                    final reason = reasonController.text.trim();
                    if (reason.length < 3) return;
                    Navigator.pop(ctx);
                    onRequestClosure!(reportId, reason);
                  },
            child: const Text('Cancel Report'),
          ),
        ],
      ),
    );
  }

  void _showClosureDecisionDialog(
    BuildContext context,
    String reportId,
    String status,
  ) {
    final noteController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${status == 'approved' ? 'Approve' : 'Reject'} Closure?'),
        content: TextField(
          controller: noteController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Admin note',
            hintText: 'Optional reason for this decision.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: onClosureDecision == null
                ? null
                : () {
                    Navigator.pop(ctx);
                    onClosureDecision!(
                      reportId,
                      status,
                      noteController.text.trim(),
                    );
                  },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }
}

class SettingsPage extends StatefulWidget {
  const SettingsPage({
    super.key,
    required this.settings,
    this.onSaveSetting,
    this.status = 'active',
    this.token = '',
  });

  final Map<String, dynamic> settings;
  final Future<void> Function(String key, Map<String, dynamic> val)?
  onSaveSetting;
  final String status;
  final String token;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Controllers for Commission Rules
  final _commissionPercentage = TextEditingController();

  // Controllers for Location Rules
  final _locationMaxRadius = TextEditingController();

  // Controllers for Bid Rules
  final _bidExpiryHours = TextEditingController();
  final _bidMinimumHours = TextEditingController();
  final _bidMaximumHours = TextEditingController();
  final _bidMaximumDealers = TextEditingController();
  final _bidMinIncrement = TextEditingController();

  // Controllers for Dealer Rules
  final _dealerMinRating = TextEditingController();

  // Controllers for Notification Rules

  // Controllers for Categories
  final _categoriesInput = TextEditingController();

  List<Map<String, dynamic>> _categoryTree = [];
  bool _loadingCategories = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
    _populateFields();
    _loadCategories();
  }

  Future<void> _loadCategories() async {
    if (widget.token.isEmpty) {
      setState(() => _loadingCategories = false);
      return;
    }
    try {
      final list = await ApiClient().getCategories(widget.token);
      if (mounted) {
        setState(() {
          _categoryTree = list;
          _loadingCategories = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loadingCategories = false);
      }
    }
  }

  Future<void> _addCategoryDialog(String? parentId) async {
    final nameCtrl = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(parentId == null ? 'Add Category' : 'Add Subcategory'),
        content: TextField(
          controller: nameCtrl,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              Navigator.pop(context);
              try {
                await ApiClient().createCategory(
                  widget.token,
                  nameCtrl.text.trim(),
                  parentId,
                );
                _loadCategories();
              } catch (e) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Failed: $e')));
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Future<void> _editCategoryDialog(
    String id,
    String currentName,
    String? parentId,
  ) async {
    final nameCtrl = TextEditingController(text: currentName);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Category / Item'),
        content: TextField(
          controller: nameCtrl,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              Navigator.pop(context);
              try {
                await ApiClient().updateCategory(
                  widget.token,
                  id,
                  nameCtrl.text.trim(),
                  parentId,
                );
                _loadCategories();
              } catch (e) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Failed: $e')));
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteCategory(String id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Delete'),
        content: const Text(
          'Are you sure you want to delete this category/item? Doing so might leave child records or products orphaned.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      try {
        await ApiClient().deleteCategory(widget.token, id);
        _loadCategories();
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to delete: $e')));
      }
    }
  }

  void _populateFields() {
    // 1. Commission
    final comm = Map<String, dynamic>.from(widget.settings['commission'] ?? {});
    _commissionPercentage.text =
        (comm['global_percent'] ?? comm['percentage'] ?? '5.0').toString();

    // 2. Location Rules
    final loc = Map<String, dynamic>.from(
      widget.settings['location_rules'] ?? {},
    );
    _locationMaxRadius.text = (loc['max_radius_km'] ?? '50.0').toString();

    // 3. Bid Rules
    final bid = Map<String, dynamic>.from(widget.settings['bid_rules'] ?? {});
    _bidExpiryHours.text =
        (bid['expiry_hours'] ?? bid['bid_expiry_hours'] ?? '24').toString();
    _bidMinimumHours.text = (bid['min_time_hours'] ?? 1 / 60).toString();
    _bidMaximumHours.text = (bid['max_time_hours'] ?? 72).toString();
    _bidMaximumDealers.text = (bid['max_dealers'] ?? 10).toString();
    _bidMinIncrement.text = (bid['min_bidding_increment'] ?? '0.0').toString();

    // 4. Dealer Rules
    final dealer = Map<String, dynamic>.from(
      widget.settings['dealer_rules'] ?? {},
    );
    _dealerMinRating.text = (dealer['min_rating_threshold'] ?? '0.0')
        .toString();

    // 6. Categories (comma separated or raw list)
    final cats = widget.settings['categories'] is Map
        ? List<dynamic>.from(
            (widget.settings['categories'] as Map)['list'] ?? [],
          )
        : List<dynamic>.from(widget.settings['categories'] ?? []);
    _categoriesInput.text = cats.join(', ');
  }

  @override
  void didUpdateWidget(covariant SettingsPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (jsonEncode(oldWidget.settings) != jsonEncode(widget.settings))
      _populateFields();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _commissionPercentage.dispose();
    _locationMaxRadius.dispose();
    _bidExpiryHours.dispose();
    _bidMinimumHours.dispose();
    _bidMaximumHours.dispose();
    _bidMaximumDealers.dispose();
    _bidMinIncrement.dispose();
    _dealerMinRating.dispose();
    _categoriesInput.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.onSaveSetting == null) {
      return PageScaffold(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if ([
              'held',
              'flagged',
              'suspended',
              'banned',
            ].contains(widget.status))
              WarningBanner(status: widget.status),
            const SectionHeader(
              title: 'Platform Rules & Location Settings',
              subtitle:
                  'Subscription billing, service radius, bid expiry, dealer eligibility, categories and location rules.',
              icon: Icons.tune_outlined,
            ),
            const SizedBox(height: 12),
            DataPanel(
              title: 'Current settings',
              children: widget.settings.isEmpty
                  ? [const Text('Default settings are active.')]
                  : widget.settings.entries
                        .map(
                          (entry) => ListTile(
                            title: Text(_title(entry.key)),
                            subtitle: Text(entry.value.toString()),
                          ),
                        )
                        .toList(),
            ),
          ],
        ),
      );
    }

    return PageScaffold(
      scrollable: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeader(
            title: 'Platform Rules & Settings Configuration',
            subtitle:
                'Manage bidding duration, service limits, dealer eligibility and product categories.',
            icon: Icons.tune_outlined,
          ),
          const SizedBox(height: 12),
          // Tab bar headers
          TabBar(
            controller: _tabController,
            isScrollable: true,
            tabs: const [
              Tab(text: 'Billing'),
              Tab(text: 'Location Rules'),
              Tab(text: 'Bid Rules'),
              Tab(text: 'Dealer Rules'),
              Tab(text: 'Notifications'),
              Tab(text: 'Categories'),
            ],
          ),
          const SizedBox(height: 16),
          // Tab bar body views
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildCommissionTab(),
                _buildLocationRulesTab(),
                _buildBidRulesTab(),
                _buildDealerRulesTab(),
                _buildNotificationsTab(),
                _buildCategoriesTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommissionTab() {
    return const DataPanel(
      title: 'Subscription billing',
      children: [
        Text(
          'Dealers participate with an active subscription. Selecting a winning bid adds no commission. Contacts and private chat open immediately for the buyer and winning dealer. Historical payment records remain in the audit history.',
        ),
      ],
    );
  }

  Widget _buildLocationRulesTab() {
    return SingleChildScrollView(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Location Limits & Rules',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF3B0764),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _locationMaxRadius,
                decoration: const InputDecoration(
                  labelText: 'Maximum Service Area Radius (km)',
                  hintText: 'e.g. 50.0',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  widget.onSaveSetting!('location_rules', {
                    'max_radius_km': parseDouble(_locationMaxRadius.text),
                  });
                },
                child: const Text('Save Location Rules'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBidRulesTab() {
    return SingleChildScrollView(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Bidding Expiry & Match Rules',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF3B0764),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _bidExpiryHours,
                decoration: const InputDecoration(
                  labelText: 'Bid Expiry Window (hours)',
                  hintText: 'e.g. 24',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _bidMinimumHours,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Minimum bidding duration (hours)',
                ),
              ),
              TextField(
                controller: _bidMaximumHours,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Maximum bidding duration (hours)',
                ),
              ),
              TextField(
                controller: _bidMaximumDealers,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Maximum invited dealers (0 = unlimited)',
                ),
              ),
              const Text(
                'Buyers choose within these limits. Set all duration values equal for fixed timing. Existing requests keep their deadline.',
              ),
              TextField(
                controller: _bidMinIncrement,
                decoration: const InputDecoration(
                  labelText: 'Minimum price decrease on revisions (INR)',
                  hintText: '0 disables the price step rule',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  widget.onSaveSetting!('bid_rules', {
                    'expiry_hours': parseDouble(_bidExpiryHours.text),
                    'min_time_hours': parseDouble(_bidMinimumHours.text),
                    'max_time_hours': parseDouble(_bidMaximumHours.text),
                    'max_dealers': int.tryParse(_bidMaximumDealers.text) ?? -1,
                    'min_bidding_increment': parseDouble(_bidMinIncrement.text),
                  });
                },
                child: const Text('Save Bid Rules'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDealerRulesTab() {
    return SingleChildScrollView(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Dealer Operations Rules',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Color(0xFF3B0764),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _dealerMinRating,
                decoration: const InputDecoration(
                  labelText: 'Minimum Dealer Star Rating Cap',
                  hintText: 'e.g. 3.5',
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  widget.onSaveSetting!('dealer_rules', {
                    'min_rating_threshold': parseDouble(_dealerMinRating.text),
                  });
                },
                child: const Text('Save Dealer Rules'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNotificationsTab() {
    return const SingleChildScrollView(
      child: DataPanel(
        title: 'Notifications',
        children: [
          Text(
            'Bid, commission, and dispute alerts are delivered in the app. Open Notifications to view the related request or bid.',
          ),
        ],
      ),
    );
  }

  Widget _buildCategoriesTab() {
    if (_loadingCategories) {
      return const Center(child: CircularProgressIndicator());
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Hierarchical Category Tree',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                  color: Color(0xFF3B0764),
                ),
              ),
              FilledButton.icon(
                icon: const Icon(Icons.add),
                label: const Text('Add Category'),
                onPressed: () => _addCategoryDialog(null),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_categoryTree.isEmpty)
            const Text('No categories created yet.')
          else
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: _categoryTree.map((cat) {
                final String catId = cat['id']?.toString() ?? '';
                final String catName = cat['name']?.toString() ?? '';
                final List<dynamic> subcats = cat['items'] ?? [];

                return Card(
                  elevation: 2,
                  child: Container(
                    width: 280,
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                catName,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                  fontSize: 16,
                                  color: Color(0xFF6D28D9),
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.edit_outlined, size: 18),
                              onPressed: () =>
                                  _editCategoryDialog(catId, catName, null),
                            ),
                            IconButton(
                              icon: const Icon(
                                Icons.delete_outline,
                                size: 18,
                                color: Colors.red,
                              ),
                              onPressed: () => _deleteCategory(catId),
                            ),
                          ],
                        ),
                        const Divider(),
                        ...subcats.map((sub) {
                          final String subId = sub['id']?.toString() ?? '';
                          final String subName = sub['name']?.toString() ?? '';
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.subdirectory_arrow_right,
                                  size: 16,
                                  color: Colors.grey,
                                ),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    subName,
                                    style: const TextStyle(fontSize: 14),
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(
                                    Icons.edit_outlined,
                                    size: 16,
                                  ),
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  onPressed: () => _editCategoryDialog(
                                    subId,
                                    subName,
                                    catId,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                IconButton(
                                  icon: const Icon(
                                    Icons.delete_outline,
                                    size: 16,
                                    color: Colors.red,
                                  ),
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  onPressed: () => _deleteCategory(subId),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                        const SizedBox(height: 8),
                        TextButton.icon(
                          icon: const Icon(Icons.add, size: 16),
                          label: const Text('Add Subcategory'),
                          onPressed: () => _addCategoryDialog(catId),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
}

class LogsPaymentsPage extends StatelessWidget {
  const LogsPaymentsPage({
    super.key,
    required this.logs,
    required this.payments,
    required this.notifications,
    required this.onPayment,
  });
  final List<Map<String, dynamic>> logs;
  final List<Map<String, dynamic>> payments;
  final List<AppNotification> notifications;
  final Future<void> Function(String commissionId, String status) onPayment;
  @override
  Widget build(BuildContext context) => PageScaffold(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(
          title: 'Logs / Payments / Notifications',
          subtitle:
              'Audit logs, manual payment states, commission logs, notification logs, and login activity.',
          icon: Icons.receipt_long_outlined,
        ),
        const SizedBox(height: 12),
        PaymentsPage(payments: payments, onPayment: onPayment),
        const SizedBox(height: 12),
        DataPanel(
          title: 'Audit logs',
          children: logs
              .take(20)
              .map(
                (row) => ListTile(
                  title: Text(row['action']?.toString() ?? ''),
                  subtitle: Text(
                    '${row['entity_type'] ?? ''} ${row['entity_id'] ?? ''}',
                  ),
                ),
              )
              .toList(),
        ),
      ],
    ),
  );
}

class PaymentsPage extends StatelessWidget {
  const PaymentsPage({super.key, required this.payments, this.onPayment});
  final List<Map<String, dynamic>> payments;
  final Future<void> Function(String commissionId, String status)? onPayment;
  @override
  Widget build(BuildContext context) => DataPanel(
    title: 'Commission / Payments',
    children: payments.isEmpty
        ? [const Text('No commission records yet.')]
        : payments.map((row) {
            final id = row['id']?.toString() ?? '';
            return ListTile(
              title: Text(
                '${row['dealer'] ?? ''} | ${money(parseDouble(row['amount']))}',
              ),
              subtitle: Text(
                '${row['product'] ?? ''} | Bid ${row['bid_id'] ?? ''}',
              ),
              leading: StatusPill(
                text: row['payment_status']?.toString() ?? 'pending',
              ),
              trailing: onPayment == null
                  ? null
                  : PopupMenuButton<String>(
                      onSelected: (status) => onPayment!(id, status),
                      itemBuilder: (_) =>
                          ['pending', 'paid', 'failed', 'waived', 'refunded']
                              .map(
                                (status) => PopupMenuItem(
                                  value: status,
                                  child: Text(status),
                                ),
                              )
                              .toList(),
                    ),
            );
          }).toList(),
  );
}

class IncomingRequestsPage extends StatelessWidget {
  const IncomingRequestsPage({
    super.key,
    required this.requests,
    required this.onBid,
  });
  final List<Map<String, dynamic>> requests;
  final Future<void> Function(String requestId) onBid;
  @override
  Widget build(BuildContext context) => PageScaffold(
    child: DealerRequestsPanel(requests: requests, onBid: onBid),
  );
}

class DealerRequestsPanel extends StatelessWidget {
  const DealerRequestsPanel({
    super.key,
    required this.requests,
    required this.onBid,
  });
  final List<Map<String, dynamic>> requests;
  final Future<void> Function(String requestId) onBid;
  @override
  Widget build(BuildContext context) => DataPanel(
    title: 'Incoming Bid Requests',
    children: requests.isEmpty
        ? [const Text('No eligible requests at this moment.')]
        : requests
              .map(
                (row) => ListTile(
                  title: Text(row['product']?.toString() ?? ''),
                  subtitle: Text(
                    '${row['buyer_area'] ?? ''} | Qty ${row['quantity']} | Ends ${row['expires_at'] ?? ''}',
                  ),
                  leading: StatusPill(
                    text: row['status']?.toString() ?? 'active',
                  ),
                  trailing: FilledButton(
                    onPressed: () => onBid(row['id'].toString()),
                    child: const Text('Submit Bid'),
                  ),
                ),
              )
              .toList(),
  );
}

class DealerBidSubmissionPage extends StatelessWidget {
  const DealerBidSubmissionPage({
    super.key,
    required this.requests,
    required this.bids,
    required this.onBid,
  });
  final List<Map<String, dynamic>> requests;
  final List<BidRecord> bids;
  final Future<void> Function(String requestId, {BidRecord? editBid}) onBid;

  void _showBidDetailsDialog(
    BuildContext context,
    BidRecord bid, {
    required bool isMine,
  }) {
    showLiveBidDialog(context, bid, isMine: isMine);
  }

  @override
  Widget build(BuildContext context) {
    final myBids = bids
        .where(
          (b) => b.isMine && (b.status == 'active' || b.status == 'updated'),
        )
        .toList();
    final otherBids = bids
        .where(
          (b) => !b.isMine && (b.status == 'active' || b.status == 'updated'),
        )
        .toList();

    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeader(
            title: 'Active Bids',
            subtitle:
                'Submit, preview, edit, withdraw, and monitor current bid offers before expiry.',
            icon: Icons.edit_note_outlined,
          ),
          const SizedBox(height: 12),
          DealerRequestsPanel(requests: requests, onBid: onBid),
          const SizedBox(height: 12),
          DataPanel(
            title: 'My active submitted bids',
            children: myBids.isEmpty
                ? [const Text('No submitted bids yet.')]
                : myBids
                      .map(
                        (bid) => ListTile(
                          leading: const Icon(
                            Icons.check_circle_outline,
                            color: Colors.green,
                          ),
                          title: Text(bid.product),
                          subtitle: Text(
                            'My Offer: ${money(bid.amount)} | Warranty: ${bid.warrantyText.isEmpty ? 'None' : bid.warrantyText} | Delivery: ${bid.deliveryTime}',
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              TextButton.icon(
                                icon: const Icon(Icons.edit_outlined, size: 16),
                                label: const Text('Edit'),
                                onPressed: () =>
                                    onBid(bid.bidRequestId, editBid: bid),
                              ),
                              const SizedBox(width: 8),
                              StatusPill(text: bidStatusLabel(bid)),
                            ],
                          ),
                          onTap: () =>
                              _showBidDetailsDialog(context, bid, isMine: true),
                        ),
                      )
                      .toList(),
          ),
          const SizedBox(height: 16),
          DataPanel(
            title: 'Other dealers\' bids (Live marketplace)',
            children: otherBids.isEmpty
                ? [const Text('No other bids submitted by competitors yet.')]
                : otherBids
                      .map(
                        (bid) => ListTile(
                          leading: const Icon(
                            Icons.people_outline,
                            color: Colors.purple,
                          ),
                          title: Text('${bid.product} (${bid.dealer})'),
                          subtitle: Text(
                            'Offer: ${money(bid.amount)} | Warranty: ${bid.warrantyText.isEmpty ? 'None' : bid.warrantyText} | Delivery: ${bid.deliveryTime}',
                          ),
                          trailing: StatusPill(text: bidStatusLabel(bid)),
                          onTap: () => _showBidDetailsDialog(
                            context,
                            bid,
                            isMine: false,
                          ),
                        ),
                      )
                      .toList(),
          ),
          DataPanel(
            title: 'Finalized requests',
            children: bids
                .where((bid) => bid.status == 'won')
                .map(
                  (bid) => ListTile(
                    title: Text('${bid.product}: ${money(bid.amount)}'),
                    subtitle: Text(
                      'Request ${bid.bidRequestId} | ${bid.warrantyText} | ${bid.deliveryTime}',
                    ),
                    trailing: TextButton(
                      onPressed: () =>
                          showLiveBidDialog(context, bid, isMine: bid.isMine),
                      child: Text(
                        bid.isMine ? 'Contacts & Chat' : 'Final offer details',
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class BusinessProfilePage extends StatefulWidget {
  const BusinessProfilePage({
    super.key,
    required this.user,
    required this.onDeleteAccount,
    this.subscribed = false,
  });
  final SessionUser user;
  final VoidCallback onDeleteAccount;
  final bool subscribed;

  @override
  State<BusinessProfilePage> createState() => _BusinessProfilePageState();
}

class _BusinessProfilePageState extends State<BusinessProfilePage> {
  final _shopName = TextEditingController();
  final _ownerName = TextEditingController();
  final _gst = TextEditingController();
  final _phone = TextEditingController();
  final _address = TextEditingController();
  final _area = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  final _country = TextEditingController();
  final _pincode = TextEditingController();
  final _radius = TextEditingController();
  double _maxServiceRadius = 5000;
  final _branches = TextEditingController();
  final _serviceCities = TextEditingController();
  final _serviceStates = TextEditingController();
  final _serviceDistricts = TextEditingController();
  final _description = TextEditingController();

  final Set<String> _selectedCategories = {};
  final Set<String> _selectedItems = {};
  List<Map<String, dynamic>> _categoryTree = [];
  final List<String> _selectedBrands = [];
  final _brandInputController = TextEditingController();

  double? _latitude;
  double? _longitude;
  String _deliveryMethod = 'radius';

  bool _loading = true;
  bool _saving = false;
  bool _profileLoaded = false;
  bool _locationConfirmed = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  String _formatList(dynamic val) {
    if (val == null) return '';
    if (val is List) return val.join(', ');
    return val.toString();
  }

  List<String> _parseList(String val) {
    return val
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  static const List<String> _stateOptions = ['Andhra Pradesh'];
  static const List<String> _cityOptions = [
    'Visakhapatnam',
    'Vijayawada',
    'Guntur',
    'Nellore',
    'Kurnool',
    'Tirupati',
    'Rajahmundry',
    'Kakinada',
  ];
  static const List<String> _districtOptions = [
    'Visakhapatnam',
    'NTR',
    'Guntur',
    'Sri Potti Sriramulu Nellore',
    'Kurnool',
    'Tirupati',
    'East Godavari',
    'Kakinada',
  ];

  void _addCsvValue(TextEditingController controller, String value) {
    final values = _parseList(controller.text);
    if (!values.contains(value)) {
      values.add(value);
      controller.text = values.join(', ');
    }
  }

  Widget _selectionChips(TextEditingController controller) {
    final values = _parseList(controller.text);
    if (values.isEmpty) return const SizedBox.shrink();
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: values
          .map(
            (value) => Chip(
              label: Text(value),
              onDeleted: () {
                setState(() {
                  final updated = _parseList(controller.text)..remove(value);
                  controller.text = updated.join(', ');
                });
              },
            ),
          )
          .toList(),
    );
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiClient().fetchProfile(widget.user.accessToken);
      final categories = await ApiClient().getCategories(
        widget.user.accessToken,
      );
      if (mounted) {
        setState(() {
          _categoryTree = categories;
          _shopName.text = data['business_name']?.toString() ?? '';
          _ownerName.text = data['full_name']?.toString() ?? '';
          _gst.text = data['gst_number']?.toString() ?? '';
          _phone.text = data['phone']?.toString() ?? '';
          _address.text = data['address']?.toString() ?? '';
          _area.text = data['area']?.toString() ?? '';
          _city.text = data['city']?.toString() ?? '';
          _state.text = data['state']?.toString() ?? '';
          _country.text = data['country']?.toString() ?? '';
          _pincode.text = data['pincode']?.toString() ?? '';
          _radius.text = (data['service_radius_km'] ?? 25.0).toString();
          _maxServiceRadius =
              double.tryParse(
                data['max_service_radius_km']?.toString() ?? '',
              ) ??
              5000;
          final branches = data['branches'];
          _branches.text = _formatList(branches);
          final serviceCities = data['service_cities'];
          _serviceCities.text = _formatList(serviceCities ?? branches);
          _serviceStates.text = _formatList(data['service_states']);
          _serviceDistricts.text = _formatList(data['service_districts']);
          _deliveryMethod = data['delivery_method']?.toString() ?? 'radius';
          _description.text = data['description']?.toString() ?? '';
          _latitude =
              double.tryParse(data['latitude']?.toString() ?? '') ?? 0.0;
          _longitude =
              double.tryParse(data['longitude']?.toString() ?? '') ?? 0.0;

          final catsList = _parseList(
            data['category_ids'] is List
                ? (data['category_ids'] as List).join(', ')
                : (data['categories']?.toString() ?? ''),
          );
          _selectedCategories.clear();
          _selectedItems.clear();
          for (final c in catsList) {
            if (_dynamicCategoryNames.contains(c)) {
              _selectedCategories.add(c);
            } else {
              bool found = false;
              for (final parent in _dynamicCategoryNames) {
                if (_dynamicItemsFor(parent).contains(c)) {
                  _selectedItems.add(c);
                  _selectedCategories.add(parent);
                  found = true;
                  break;
                }
              }
              if (!found) {
                _selectedItems.add(c);
              }
            }
          }

          _selectedBrands.clear();
          final brandsVal = data['brands'];
          if (brandsVal is List) {
            _selectedBrands.addAll(brandsVal.map((e) => e.toString()));
          } else if (brandsVal != null) {
            _selectedBrands.addAll(_parseList(brandsVal.toString()));
          }

          _loading = false;
          _profileLoaded = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  List<String> get _dynamicCategoryNames {
    final names = _categoryTree
        .map((row) => row['id']?.toString() ?? '')
        .where((name) => name.isNotEmpty)
        .toList();
    return names;
  }

  List<String> _dynamicItemsFor(String category) {
    final parent = _categoryTree.firstWhere(
      (row) => row['id']?.toString() == category,
      orElse: () => <String, dynamic>{},
    );
    final items = parent['items'];
    if (items is List) {
      return items
          .map((item) => (item as Map)['id']?.toString() ?? '')
          .where((name) => name.isNotEmpty)
          .toList();
    }
    return [];
  }

  String _categoryLabel(String id) {
    for (final parent in _categoryTree) {
      if (parent['id'] == id) return parent['name'].toString();
      for (final item in List<Map<String, dynamic>>.from(
        parent['items'] ?? [],
      )) {
        if (item['id'] == id) return '${parent['name']} / ${item['name']}';
      }
    }
    return id;
  }

  @override
  void dispose() {
    _shopName.dispose();
    _ownerName.dispose();
    _gst.dispose();
    _phone.dispose();
    _address.dispose();
    _area.dispose();
    _city.dispose();
    _state.dispose();
    _country.dispose();
    _pincode.dispose();
    _radius.dispose();
    _branches.dispose();
    _serviceCities.dispose();
    _serviceStates.dispose();
    _serviceDistricts.dispose();
    _brandInputController.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_deliveryMethod == 'radius' && !_locationConfirmed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Confirm your shop pin before saving.')),
      );
      return;
    }
    final serviceRadius = double.tryParse(_radius.text);
    if (serviceRadius == null ||
        !serviceRadius.isFinite ||
        serviceRadius <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid positive service radius.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      final profileData = {
        'full_name': _ownerName.text.trim(),
        'phone': _phone.text.trim(),
        'address': _address.text.trim(),
        'city': _city.text.trim(),
        'state': _state.text.trim(),
        'country': _country.text.trim().isEmpty
            ? 'India'
            : _country.text.trim(),
        'area': _area.text.trim(),
        'pincode': _pincode.text.trim(),
        'business_name': _shopName.text.trim(),
        'gst_number': _gst.text.trim(),
        'service_radius_km': serviceRadius,
        'description': _description.text.trim(),
        'branches': _parseList(_branches.text),
        'delivery_method': _deliveryMethod,
        'service_states': _parseList(_serviceStates.text),
        'service_cities': _parseList(_serviceCities.text),
        'service_districts': _parseList(_serviceDistricts.text),
        'categories': [..._selectedCategories, ..._selectedItems],
        'brands': _selectedBrands,
        'latitude': _latitude ?? 0.0,
        'longitude': _longitude ?? 0.0,
      };
      await ApiClient().updateProfile(widget.user.accessToken, profileData);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Business profile updated successfully!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to save profile: $e')));
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_loading && !_profileLoaded) {
      return PageScaffold(
        child: DataPanel(
          title: 'Could not load business profile',
          children: [
            FilledButton(onPressed: _loadProfile, child: const Text('Retry')),
          ],
        ),
      );
    }
    return PageScaffold(
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if ([
                  'held',
                  'flagged',
                  'suspended',
                  'banned',
                ].contains(widget.user.status))
                  WarningBanner(status: widget.user.status),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Expanded(
                      child: SectionHeader(
                        title: 'Business Profile & Configurations',
                        subtitle:
                            'Manage owner name, shop details, GST numbers, item types, and service coverage rules.',
                        icon: Icons.store_outlined,
                      ),
                    ),
                    if (widget.subscribed)
                      Padding(
                        padding: const EdgeInsets.only(top: 8.0, right: 8.0),
                        child: Chip(
                          avatar: const Icon(
                            Icons.check_circle_outline,
                            color: Color(0xFF16A34A),
                            size: 16,
                          ),
                          label: const Text(
                            'Subscribed ✓',
                            style: TextStyle(
                              color: Color(0xFF16A34A),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          backgroundColor: const Color(0xFFDCFCE7),
                          side: const BorderSide(color: Color(0xFF16A34A)),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                DataPanel(
                  title: 'Store & Verification Info',
                  children: [
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: 240,
                          child: TextField(
                            controller: _shopName,
                            decoration: const InputDecoration(
                              labelText: 'Shop Name',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 200,
                          child: TextField(
                            controller: _ownerName,
                            decoration: const InputDecoration(
                              labelText: 'Owner / Contact Name',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 180,
                          child: TextField(
                            controller: _gst,
                            decoration: const InputDecoration(
                              labelText: 'GST Number',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 180,
                          child: TextField(
                            controller: _phone,
                            decoration: const InputDecoration(
                              labelText: 'Store Phone',
                            ),
                            keyboardType: TextInputType.phone,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _description,
                      decoration: const InputDecoration(
                        labelText: 'Business Description',
                        hintText:
                            'Describe your product quality, shipping standards, or support terms...',
                      ),
                      maxLines: 2,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DataPanel(
                  title: 'Service Coverage & Operating Scope',
                  children: [
                    SizedBox(
                      width: 200,
                      child: TextField(
                        controller: _radius,
                        enabled: _deliveryMethod == 'radius',
                        onChanged: (_) => setState(() {}),
                        decoration: const InputDecoration(
                          labelText: 'Service Radius (km)',
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: 240,
                      child: DropdownButtonFormField<String>(
                        value: _deliveryMethod,
                        decoration: const InputDecoration(
                          labelText: 'Delivery Method',
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'radius',
                            child: Text('Radius'),
                          ),
                          DropdownMenuItem(
                            value: 'city',
                            child: Text('Cities'),
                          ),
                          DropdownMenuItem(
                            value: 'district',
                            child: Text('District'),
                          ),
                          DropdownMenuItem(
                            value: 'state',
                            child: Text('State'),
                          ),
                        ],
                        onChanged: (value) {
                          if (value != null) {
                            setState(() => _deliveryMethod = value);
                          }
                        },
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _branches,
                      decoration: const InputDecoration(
                        labelText: 'Operating Branches',
                        hintText: 'Enter comma-separated branch names',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _serviceCities,
                      enabled: _deliveryMethod == 'city',
                      decoration: const InputDecoration(
                        labelText: 'Service Cities',
                        hintText: 'Enter comma-separated delivery cities',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _serviceStates,
                      enabled: _deliveryMethod != 'radius',
                      decoration: const InputDecoration(
                        labelText: 'Service States',
                        hintText: 'Enter comma-separated state names',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _serviceDistricts,
                      enabled: _deliveryMethod == 'district',
                      decoration: const InputDecoration(
                        labelText: 'Service Districts',
                        hintText: 'Enter comma-separated district names',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DataPanel(
                  title: 'Product Offerings & Categories',
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Dealt Categories (Parent Group)',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF3B0764),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            ..._selectedCategories.map(
                              (c) => Chip(
                                label: Text(_categoryLabel(c)),
                                deleteIcon: const Icon(Icons.cancel, size: 16),
                                onDeleted: () {
                                  setState(() {
                                    _selectedCategories.remove(c);
                                    if (_dynamicCategoryNames.contains(c)) {
                                      for (final child in _dynamicItemsFor(c)) {
                                        _selectedItems.remove(child);
                                      }
                                    }
                                  });
                                },
                              ),
                            ),
                            if (_dynamicCategoryNames.any(
                              (c) => !_selectedCategories.contains(c),
                            ))
                              DropdownButton<String>(
                                value: null,
                                hint: const Text('Add Category'),
                                items: _dynamicCategoryNames
                                    .where(
                                      (c) => !_selectedCategories.contains(c),
                                    )
                                    .map(
                                      (c) => DropdownMenuItem<String>(
                                        value: c,
                                        child: Text(_categoryLabel(c)),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (val) {
                                  if (val != null) {
                                    setState(() {
                                      _selectedCategories.add(val);
                                    });
                                  }
                                },
                              ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Dealt Items / Subcategories',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF3B0764),
                          ),
                        ),
                        const SizedBox(height: 6),
                        _selectedCategories.isEmpty
                            ? const Text(
                                'Select parent categories first to configure items.',
                                style: TextStyle(
                                  color: Colors.grey,
                                  fontSize: 13,
                                ),
                              )
                            : Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  ..._selectedItems.map(
                                    (item) => Chip(
                                      label: Text(_categoryLabel(item)),
                                      deleteIcon: const Icon(
                                        Icons.cancel,
                                        size: 16,
                                      ),
                                      onDeleted: () {
                                        setState(() {
                                          _selectedItems.remove(item);
                                        });
                                      },
                                    ),
                                  ),
                                  DropdownButton<String>(
                                    value: null,
                                    hint: const Text('Add Item'),
                                    items: _dynamicCategoryNames
                                        .where(
                                          (c) =>
                                              _selectedCategories.contains(c),
                                        )
                                        .expand((c) => _dynamicItemsFor(c))
                                        .where(
                                          (item) =>
                                              !_selectedItems.contains(item),
                                        )
                                        .toSet()
                                        .map(
                                          (item) => DropdownMenuItem<String>(
                                            value: item,
                                            child: Text(_categoryLabel(item)),
                                          ),
                                        )
                                        .toList(),
                                    onChanged: (val) {
                                      if (val != null) {
                                        setState(() {
                                          _selectedItems.add(val);
                                        });
                                      }
                                    },
                                  ),
                                ],
                              ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DataPanel(
                  title: 'Physical Address',
                  children: [
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: 320,
                          child: TextField(
                            controller: _address,
                            decoration: const InputDecoration(
                              labelText: 'Shop Street Address',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 150,
                          child: TextField(
                            controller: _area,
                            decoration: const InputDecoration(
                              labelText: 'Area / Locality',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 150,
                          child: TextField(
                            controller: _city,
                            decoration: const InputDecoration(
                              labelText: 'City',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 150,
                          child: TextField(
                            controller: _state,
                            decoration: const InputDecoration(
                              labelText: 'State',
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 120,
                          child: TextField(
                            controller: _pincode,
                            decoration: const InputDecoration(
                              labelText: 'Pincode',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Drag/Tap Map to set shop coordinates & Address details',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    LocationMapPicker(
                      token: widget.user.accessToken,
                      onConfirmedChange: (confirmed) {
                        if (mounted)
                          setState(() => _locationConfirmed = confirmed);
                      },
                      serviceRadiusKm: _deliveryMethod == 'radius'
                          ? (double.tryParse(_radius.text) ?? 0)
                                .clamp(0, _maxServiceRadius)
                                .toDouble()
                          : 0,
                      initialLatitude: _latitude,
                      initialLongitude: _longitude,
                      onLocationSelected: (pos, details) {
                        setState(() {
                          if (details.isNotEmpty) {
                            _address.text = details['address'] ?? '';
                            _area.text = details['area'] ?? '';
                            _city.text = details['city'] ?? '';
                            _state.text = details['state'] ?? '';
                            _pincode.text = details['pincode'] ?? '';
                            if (details['country'] != null) {
                              _country.text = details['country']!;
                            }
                          }
                          _latitude = pos.latitude;
                          _longitude = pos.longitude;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        InfoChip('Email', widget.user.email),
                        const SizedBox(width: 8),
                        InfoChip('Status', widget.user.status),
                        const Spacer(),
                        OutlinedButton.icon(
                          onPressed: widget.onDeleteAccount,
                          icon: const Icon(
                            Icons.delete_forever_outlined,
                            color: Colors.red,
                          ),
                          label: const Text(
                            'Delete Account',
                            style: TextStyle(color: Colors.red),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                          onPressed: _saving ? null : _save,
                          icon: _saving
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.save_outlined),
                          label: const Text('Save Business Profile'),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
    );
  }
}

class NotificationsPage extends StatelessWidget {
  const NotificationsPage({
    super.key,
    required this.notifications,
    this.onTapNotification,
  });
  final List<AppNotification> notifications;
  final void Function(AppNotification)? onTapNotification;
  @override
  Widget build(BuildContext context) => PageScaffold(
    child: DataPanel(
      title: 'Notifications',
      children: notifications.isEmpty
          ? [const Text('No notifications.')]
          : notifications
                .map(
                  (item) => ListTile(
                    leading: Icon(
                      item.isRead
                          ? Icons.notifications_none
                          : Icons.notifications_active,
                      color: item.isRead
                          ? Colors.grey
                          : const Color(0xFF3B0764),
                    ),
                    title: Text(
                      item.title,
                      style: TextStyle(
                        fontWeight: item.isRead
                            ? FontWeight.normal
                            : FontWeight.bold,
                        color: item.isRead ? Colors.black54 : Colors.black,
                      ),
                    ),
                    subtitle: Text(
                      item.message,
                      style: TextStyle(
                        color: item.isRead ? Colors.grey : Colors.black87,
                      ),
                    ),
                    trailing: Text(
                      shortTime(item.createdAt),
                      style: TextStyle(
                        color: item.isRead ? Colors.grey : Colors.black54,
                      ),
                    ),
                    onTap: onTapNotification == null
                        ? null
                        : () => onTapNotification!(item),
                  ),
                )
                .toList(),
    ),
  );
}

class ProfileSettingsPage extends StatefulWidget {
  const ProfileSettingsPage({
    super.key,
    required this.user,
    required this.reports,
    required this.onSave,
    required this.onDeleteAccount,
  });
  final SessionUser user;
  final List<Map<String, dynamic>> reports;
  final ValueChanged<SessionUser> onSave;
  final VoidCallback onDeleteAccount;

  @override
  State<ProfileSettingsPage> createState() => _ProfileSettingsPageState();
}

class _ProfileSettingsPageState extends State<ProfileSettingsPage> {
  late final TextEditingController _name;
  late final TextEditingController _phone;
  final _address = TextEditingController();
  final _country = TextEditingController();
  final _state = TextEditingController();
  final _city = TextEditingController();
  final _area = TextEditingController();
  final _pincode = TextEditingController();
  final _preferredRadius = TextEditingController();
  final _locationLabel = TextEditingController();

  double? _latitude;
  double? _longitude;
  List<Map<String, dynamic>> _savedLocations = [];
  String? _editingSavedLocationId;
  bool _locationDefault = false;
  bool _locationConfirmed = false;

  bool _loadingProfile = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.user.name);
    _phone = TextEditingController();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiClient().fetchProfile(widget.user.accessToken);
      final savedLocations = await ApiClient().buyerLocations(
        widget.user.accessToken,
      );
      if (mounted) {
        setState(() {
          _phone.text = data['phone'] ?? '';
          _address.text = data['address'] ?? '';
          _country.text = data['country'] ?? '';
          _state.text = data['state'] ?? '';
          _city.text = data['city'] ?? '';
          _area.text = data['area'] ?? '';
          _pincode.text = data['pincode'] ?? '';
          _preferredRadius.text = (data['preferred_radius'] ?? 15.0).toString();
          _latitude =
              double.tryParse(data['latitude']?.toString() ?? '') ?? 0.0;
          _longitude =
              double.tryParse(data['longitude']?.toString() ?? '') ?? 0.0;
          _savedLocations = savedLocations;
          if (savedLocations.isNotEmpty && _locationLabel.text.isEmpty) {
            final first = savedLocations.first;
            _locationLabel.text = first['label']?.toString() ?? '';
            _address.text = first['address']?.toString() ?? _address.text;
            _country.text = first['country']?.toString() ?? _country.text;
            _state.text = first['state']?.toString() ?? _state.text;
            _city.text = first['city']?.toString() ?? _city.text;
            _area.text = first['area']?.toString() ?? _area.text;
            _pincode.text = first['pincode']?.toString() ?? _pincode.text;
            _latitude =
                double.tryParse(first['latitude']?.toString() ?? '') ??
                _latitude;
            _longitude =
                double.tryParse(first['longitude']?.toString() ?? '') ??
                _longitude;
            _editingSavedLocationId = first['id']?.toString();
            _locationDefault =
                first['is_default'] == true || first['is_default'] == 1;
          }
          _loadingProfile = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loadingProfile = false);
      }
    }
  }

  @override
  void didUpdateWidget(covariant ProfileSettingsPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.user.name != widget.user.name &&
        _name.text != widget.user.name) {
      _name.text = widget.user.name;
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _address.dispose();
    _country.dispose();
    _state.dispose();
    _city.dispose();
    _area.dispose();
    _pincode.dispose();
    _preferredRadius.dispose();
    _locationLabel.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (((_latitude ?? 0) != 0 || (_longitude ?? 0) != 0) &&
        !_locationConfirmed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Confirm the delivery pin before saving.'),
        ),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      final profileData = {
        'full_name': _name.text.trim(),
        'phone': _phone.text.trim(),
        'address': _address.text.trim(),
        'country': _country.text.trim(),
        'state': _state.text.trim(),
        'city': _city.text.trim(),
        'area': _area.text.trim(),
        'pincode': _pincode.text.trim(),
        'preferred_radius': double.tryParse(_preferredRadius.text) ?? 15.0,
        'latitude': _latitude ?? 0.0,
        'longitude': _longitude ?? 0.0,
      };
      final updated = await ApiClient().updateProfile(
        widget.user.accessToken,
        profileData,
      );
      await _reloadSavedLocations();
      widget.onSave(updated);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile saved successfully!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error saving profile: $e')));
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  Future<void> _reloadSavedLocations() async {
    final locations = await ApiClient().buyerLocations(widget.user.accessToken);
    if (mounted) {
      setState(() => _savedLocations = locations);
    }
  }

  void _loadLocationForEdit(Map<String, dynamic> loc) {
    setState(() {
      _editingSavedLocationId = loc['id']?.toString();
      _locationLabel.text = loc['label']?.toString() ?? '';
      _address.text = loc['address']?.toString() ?? '';
      _country.text = loc['country']?.toString() ?? '';
      _state.text = loc['state']?.toString() ?? '';
      _city.text = loc['city']?.toString() ?? '';
      _area.text = loc['area']?.toString() ?? '';
      _pincode.text = loc['pincode']?.toString() ?? '';
      _latitude = double.tryParse(loc['latitude']?.toString() ?? '') ?? 0.0;
      _longitude = double.tryParse(loc['longitude']?.toString() ?? '') ?? 0.0;
      _locationDefault = loc['is_default'] == true || loc['is_default'] == 1;
    });
  }

  void _clearLocationForm() {
    setState(() {
      _editingSavedLocationId = null;
      _locationLabel.clear();
      _address.clear();
      _area.clear();
      _city.clear();
      _state.clear();
      _pincode.clear();
      _latitude = 0.0;
      _longitude = 0.0;
      _locationDefault = _savedLocations.isEmpty;
    });
  }

  Future<void> _saveBuyerLocation() async {
    if (!_locationConfirmed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Confirm the delivery pin before saving.'),
        ),
      );
      return;
    }
    if (_savedLocations.length >= 3 && _editingSavedLocationId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('You can save up to 3 locations.')),
      );
      return;
    }
    if ((_latitude ?? 0) == 0 && (_longitude ?? 0) == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Set a map pin before saving location.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await ApiClient().saveBuyerLocation(widget.user.accessToken, {
        'label': _locationLabel.text.trim().isEmpty
            ? _address.text.trim().isEmpty
                  ? 'Saved location'
                  : _address.text.trim()
            : _locationLabel.text.trim(),
        'address': _address.text.trim(),
        'country': _country.text.trim().isEmpty
            ? 'India'
            : _country.text.trim(),
        'state': _state.text.trim(),
        'city': _city.text.trim(),
        'area': _area.text.trim(),
        'pincode': _pincode.text.trim(),
        'latitude': _latitude,
        'longitude': _longitude,
        'is_default': _locationDefault || _savedLocations.isEmpty,
      }, savedId: _editingSavedLocationId);
      await _reloadSavedLocations();
      _clearLocationForm();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Saved location updated.')));
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Location save failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _setDefaultLocation(String savedId) async {
    await ApiClient().setDefaultBuyerLocation(widget.user.accessToken, savedId);
    await _reloadSavedLocations();
  }

  Future<void> _deleteSavedLocation(String savedId) async {
    await ApiClient().deleteBuyerLocation(widget.user.accessToken, savedId);
    await _reloadSavedLocations();
    if (_editingSavedLocationId == savedId) _clearLocationForm();
  }

  @override
  Widget build(BuildContext context) => PageScaffold(
    child: _loadingProfile
        ? const Center(child: CircularProgressIndicator())
        : Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionHeader(
                title: 'Profile & Default Location Settings',
                subtitle:
                    'Configure personal information, default shipping addresses, pincode matching radius, and raising dispute support.',
                icon: Icons.person_outline,
              ),
              const SizedBox(height: 12),
              DataPanel(
                title: 'Account & Location Details',
                children: [
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      SizedBox(
                        width: 200,
                        child: TextField(
                          controller: _name,
                          decoration: const InputDecoration(
                            labelText: 'Full name',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 180,
                        child: TextField(
                          controller: _phone,
                          decoration: const InputDecoration(labelText: 'Phone'),
                          keyboardType: TextInputType.phone,
                        ),
                      ),
                      SizedBox(
                        width: 190,
                        child: TextField(
                          controller: _preferredRadius,
                          decoration: const InputDecoration(
                            labelText: 'Buyer matching radius (km)',
                          ),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_savedLocations.isNotEmpty) ...[
                    const Text(
                      'Saved Locations',
                      style: TextStyle(fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 8),
                    ..._savedLocations.map((loc) {
                      final savedId = loc['id']?.toString() ?? '';
                      final isDefault =
                          loc['is_default'] == true || loc['is_default'] == 1;
                      return ListTile(
                        dense: true,
                        leading: Icon(
                          isDefault
                              ? Icons.location_on
                              : Icons.location_on_outlined,
                          color: isDefault
                              ? const Color(0xFF6D28D9)
                              : Colors.grey,
                        ),
                        title: Text(loc['label']?.toString() ?? ''),
                        subtitle: Text(
                          '${loc['area'] ?? ''}, ${loc['city'] ?? ''}, ${loc['state'] ?? ''} | ${loc['latitude'] ?? ''}, ${loc['longitude'] ?? ''}',
                        ),
                        trailing: Wrap(
                          spacing: 4,
                          children: [
                            IconButton(
                              tooltip: 'Edit',
                              onPressed: () => _loadLocationForEdit(loc),
                              icon: const Icon(Icons.edit_outlined),
                            ),
                            IconButton(
                              tooltip: 'Set default',
                              onPressed: isDefault
                                  ? null
                                  : () => _setDefaultLocation(savedId),
                              icon: const Icon(Icons.star_border),
                            ),
                            IconButton(
                              tooltip: 'Delete',
                              onPressed: () => _deleteSavedLocation(savedId),
                              icon: const Icon(
                                Icons.delete_outline,
                                color: Colors.red,
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                    const SizedBox(height: 12),
                  ],
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      SizedBox(
                        width: 220,
                        child: TextField(
                          controller: _locationLabel,
                          decoration: const InputDecoration(
                            labelText: 'Location name',
                            hintText: 'Home, Office, Clinic...',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 320,
                        child: TextField(
                          controller: _address,
                          decoration: const InputDecoration(
                            labelText: 'Street Address',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 150,
                        child: TextField(
                          controller: _area,
                          decoration: const InputDecoration(
                            labelText: 'Area / Neighborhood',
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      SizedBox(
                        width: 150,
                        child: TextField(
                          controller: _city,
                          decoration: const InputDecoration(labelText: 'City'),
                        ),
                      ),
                      SizedBox(
                        width: 150,
                        child: TextField(
                          controller: _state,
                          decoration: const InputDecoration(labelText: 'State'),
                        ),
                      ),
                      SizedBox(
                        width: 150,
                        child: TextField(
                          controller: _country,
                          decoration: const InputDecoration(
                            labelText: 'Country',
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 120,
                        child: TextField(
                          controller: _pincode,
                          decoration: const InputDecoration(
                            labelText: 'Pincode',
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Drag/Tap Map to set shipping coordinates & address details',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  LocationMapPicker(
                    key: ValueKey(_editingSavedLocationId ?? 'new-location'),
                    token: widget.user.accessToken,
                    onConfirmedChange: (confirmed) {
                      if (mounted)
                        setState(() => _locationConfirmed = confirmed);
                    },
                    initialLatitude: _latitude,
                    initialLongitude: _longitude,
                    onLocationSelected: (pos, details) {
                      setState(() {
                        if (details.isNotEmpty) {
                          _address.text = details['address'] ?? '';
                          _city.text = details['city'] ?? '';
                          _state.text = details['state'] ?? '';
                          _pincode.text = details['pincode'] ?? '';
                          _area.text = details['area'] ?? '';
                          if (details['country'] != null) {
                            _country.text = details['country']!;
                          }
                          if (_locationLabel.text.trim().isEmpty) {
                            _locationLabel.text =
                                [details['area'], details['city']]
                                    .where((item) => (item ?? '').isNotEmpty)
                                    .join(', ');
                          }
                        }
                        _latitude = pos.latitude;
                        _longitude = pos.longitude;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      InfoChip('Email', widget.user.email),
                      const SizedBox(width: 8),
                      InfoChip('Status', widget.user.status),
                      const SizedBox(width: 8),
                      InfoChip('Saved', '${_savedLocations.length}/3'),
                      const Spacer(),
                      OutlinedButton.icon(
                        onPressed: _clearLocationForm,
                        icon: const Icon(Icons.add_location_alt_outlined),
                        label: const Text('New Location'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.icon(
                        onPressed: _saving || !_locationConfirmed
                            ? null
                            : _saveBuyerLocation,
                        icon: const Icon(Icons.pin_drop_outlined),
                        label: Text(
                          _editingSavedLocationId == null
                              ? 'Save Location'
                              : 'Update Location',
                        ),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: widget.onDeleteAccount,
                        icon: const Icon(
                          Icons.delete_forever_outlined,
                          color: Colors.red,
                        ),
                        label: const Text(
                          'Delete Account',
                          style: TextStyle(color: Colors.red),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.icon(
                        onPressed: _saving ? null : _save,
                        icon: _saving
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.save_outlined),
                        label: const Text('Save Profile'),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DataPanel(
                title: 'Reports & Dispute History',
                children: widget.reports.isEmpty
                    ? [const Text('No report history.')]
                    : widget.reports
                          .map(
                            (row) => ListTile(
                              title: Text(row['reason']?.toString() ?? ''),
                              subtitle: Text(
                                'Status: ${row['status']?.toString() ?? 'open'}',
                              ),
                              trailing: Text(
                                shortTime(
                                  DateTime.tryParse(
                                        row['created_at']?.toString() ?? '',
                                      ) ??
                                      DateTime.now(),
                                ),
                              ),
                            ),
                          )
                          .toList(),
              ),
            ],
          ),
  );
}

class _ProgressRow extends StatelessWidget {
  const _ProgressRow({required this.label, required this.value});
  final String label;
  final double value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      children: [
        SizedBox(width: 170, child: Text(label)),
        Expanded(child: LinearProgressIndicator(value: value)),
        const SizedBox(width: 8),
        Text('${(value * 100).round()}%'),
      ],
    ),
  );
}

class FieldPairController {
  FieldPairController.withText(String nameText, String valueText)
    : name = TextEditingController(text: nameText),
      value = TextEditingController(text: valueText);
  final TextEditingController name;
  final TextEditingController value;
  void dispose() {
    name.dispose();
    value.dispose();
  }
}

class _FilterField extends StatelessWidget {
  const _FilterField({
    required this.label,
    required this.controller,
    this.number = false,
  });

  final String label;
  final TextEditingController controller;
  final bool number;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        keyboardType: number ? TextInputType.number : TextInputType.text,
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}

IconData _metricIcon(String key) {
  if (key.contains('dealer')) return Icons.storefront_outlined;
  if (key.contains('buyer')) return Icons.people_alt_outlined;
  if (key.contains('product')) return Icons.inventory_2_outlined;
  if (key.contains('bid')) return Icons.gavel_outlined;
  if (key.contains('revenue') || key.contains('commission')) {
    return Icons.payments_outlined;
  }
  if (key.contains('report')) return Icons.report_outlined;
  return Icons.insights_outlined;
}

String _title(String key) => key
    .replaceAll('_', ' ')
    .split(' ')
    .map(
      (part) =>
          part.isEmpty ? part : '${part[0].toUpperCase()}${part.substring(1)}',
    )
    .join(' ');

String _formatMetric(Object? value) {
  final number = parseDouble(value);
  if (number > 999) return money(number);
  if (value == null) return '0';
  return value.toString();
}

String bidStatusLabel(BidRecord bid) =>
    bid.requestStatus == 'cancelled' ? 'Closed by Customer' : bid.status;

class BidMonitorPage extends StatelessWidget {
  const BidMonitorPage({
    super.key,
    required this.bids,
    required this.adminView,
    required this.onExport,
  });
  final List<BidRecord> bids;
  final bool adminView;
  final VoidCallback onExport;

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
            title: adminView ? 'Bid Monitor / History' : 'Orders / Bid History',
            subtitle:
                'Active, completed, expired, cancelled, lost, and winning bids.',
            icon: Icons.gavel_outlined,
            trailing: OutlinedButton.icon(
              onPressed: onExport,
              icon: const Icon(Icons.download_outlined),
              label: const Text('CSV'),
            ),
          ),
          const SizedBox(height: 12),
          DataPanel(
            title: '${bids.length} bid records',
            children: bids.isEmpty
                ? [const Text('No bid records yet.')]
                : bids
                      .map(
                        (bid) => ListTile(
                          title: Text(bid.product),
                          subtitle: Text(
                            '${adminView ? bid.dealer : 'Dealer hidden until win'} | ${money(bid.amount)}',
                          ),
                          leading: StatusPill(text: bidStatusLabel(bid)),
                          trailing: Text(shortTime(bid.endsAt)),
                        ),
                      )
                      .toList(),
          ),
        ],
      ),
    );
  }
}

class DealerBidHistoryPage extends StatelessWidget {
  const DealerBidHistoryPage({
    super.key,
    required this.bids,
    this.focusedBidId,
    this.onPay,
    this.onReport,
    this.onWithdraw,
    required this.onExport,
  });

  final List<BidRecord> bids;
  final String? focusedBidId;
  final ValueChanged<BidRecord>? onPay;
  final ValueChanged<BidRecord>? onReport;
  final ValueChanged<BidRecord>? onWithdraw;
  final VoidCallback onExport;

  @override
  Widget build(BuildContext context) {
    final won = bids.where((b) => b.status == 'won').toList();
    final lost = bids
        .where((b) => b.status == 'lost' || b.status == 'rejected')
        .toList();
    final pending = bids
        .where((b) => b.status == 'active' || b.status == 'updated')
        .toList();
    final completed = bids
        .where((b) => b.status != 'active' && b.status != 'updated')
        .toList();

    return PageScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
            title: 'Dealer Bid History',
            subtitle:
                'Overview of all your bid activity, outcomes, and earnings breakdown.',
            icon: Icons.history_outlined,
            trailing: OutlinedButton.icon(
              onPressed: onExport,
              icon: const Icon(Icons.download_outlined),
              label: const Text('Export History'),
            ),
          ),
          const SizedBox(height: 12),
          DefaultTabController(
            length: 4,
            child: DataPanel(
              title: 'Bid Summary',
              children: [
                const TabBar(
                  isScrollable: true,
                  tabs: [
                    Tab(text: 'Won Bids'),
                    Tab(text: 'Lost Bids'),
                    Tab(text: 'Pending Bids'),
                    Tab(text: 'Closed Bids'),
                  ],
                ),
                SizedBox(
                  height: 380,
                  child: TabBarView(
                    children: [
                      _DealerHistorySublist(
                        bids: won,
                        focusedBidId: focusedBidId,
                        showInvoice: true,
                        onPay: onPay,
                        onReport: onReport,
                      ),
                      _DealerHistorySublist(
                        bids: lost,
                        focusedBidId: focusedBidId,
                        onPay: onPay,
                        onReport: onReport,
                      ),
                      _DealerHistorySublist(
                        bids: pending,
                        focusedBidId: focusedBidId,
                        onPay: onPay,
                        onReport: onReport,
                        onWithdraw: onWithdraw,
                      ),
                      _DealerHistorySublist(
                        bids: completed,
                        focusedBidId: focusedBidId,
                        showInvoice: true,
                        onPay: onPay,
                        onReport: onReport,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DealerHistorySublist extends StatelessWidget {
  const _DealerHistorySublist({
    required this.bids,
    this.focusedBidId,
    this.showInvoice = false,
    this.onPay,
    this.onReport,
    this.onWithdraw,
  });
  final List<BidRecord> bids;
  final String? focusedBidId;
  final bool showInvoice;
  final ValueChanged<BidRecord>? onPay;
  final ValueChanged<BidRecord>? onReport;
  final ValueChanged<BidRecord>? onWithdraw;

  @override
  Widget build(BuildContext context) {
    if (bids.isEmpty) {
      return const Center(child: Text('No bid history in this category.'));
    }
    return ListView.builder(
      itemCount: bids.length,
      itemBuilder: (context, idx) {
        final bid = bids[idx];
        return Card(
          color: bid.id == focusedBidId ? const Color(0xFFF3E8FF) : null,
          shape: bid.id == focusedBidId
              ? RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: const BorderSide(color: Color(0xFF7C3AED), width: 1.4),
                )
              : null,
          margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    StatusPill(text: bidStatusLabel(bid)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        bid.product,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ),
                    Text(
                      money(bid.amount),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: Color(0xFF2563EB),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                if (bid.status == 'lost') ...[
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Offer Comparison (Winner Identity Hidden)',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            color: Color(0xFF374151),
                          ),
                        ),
                        const Divider(height: 12),
                        _compRow(
                          'Feature',
                          'My Offer',
                          'Winning Offer',
                          isHeader: true,
                        ),
                        const Divider(height: 8),
                        _compRow(
                          'Price',
                          money(bid.amount),
                          money(bid.winningAmount),
                          isWinnerPrice: true,
                        ),
                        _compRow(
                          'Delivery',
                          '${bid.deliveryTime}',
                          '${bid.winningDeliveryTime}',
                        ),
                        _compRow(
                          'Warranty',
                          bid.warrantyText.isEmpty ? 'None' : bid.warrantyText,
                          bid.winningWarrantyText.isEmpty
                              ? 'None'
                              : bid.winningWarrantyText,
                        ),
                        _compRow(
                          'Free Gifts',
                          bid.freeGifts.isEmpty ? 'None' : bid.freeGifts,
                          bid.winningFreeGifts.isEmpty
                              ? 'None'
                              : bid.winningFreeGifts,
                        ),
                        _compRow(
                          'Extra Services',
                          bid.extraServices.isEmpty
                              ? 'None'
                              : bid.extraServices,
                          bid.winningExtraServices.isEmpty
                              ? 'None'
                              : bid.winningExtraServices,
                        ),
                        _compRow(
                          'Notes',
                          bid.notes.isEmpty ? 'None' : bid.notes,
                          bid.winningNotes.isEmpty ? 'None' : bid.winningNotes,
                        ),
                      ],
                    ),
                  ),
                ],
                if (bid.status == 'won') ...[
                  const Divider(height: 14),
                  if (bid.status == 'won') ...[
                    const Text(
                      'Buyer Contact Details',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF16A34A),
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (bid.buyer.isNotEmpty)
                      _infoRow(Icons.person_outline, bid.buyer),
                    if (bid.buyerPhone.isNotEmpty)
                      _infoRow(Icons.phone_outlined, bid.buyerPhone),
                    if (bid.buyerEmail.isNotEmpty)
                      _infoRow(Icons.email_outlined, bid.buyerEmail),
                    if (bid.buyerAddress.isNotEmpty)
                      _infoRow(Icons.location_on_outlined, bid.buyerAddress),
                  ] else
                    const Text(
                      'Contact details open immediately for the buyer and winning dealer.',
                    ),
                ],
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    OutlinedButton.icon(
                      icon: const Icon(Icons.info_outline, size: 14),
                      label: const Text('Details'),
                      onPressed: () => _showBidDetails(context, bid),
                    ),
                    // Withdraw Bid Button
                    if ((bid.status == 'active' || bid.status == 'updated') &&
                        onWithdraw != null)
                      OutlinedButton.icon(
                        icon: const Icon(
                          Icons.cancel_outlined,
                          size: 14,
                          color: Colors.red,
                        ),
                        label: const Text(
                          'Withdraw Bid',
                          style: TextStyle(color: Colors.red, fontSize: 12),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.red),
                        ),
                        onPressed: () {
                          showDialog<void>(
                            context: context,
                            builder: (ctx) => AlertDialog(
                              title: const Row(
                                children: [
                                  Icon(
                                    Icons.warning_amber_rounded,
                                    color: Colors.red,
                                  ),
                                  SizedBox(width: 8),
                                  Text('Withdraw Bid?'),
                                ],
                              ),
                              content: const Text(
                                'Are you sure you want to withdraw this bid? '
                                'Note: If you exceed 3 withdrawals, your profile will be automatically flagged by the system.',
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(ctx),
                                  child: const Text('No, Keep Bid'),
                                ),
                                FilledButton(
                                  onPressed: () {
                                    Navigator.pop(ctx);
                                    onWithdraw!(bid);
                                  },
                                  style: FilledButton.styleFrom(
                                    backgroundColor: Colors.red,
                                  ),
                                  child: const Text('Yes, Withdraw'),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    // Report button
                    if (onReport != null && bid.status != 'lost')
                      OutlinedButton.icon(
                        icon: const Icon(
                          Icons.flag_outlined,
                          size: 14,
                          color: Colors.red,
                        ),
                        label: const Text(
                          'Report',
                          style: TextStyle(color: Colors.red, fontSize: 12),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.red),
                        ),
                        onPressed: () => onReport!(bid),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showBidDetails(BuildContext context, BidRecord bid) {
    showLiveBidDialog(context, bid, isMine: bid.isMine);
  }

  void _showCustomerReveal(BuildContext context, BidRecord bid) {
    showLiveBidDialog(context, bid, isMine: bid.isMine);
  }

  void _showBuyerReveal(BuildContext context, BidRecord bid) {
    showLiveBidDialog(context, bid, isMine: bid.isMine);
  }

  Widget _infoRow(IconData icon, String text) => Padding(
    padding: const EdgeInsets.only(top: 3),
    child: Row(
      children: [
        Icon(icon, size: 14, color: Colors.grey),
        const SizedBox(width: 6),
        Flexible(child: Text(text, style: const TextStyle(fontSize: 13))),
      ],
    ),
  );

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 90,
          child: Text(
            '$label:',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
        ),
        Flexible(child: Text(value, style: const TextStyle(fontSize: 13))),
      ],
    ),
  );

  Widget _compRow(
    String label,
    String myVal,
    String winVal, {
    bool isHeader = false,
    bool isWinnerPrice = false,
  }) {
    final style = TextStyle(
      fontSize: 12,
      fontWeight: isHeader ? FontWeight.bold : FontWeight.normal,
      color: isHeader ? Colors.black54 : Colors.black87,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(flex: 2, child: Text(label, style: style)),
          Expanded(flex: 3, child: Text(myVal, style: style)),
          Expanded(
            flex: 3,
            child: Text(
              winVal,
              style: isWinnerPrice && !isHeader
                  ? const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF16A34A),
                    )
                  : style,
            ),
          ),
        ],
      ),
    );
  }
}

class LocationMapPicker extends StatefulWidget {
  const LocationMapPicker({
    super.key,
    required this.onLocationSelected,
    this.initialLatitude,
    this.initialLongitude,
    required this.token,
    this.serviceRadiusKm = 0,
    this.onConfirmedChange,
  });
  final ValueChanged<bool>? onConfirmedChange;
  final String token;
  final double serviceRadiusKm;
  final void Function(LatLng position, Map<String, String> details)
  onLocationSelected;
  final double? initialLatitude;
  final double? initialLongitude;

  @override
  State<LocationMapPicker> createState() => _LocationMapPickerState();
}

class _LocationMapPickerState extends State<LocationMapPicker> {
  final MapController _mapController = MapController();
  final TextEditingController _searchController = TextEditingController();
  late LatLng _selectedPos;
  bool _searching = false;
  bool _pinConfirmed = false;

  @override
  void initState() {
    super.initState();
    final lat = widget.initialLatitude;
    final lon = widget.initialLongitude;
    _selectedPos =
        (lat != null &&
            lon != null &&
            (lat != 0 || lon != 0) &&
            lat >= -90 &&
            lat <= 90 &&
            lon >= -180 &&
            lon <= 180)
        ? LatLng(lat, lon)
        : const LatLng(15.5050, 80.0450);
    _pinConfirmed =
        lat != null &&
        lon != null &&
        (lat != 0 || lon != 0) &&
        lat >= -90 &&
        lat <= 90 &&
        lon >= -180 &&
        lon <= 180;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) widget.onConfirmedChange?.call(_pinConfirmed);
    });
  }

  @override
  void didUpdateWidget(covariant LocationMapPicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    final lat = widget.initialLatitude;
    final lon = widget.initialLongitude;
    if ((lat ?? 0) == 0 &&
        (lon ?? 0) == 0 &&
        (lat != oldWidget.initialLatitude ||
            lon != oldWidget.initialLongitude)) {
      _selectionVersion++;
      _selectedPos = const LatLng(15.5050, 80.0450);
      _pinConfirmed = false;
      _mapController.move(_selectedPos, 11);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.onConfirmedChange?.call(false);
      });
      return;
    }
    if (lat != null &&
        lon != null &&
        (lat != 0 || lon != 0) &&
        (lat != oldWidget.initialLatitude ||
            lon != oldWidget.initialLongitude) &&
        (lat != _selectedPos.latitude || lon != _selectedPos.longitude)) {
      final next = LatLng(lat, lon);
      setState(() {
        _selectedPos = next;
        _pinConfirmed = true;
      });
      _mapController.move(next, 14.0);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.onConfirmedChange?.call(true);
      });
    }
  }

  int _selectionVersion = 0;

  void _selectPin(LatLng point) {
    _selectionVersion++;
    setState(() {
      _selectedPos = point;
      _pinConfirmed = false;
    });
    widget.onLocationSelected(point, const {
      'address': '',
      'city': '',
      'state': '',
      'area': '',
      'pincode': '',
    });
    widget.onConfirmedChange?.call(false);
  }

  void _locationFeedback(String message) {
    if (mounted)
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _useCurrentLocation() async {
    setState(() => _searching = true);
    try {
      if (!kIsWeb) {
        if (!await Geolocator.isLocationServiceEnabled()) {
          _locationFeedback(
            'Turn on location services, or search for your address.',
          );
          return;
        }
        var permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied)
          permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied ||
            permission == LocationPermission.deniedForever) {
          _locationFeedback(
            'Allow location access in settings, or search for your address.',
          );
          return;
        }
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 15),
        ),
      );
      if (!mounted) return;
      final point = LatLng(position.latitude, position.longitude);
      _selectPin(point);
      _mapController.move(point, 16);
      await _reverseGeocode(point);
    } catch (_) {
      _locationFeedback(
        'Location access was denied or unavailable. Allow it in browser/device settings, or search for your address.',
      );
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _searchLocation() async {
    final query = _searchController.text.trim();
    if (query.length < 3) {
      _locationFeedback(
        'Enter a city, area, address or pincode (at least 3 characters).',
      );
      return;
    }
    setState(() => _searching = true);
    try {
      final places = await ApiClient().searchLocations(widget.token, query);
      if (!mounted) return;
      if (places.isEmpty) {
        _locationFeedback(
          'No places found. Try a nearby city, area or pincode.',
        );
        return;
      }
      final place = await showModalBottomSheet<Map<String, dynamic>>(
        context: context,
        builder: (sheetContext) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: places
                .map(
                  (place) => ListTile(
                    leading: const Icon(Icons.location_on_outlined),
                    title: Text(
                      place['display_name']?.toString() ?? 'Location',
                    ),
                    onTap: () => Navigator.pop(sheetContext, place),
                  ),
                )
                .toList(),
          ),
        ),
      );
      if (!mounted || place == null) return;
      final point = LatLng(
        double.parse(place['lat'].toString()),
        double.parse(place['lon'].toString()),
      );
      _selectPin(point);
      _mapController.move(point, 16);
      await _reverseGeocode(point);
    } catch (_) {
      _locationFeedback(
        'Search is unavailable. Use your location or tap the map and enter the address.',
      );
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _reverseGeocode(LatLng point) async {
    final version = ++_selectionVersion;
    setState(() => _searching = true);
    try {
      final data = await ApiClient().reverseLocation(
        widget.token,
        point.latitude,
        point.longitude,
      );
      if (!mounted || version != _selectionVersion) return;
      final address = Map<String, dynamic>.from(data['address'] ?? {});
      final street = [
        address['house_number'],
        address['road'],
      ].whereType<String>().where((item) => item.isNotEmpty).join(' ');
      widget.onLocationSelected(point, {
        'address': street.isNotEmpty
            ? street
            : (data['display_name']?.toString() ?? ''),
        'city':
            (address['city'] ??
                    address['town'] ??
                    address['municipality'] ??
                    address['village'] ??
                    address['county'] ??
                    '')
                .toString(),
        'state': (address['state'] ?? '').toString(),
        'country': (address['country'] ?? '').toString(),
        'pincode': (address['postcode'] ?? '').toString(),
        'area':
            (address['neighbourhood'] ??
                    address['suburb'] ??
                    address['quarter'] ??
                    address['village'] ??
                    '')
                .toString(),
      });
      setState(() => _pinConfirmed = true);
      widget.onConfirmedChange?.call(true);
    } catch (_) {
      if (mounted && version == _selectionVersion) {
        widget.onLocationSelected(point, const {});
        setState(() => _pinConfirmed = true);
        widget.onConfirmedChange?.call(true);
        _locationFeedback(
          'Pin confirmed. Enter the street address, city and state manually.',
        );
      }
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 350,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: _selectedPos,
                initialZoom: 11.0,
                onTap: (tapPosition, point) async {
                  _selectPin(point);
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.turacoz.biddingtool',
                ),
                if (widget.serviceRadiusKm > 0)
                  CircleLayer(
                    circles: [
                      CircleMarker(
                        point: _selectedPos,
                        radius: widget.serviceRadiusKm * 1000,
                        useRadiusInMeter: true,
                        color: Colors.blue.withValues(alpha: 0.12),
                        borderColor: Colors.blue,
                        borderStrokeWidth: 2,
                      ),
                    ],
                  ),
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _selectedPos,
                      width: 50,
                      height: 50,
                      child: const Icon(
                        Icons.location_on,
                        color: Colors.red,
                        size: 40,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            Positioned(
              top: 10,
              left: 10,
              right: 10,
              child: Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8.0),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          decoration: const InputDecoration(
                            hintText: 'Search city/location...',
                            border: InputBorder.none,
                          ),
                          onSubmitted: (_) => _searchLocation(),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Use my location',
                        icon: const Icon(Icons.my_location),
                        onPressed: _searching ? null : _useCurrentLocation,
                      ),
                      if (_searching)
                        const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      else
                        IconButton(
                          icon: const Icon(Icons.search),
                          onPressed: _searchLocation,
                        ),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              left: 10,
              right: 10,
              bottom: 10,
              child: Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 8,
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _pinConfirmed
                            ? Icons.check_circle_outline
                            : Icons.pin_drop_outlined,
                        color: _pinConfirmed
                            ? const Color(0xFF16A34A)
                            : const Color(0xFF6D28D9),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _pinConfirmed
                              ? 'Pin confirmed. This latitude and longitude will be saved.'
                              : 'Search or tap the map, then confirm this exact pin.',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      FilledButton.icon(
                        onPressed: _searching
                            ? null
                            : () => _reverseGeocode(_selectedPos),
                        icon: const Icon(Icons.my_location_outlined),
                        label: const Text('Confirm Pin'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
