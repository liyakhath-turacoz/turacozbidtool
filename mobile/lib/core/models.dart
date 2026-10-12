enum UserRole { buyer, dealer, admin }

UserRole parseRole(String role) {
  switch (role.toLowerCase()) {
    case 'admin':
      return UserRole.admin;
    case 'dealer':
      return UserRole.dealer;
    default:
      return UserRole.buyer;
  }
}

extension UserRoleLabel on UserRole {
  String get label {
    switch (this) {
      case UserRole.buyer:
        return 'Buyer';
      case UserRole.dealer:
        return 'Dealer';
      case UserRole.admin:
        return 'Admin';
    }
  }
}

class SessionUser {
  const SessionUser({
    required this.id,
    required this.email,
    required this.name,
    required this.role,
    required this.status,
    required this.accessToken,
  });

  final String id;
  final String email;
  final String name;
  final UserRole role;
  final String status;
  final String accessToken;

  factory SessionUser.fromJson(Map<String, dynamic> json) => SessionUser(
    id: json['id']?.toString() ?? '',
    email: json['email']?.toString() ?? '',
    name: json['name']?.toString() ?? '',
    role: parseRole(json['role']?.toString() ?? 'buyer'),
    status: json['status']?.toString() ?? 'active',
    accessToken: json['access_token']?.toString() ?? '',
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'name': name,
    'role': role.label.toLowerCase(),
    'status': status,
    'access_token': accessToken,
  };
}

class ProductItem {
  const ProductItem({
    required this.id,
    required this.name,
    required this.category,
    this.subcategory = '',
    required this.brand,
    required this.model,
    required this.priceMin,
    required this.priceMax,
    required this.location,
    required this.status,
    required this.specifications,
    this.imageUrl = '',
    this.releaseYear,
    this.source = 'manual',
  });

  final String id;
  final String name;
  final String category;
  final String subcategory;
  final String brand;
  final String model;
  final double priceMin;
  final double priceMax;
  final String location;
  final String status;
  final Map<String, String> specifications;
  final String imageUrl;
  final int? releaseYear;
  final String source;

  factory ProductItem.fromJson(Map<String, dynamic> json) => ProductItem(
    id: json['id']?.toString() ?? '',
    name: json['name']?.toString() ?? '',
    category: json['category']?.toString() ?? '',
    subcategory:
        json['item']?.toString() ?? json['subcategory']?.toString() ?? '',
    brand: json['brand']?.toString() ?? '',
    model: json['model']?.toString() ?? '',
    priceMin: parseDouble(json['price_min']),
    priceMax: parseDouble(json['price_max']),
    location: json['location']?.toString() ?? '',
    status: json['status']?.toString() ?? '',
    specifications: Map<String, String>.from(json['specifications'] ?? {}),
    imageUrl: json['image_url']?.toString() ?? '',
    releaseYear: int.tryParse(json['release_year']?.toString() ?? ''),
    source: json['source']?.toString() ?? 'manual',
  );
}

class BidRecord {
  const BidRecord({
    required this.id,
    required this.bidRequestId,
    this.productId = '',
    this.quantity = 1,
    this.selectable = false,
    this.isMine = false,
    this.installationIncluded = false,
    required this.product,
    required this.buyer,
    required this.buyerAddress,
    required this.buyerPhone,
    required this.buyerEmail,
    required this.dealer,
    required this.ownerName,
    required this.businessAddress,
    required this.gstNumber,
    required this.dealerPhone,
    required this.dealerEmail,
    required this.amount,
    required this.discountAmount,
    required this.warrantyText,
    required this.deliveryTime,
    required this.freeGifts,
    required this.extraServices,
    required this.notes,
    required this.commission,
    required this.status,
    required this.requestStatus,
    required this.endsAt,
    required this.commissionPaymentStatus,
    required this.winningAmount,
    required this.winningWarrantyText,
    required this.winningDeliveryTime,
    required this.winningFreeGifts,
    required this.winningExtraServices,
    required this.winningNotes,
    required this.priceDifference,
    required this.lostReason,
  });

  final String id;
  final String bidRequestId;
  final String productId;
  final int quantity;
  final bool selectable;
  final bool isMine;
  final bool installationIncluded;
  final String product;
  final String buyer;
  final String buyerAddress;
  final String buyerPhone;
  final String buyerEmail;
  final String dealer;
  final String ownerName;
  final String businessAddress;
  final String gstNumber;
  final String dealerPhone;
  final String dealerEmail;
  final double amount;
  final double discountAmount;
  final String warrantyText;
  final String deliveryTime;
  final String freeGifts;
  final String extraServices;
  final String notes;
  final double commission;
  final String status;
  final String requestStatus;
  final DateTime endsAt;
  final String commissionPaymentStatus;
  final double winningAmount;
  final String winningWarrantyText;
  final String winningDeliveryTime;
  final String winningFreeGifts;
  final String winningExtraServices;
  final String winningNotes;
  final double priceDifference;
  final String lostReason;

