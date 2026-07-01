-- GicleeArt — analityka ruchu (D1)
CREATE TABLE IF NOT EXISTS analytics_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  event_name TEXT NOT NULL,
  event_type TEXT NOT NULL DEFAULT 'standard',
  shopify_event_id TEXT,
  visitor_id_hash TEXT NOT NULL,
  session_id TEXT NOT NULL,
  customer_id_hash TEXT,
  shopify_customer_id_hash TEXT,
  shopify_order_id TEXT,
  shopify_product_id TEXT,
  shopify_variant_id TEXT,
  product_title TEXT,
  collection_id TEXT,
  url TEXT,
  path TEXT,
  page_title TEXT,
  referrer TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  device_type TEXT,
  browser TEXT,
  os TEXT,
  country TEXT,
  region TEXT,
  language TEXT,
  currency TEXT,
  cart_value REAL,
  checkout_value REAL,
  order_value REAL,
  quantity INTEGER,
  metadata_json TEXT,
  consent_status TEXT,
  bot_suspected INTEGER NOT NULL DEFAULT 0,
  source_bucket TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_event_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_country ON analytics_events(country);

CREATE TABLE IF NOT EXISTS analytics_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
