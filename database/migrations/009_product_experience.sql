ALTER TABLE products
  ADD COLUMN IF NOT EXISTS short_description text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS gallery jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS categories jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS attributes jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS ingredients text,
  ADD COLUMN IF NOT EXISTS allergens jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS nutrition jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS preparation_minutes integer NOT NULL DEFAULT 180
    CHECK (preparation_minutes BETWEEN 15 AND 10080),
  ADD COLUMN IF NOT EXISTS average_rating numeric(3,2) NOT NULL DEFAULT 0
    CHECK (average_rating BETWEEN 0 AND 5),
  ADD COLUMN IF NOT EXISTS review_count integer NOT NULL DEFAULT 0
    CHECK (review_count >= 0),
  ADD COLUMN IF NOT EXISTS upsell_woo_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS cross_sell_woo_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS video_url text,
  ADD COLUMN IF NOT EXISTS spin_image_urls jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_products_rating
  ON products(status, in_stock, average_rating DESC);
CREATE INDEX IF NOT EXISTS ix_products_categories
  ON products USING gin(categories);
