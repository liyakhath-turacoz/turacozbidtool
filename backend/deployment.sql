CREATE TABLE IF NOT EXISTS roles (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(32) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  role_id CHAR(36) NOT NULL,
  email VARCHAR(190) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  phone VARCHAR(32),
  status ENUM('active','verified','pending','held','flagged','suspended','banned','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_role_status (role_id, status),
  CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  KEY idx_refresh_user_expiry (user_id, expires_at),
  CONSTRAINT fk_refresh_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS login_history (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NULL,
  success BOOLEAN NOT NULL,
  reason VARCHAR(160),
  ip_address VARCHAR(64),
  user_agent VARCHAR(255),
  created_at DATETIME NOT NULL,
  KEY idx_login_user_time (user_id, created_at),
  CONSTRAINT fk_login_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS locations (
  id CHAR(36) PRIMARY KEY,
  country VARCHAR(80) NOT NULL,
  state VARCHAR(100) NOT NULL,
  city VARCHAR(100) NOT NULL,
  area VARCHAR(120),
  address_line VARCHAR(255),
  pincode VARCHAR(20),
  zipcode VARCHAR(20),
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  service_radius_km DECIMAL(8,2) NOT NULL DEFAULT 10,
  status ENUM('active','inactive','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_location_pin (latitude, longitude),
  KEY idx_location_search (country, state, city, pincode, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
  id CHAR(36) PRIMARY KEY,
  parent_id CHAR(36) NULL,
  name VARCHAR(120) NOT NULL,
  status ENUM('active','archived','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  UNIQUE KEY uq_category_parent_name (parent_id, name, deleted_at),
  KEY idx_categories_status_name (status, name),
  CONSTRAINT fk_category_parent FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id CHAR(36) PRIMARY KEY,
  category_id CHAR(36) NOT NULL,
  subcategory_id CHAR(36) NULL,
  location_id CHAR(36) NULL,
  name VARCHAR(190) NOT NULL,
  brand VARCHAR(120),
  model VARCHAR(120),
  source VARCHAR(40) NOT NULL DEFAULT 'manual',
  source_product_id VARCHAR(80) NULL,
  mpn VARCHAR(190) NULL,
  gtin VARCHAR(255) NULL,
  release_year SMALLINT NULL,
  source_updated_at DATETIME NULL,
  icecat_quality VARCHAR(30) NULL,
  description TEXT,
  summary_description TEXT,
  highlights JSON NULL,
  technical_specifications JSON NULL,
  software_specifications JSON NULL,
  gallery JSON NULL,
  multimedia JSON NULL,
  price_min DECIMAL(12,2) NOT NULL DEFAULT 0,
  price_max DECIMAL(12,2) NOT NULL DEFAULT 0,
  image_url VARCHAR(500),
  status ENUM('active','inactive','archived','deleted') NOT NULL DEFAULT 'active',
  created_by CHAR(36) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  CONSTRAINT chk_product_price CHECK (price_min >= 0 AND price_max >= price_min),
  UNIQUE KEY uq_products_source_product (source, source_product_id),
  KEY idx_products_search (status, category_id, brand, model, created_at),
  KEY idx_products_release_source (release_year, source, status),
  FULLTEXT KEY ft_products_text (name, brand, model, description),
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id),
  CONSTRAINT fk_products_subcategory FOREIGN KEY (subcategory_id) REFERENCES categories(id) ON DELETE SET NULL,
  CONSTRAINT fk_products_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
  CONSTRAINT fk_products_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS product_specifications (
  id CHAR(36) PRIMARY KEY,
  product_id CHAR(36) NOT NULL,
  spec_name VARCHAR(120) NOT NULL,
  spec_group VARCHAR(120) NOT NULL DEFAULT 'Highlights',
  feature_id VARCHAR(80) NULL,
  spec_value TEXT NOT NULL,
  unit VARCHAR(40) NULL,
  spec_type VARCHAR(40) NULL,
  description TEXT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_product_spec (product_id, spec_group, spec_name),
  KEY idx_specs_product (product_id),
  KEY idx_spec_search (spec_name, spec_value(100)),
  CONSTRAINT fk_specs_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS product_assets (
  id CHAR(36) PRIMARY KEY,
  product_id CHAR(36) NOT NULL,
  asset_type VARCHAR(40) NOT NULL,
  url VARCHAR(1000) NOT NULL,
  thumbnail_url VARCHAR(1000) NULL,
  content_type VARCHAR(120) NULL,
  description VARCHAR(500) NULL,
  width INT NOT NULL DEFAULT 0,
  height INT NOT NULL DEFAULT 0,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_product_asset (product_id, asset_type, url(400)),
  KEY idx_product_assets_product_sort (product_id, asset_type, sort_order),
  CONSTRAINT fk_product_assets_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS catalog_imports (
  id CHAR(36) PRIMARY KEY,
  catalog_version VARCHAR(80) NOT NULL UNIQUE,
  manifest_hash CHAR(64) NOT NULL,
  status ENUM('importing','completed','failed') NOT NULL,
  product_count INT NOT NULL DEFAULT 0,
  imported_count INT NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  started_at DATETIME NOT NULL,
  completed_at DATETIME NULL,
  updated_at DATETIME NOT NULL,
  KEY idx_catalog_import_status (status, updated_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dealer_profiles (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL UNIQUE,
  business_name VARCHAR(190) NOT NULL,
  owner_name VARCHAR(160),
  business_address VARCHAR(255),
  gst_number VARCHAR(32),
  rating DECIMAL(3,2) NOT NULL DEFAULT 0,
  verification_status ENUM('pending','verified','rejected') NOT NULL DEFAULT 'pending',
  warning_message TEXT,
  dynamic_fields JSON NULL,
  service_preferences JSON NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_dealer_profile_business (business_name, verification_status, rating),
  CONSTRAINT fk_dealer_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS buyer_profiles (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL UNIQUE,
  phone VARCHAR(32),
  address VARCHAR(255),
  country VARCHAR(80),
  state VARCHAR(100),
  city VARCHAR(100),
  area VARCHAR(120),
  pincode VARCHAR(20),
  preferred_radius DECIMAL(8,2) NOT NULL DEFAULT 10,
  default_location_id CHAR(36) NULL,
  dynamic_fields JSON NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT fk_buyer_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_buyer_profile_location FOREIGN KEY (default_location_id) REFERENCES locations(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS buyer_locations (
  id CHAR(36) PRIMARY KEY,
  buyer_id CHAR(36) NOT NULL,
  location_id CHAR(36) NOT NULL,
  label VARCHAR(120) NOT NULL DEFAULT 'Saved location',
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  active_location_id CHAR(36) NULL,
  UNIQUE KEY uq_buyer_active_location (buyer_id, active_location_id),
  KEY idx_buyer_locations_buyer_default (buyer_id, is_default, deleted_at),
  CONSTRAINT fk_buyer_locations_buyer FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_buyer_locations_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dealer_categories (
  dealer_id CHAR(36) NOT NULL,
  category_id CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (dealer_id, category_id),
  KEY idx_dealer_categories_category_dealer (category_id, dealer_id),
  CONSTRAINT fk_dealer_categories_dealer FOREIGN KEY (dealer_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_dealer_categories_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dealer_service_locations (
  dealer_id CHAR(36) NOT NULL,
  location_id CHAR(36) NOT NULL,
  radius_km DECIMAL(8,2) NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (dealer_id, location_id),
  KEY idx_dealer_service_location_radius (location_id, radius_km),
  CONSTRAINT fk_dealer_locations_dealer FOREIGN KEY (dealer_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_dealer_locations_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS carts (
  id CHAR(36) PRIMARY KEY,
  buyer_id CHAR(36) NOT NULL,
  status ENUM('active','converted','abandoned','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_carts_buyer_status (buyer_id, status),
  CONSTRAINT fk_carts_buyer FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cart_items (
  id CHAR(36) PRIMARY KEY,
  cart_id CHAR(36) NOT NULL,
  product_id CHAR(36) NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  saved_for_later BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_cart_product (cart_id, product_id),
  CONSTRAINT chk_cart_quantity CHECK (quantity > 0),
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_product FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bid_requests (
  id CHAR(36) PRIMARY KEY,
  buyer_id CHAR(36) NOT NULL,
  product_id CHAR(36) NOT NULL,
  location_id CHAR(36) NOT NULL,
  quantity INT NOT NULL,
  radius_km DECIMAL(8,2) NOT NULL,
  skip_flagged_dealers BOOLEAN NOT NULL DEFAULT TRUE,
  status ENUM('draft','active','awarded','expired','cancelled','deleted') NOT NULL DEFAULT 'active',
  winning_bid_id CHAR(36) NULL,
  starts_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  CONSTRAINT chk_bid_request_quantity CHECK (quantity > 0),
  KEY idx_bid_requests_buyer_status (buyer_id, status, created_at),
  KEY idx_bid_requests_product_status (product_id, status, expires_at),
  KEY idx_bid_requests_location_status (location_id, status, expires_at),
  CONSTRAINT fk_bid_requests_buyer FOREIGN KEY (buyer_id) REFERENCES users(id),
  CONSTRAINT fk_bid_requests_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT fk_bid_requests_location FOREIGN KEY (location_id) REFERENCES locations(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bid_request_fields (
  id CHAR(36) PRIMARY KEY,
  bid_request_id CHAR(36) NOT NULL,
  field_name VARCHAR(120) NOT NULL,
  field_value TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_request_field (bid_request_id, field_name),
  CONSTRAINT fk_request_fields_request FOREIGN KEY (bid_request_id) REFERENCES bid_requests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bid_request_dealers (
  bid_request_id CHAR(36) NOT NULL,
  dealer_id CHAR(36) NOT NULL,
  notified_at DATETIME NOT NULL,
  status ENUM('notified','viewed','bid','ignored','expired') NOT NULL DEFAULT 'notified',
  PRIMARY KEY (bid_request_id, dealer_id),
  KEY idx_request_dealer_status (dealer_id, status),
  CONSTRAINT fk_request_dealers_request FOREIGN KEY (bid_request_id) REFERENCES bid_requests(id) ON DELETE CASCADE,
  CONSTRAINT fk_request_dealers_dealer FOREIGN KEY (dealer_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bids (
  id CHAR(36) PRIMARY KEY,
  bid_request_id CHAR(36) NOT NULL,
  dealer_id CHAR(36) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  warranty_text VARCHAR(255),
  delivery_time VARCHAR(120),
  installation_included BOOLEAN NOT NULL DEFAULT FALSE,
  free_gifts TEXT,
  extra_services TEXT,
  notes TEXT,
  status ENUM('active','updated','won','lost','expired','withdrawn','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  CONSTRAINT chk_bid_amount CHECK (amount > 0),
  UNIQUE KEY uq_bid_request_dealer (bid_request_id, dealer_id),
  KEY idx_bids_request_status_amount (bid_request_id, status, amount),
  KEY idx_bids_dealer_status_time (dealer_id, status, created_at),
  CONSTRAINT fk_bids_request FOREIGN KEY (bid_request_id) REFERENCES bid_requests(id) ON DELETE CASCADE,
  CONSTRAINT fk_bids_dealer FOREIGN KEY (dealer_id) REFERENCES users(id)
) ENGINE=InnoDB;

ALTER TABLE bid_requests
  ADD CONSTRAINT fk_bid_requests_winning_bid
  FOREIGN KEY (winning_bid_id) REFERENCES bids(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS commissions (
  id CHAR(36) PRIMARY KEY,
  bid_id CHAR(36) NOT NULL UNIQUE,
  amount DECIMAL(12,2) NOT NULL,
  rate_percent DECIMAL(5,2) NOT NULL,
  payment_status ENUM('pending','paid','failed','waived','refunded') NOT NULL DEFAULT 'pending',
  paid_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT chk_commission_amount CHECK (amount >= 0),
  KEY idx_commissions_status_created (payment_status, created_at),
  CONSTRAINT fk_commissions_bid FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS invoices (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  bid_id CHAR(36) NULL,
  invoice_number VARCHAR(80) NOT NULL UNIQUE,
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('draft','issued','paid','cancelled') NOT NULL DEFAULT 'issued',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT fk_invoices_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_invoices_bid FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reports (
  id CHAR(36) PRIMARY KEY,
  reporter_id CHAR(36) NOT NULL,
  reported_user_id CHAR(36) NOT NULL,
  bid_id CHAR(36) NOT NULL,
  assigned_admin_id CHAR(36) NULL,
  reason VARCHAR(190) NOT NULL,
  description TEXT,
  status ENUM('open','investigating','resolved','rejected','escalated','closed') NOT NULL DEFAULT 'open',
  internal_notes TEXT,
  closure_requested_by CHAR(36) NULL,
  closure_reason TEXT NULL,
  closure_requested_status ENUM('none','requested','approved','rejected') NOT NULL DEFAULT 'none',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_reports_status_created (status, created_at),
  KEY idx_reports_users (reporter_id, reported_user_id),
  KEY idx_reports_bid_status (bid_id, status, created_at),
  KEY idx_reports_closure_request (closure_requested_status, updated_at),
  UNIQUE KEY uq_reports_bid (bid_id),
  CONSTRAINT fk_reports_reporter FOREIGN KEY (reporter_id) REFERENCES users(id),
  CONSTRAINT fk_reports_reported FOREIGN KEY (reported_user_id) REFERENCES users(id),
  CONSTRAINT fk_reports_closure_user FOREIGN KEY (closure_requested_by) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_reports_admin FOREIGN KEY (assigned_admin_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_reports_bid FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  event_type VARCHAR(80) NOT NULL,
  title VARCHAR(160) NOT NULL,
  body TEXT NOT NULL,
  target_bid_id CHAR(36) NULL,
  target_report_id CHAR(36) NULL,
  read_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_notifications_user_read_time (user_id, read_at, created_at),
  KEY idx_notifications_target_bid (target_bid_id),
  KEY idx_notifications_target_report (target_report_id),
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_notifications_report FOREIGN KEY (target_report_id) REFERENCES reports(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
  id CHAR(36) PRIMARY KEY,
  actor_id CHAR(36) NULL,
  action VARCHAR(120) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id CHAR(36) NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL,
  KEY idx_audit_entity (entity_type, entity_id, created_at),
  KEY idx_audit_actor (actor_id, created_at),
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS platform_settings (
  id CHAR(36) PRIMARY KEY,
  setting_key VARCHAR(120) NOT NULL UNIQUE,
  setting_value JSON NOT NULL,
  status ENUM('active','disabled') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  KEY idx_platform_settings_status (status, setting_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS entity_notes (
  id CHAR(36) PRIMARY KEY,
  entity_type VARCHAR(80) NOT NULL,
  entity_id CHAR(36) NOT NULL,
  author_id CHAR(36) NULL,
  note TEXT NOT NULL,
  visibility ENUM('internal','public') NOT NULL DEFAULT 'internal',
  created_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_entity_notes_lookup (entity_type, entity_id, created_at),
  CONSTRAINT fk_entity_notes_author FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS status_history (
  id CHAR(36) PRIMARY KEY,
  entity_type VARCHAR(80) NOT NULL,
  entity_id CHAR(36) NOT NULL,
  old_status VARCHAR(80),
  new_status VARCHAR(80) NOT NULL,
  changed_by CHAR(36) NULL,
  reason VARCHAR(255),
  created_at DATETIME NOT NULL,
  KEY idx_status_history_entity (entity_type, entity_id, created_at),
  CONSTRAINT fk_status_history_actor FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS uploaded_files (
  id CHAR(36) PRIMARY KEY,
  owner_id CHAR(36) NULL,
  entity_type VARCHAR(80),
  entity_id CHAR(36),
  original_name VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  content_type VARCHAR(120),
  size_bytes BIGINT NOT NULL DEFAULT 0,
  status ENUM('active','deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_uploaded_files_entity (entity_type, entity_id, status),
  CONSTRAINT fk_uploaded_files_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS support_tickets (
  id CHAR(36) PRIMARY KEY,
  requester_id CHAR(36) NOT NULL,
  assigned_admin_id CHAR(36) NULL,
  subject VARCHAR(190) NOT NULL,
  description TEXT,
  status ENUM('open','investigating','resolved','closed') NOT NULL DEFAULT 'open',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  deleted_at DATETIME NULL,
  KEY idx_support_tickets_status (status, created_at),
  CONSTRAINT fk_support_tickets_requester FOREIGN KEY (requester_id) REFERENCES users(id),
  CONSTRAINT fk_support_tickets_admin FOREIGN KEY (assigned_admin_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS report_messages (
  id CHAR(36) PRIMARY KEY,
  report_id CHAR(36) NOT NULL,
  sender_id CHAR(36) NOT NULL,
  recipient_group ENUM('admin', 'buyer', 'dealer', 'both') NOT NULL,
  message TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_report_messages_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  CONSTRAINT fk_report_messages_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bid_messages (
  id CHAR(36) PRIMARY KEY,
  bid_id CHAR(36) NOT NULL,
  sender_id CHAR(36) NOT NULL,
  message TEXT NOT NULL,
  created_at DATETIME(6) NOT NULL,
  KEY idx_bid_messages_thread (bid_id, created_at, id),
  CONSTRAINT fk_bid_messages_bid FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
  CONSTRAINT fk_bid_messages_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