  factory BidRecord.fromJson(Map<String, dynamic> json) => BidRecord(
    id: json['id']?.toString() ?? '',
    bidRequestId: json['bid_request_id']?.toString() ?? '',
    productId: json['product_id']?.toString() ?? '',
    quantity: int.tryParse(json['quantity']?.toString() ?? '') ?? 1,
    selectable: json['selectable'] == true || json['selectable'] == 1,
    isMine: json['is_mine'] == true || json['is_mine'] == 1,
    installationIncluded: json['installation_included'] == true || json['installation_included'] == 1,
    product: json['product']?.toString() ?? '',
    buyer: json['buyer']?.toString() ?? '',
    buyerAddress: json['buyer_address']?.toString() ?? '',
    buyerPhone: json['buyer_phone']?.toString() ?? '',
    buyerEmail: json['buyer_email']?.toString() ?? '',
    dealer: json['dealer']?.toString() ?? '',
    ownerName: json['owner_name']?.toString() ?? '',
    businessAddress: json['business_address']?.toString() ?? '',
    gstNumber: json['gst_number']?.toString() ?? '',
    dealerPhone: json['dealer_phone']?.toString() ?? '',
    dealerEmail: json['dealer_email']?.toString() ?? '',
    amount: parseDouble(json['amount']),
    discountAmount: parseDouble(json['discount_amount']),
    warrantyText: json['warranty_text']?.toString() ?? '',
    deliveryTime: json['delivery_time']?.toString() ?? '',
    freeGifts: json['free_gifts']?.toString() ?? '',
    extraServices: json['extra_services']?.toString() ?? '',
    notes: json['notes']?.toString() ?? '',
    commission: parseDouble(json['commission']),
    status: json['status']?.toString() ?? 'active',
    requestStatus: json['request_status']?.toString() ?? '',
    endsAt:
        DateTime.tryParse(json['ends_at']?.toString() ?? '') ??
        DateTime.now().add(const Duration(hours: 2)),
    commissionPaymentStatus:
        json['commission_payment_status']?.toString() ?? 'pending',
    winningAmount: parseDouble(json['winning_amount']),
    winningWarrantyText: json['winning_warranty_text']?.toString() ?? '',
    winningDeliveryTime: json['winning_delivery_time']?.toString() ?? '',
    winningFreeGifts: json['winning_free_gifts']?.toString() ?? '',
    winningExtraServices: json['winning_extra_services']?.toString() ?? '',
    winningNotes: json['winning_notes']?.toString() ?? '',
    priceDifference: parseDouble(json['price_difference']),
    lostReason: json['lost_reason']?.toString() ?? '',
  );
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.eventType,
    required this.targetBidId,
    required this.targetReportId,
    required this.createdAt,
    required this.isRead,
  });

  final String id;
  final String title;
  final String message;
  final String eventType;
  final String targetBidId;
  final String targetReportId;
  final DateTime createdAt;
  final bool isRead;

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        message: json['message']?.toString() ?? '',
        eventType: json['event_type']?.toString() ?? 'system',
        targetBidId: json['target_bid_id']?.toString() ?? '',
        targetReportId: json['target_report_id']?.toString() ?? '',
        createdAt:
            DateTime.tryParse(json['created_at']?.toString() ?? '') ??
            DateTime.now(),
        isRead: json['is_read'] == true || json['is_read'] == 1,
      );
}

class ProductDraft {
  ProductDraft({
    required this.name,
    required this.category,
    this.subcategory,
    required this.brand,
    required this.model,
    required this.priceMin,
    required this.priceMax,
    required this.location,
    required this.specifications,
  });

  final String name;
  final String category;
  final String? subcategory;
  final String brand;
  final String model;
  final double priceMin;
  final double priceMax;
  final String location;
  final Map<String, String> specifications;

  Map<String, dynamic> toJson() => {
    'name': name,
    'category': category,
    if (subcategory != null) 'subcategory': subcategory,
    'brand': brand,
    'model': model,
    'price_min': priceMin,
    'price_max': priceMax,
    'location': location,
    'specifications': specifications,
  };
}

double parseDouble(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? 0;
  }
  return 0;
}

String money(double value) =>
    'Rs. ${value.toStringAsFixed(2).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => ',')}';

String shortTime(DateTime dateTime) =>
    '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
