# Product experience synchronization

WooCommerce remains authoritative for product identity, price, stock, descriptions, categories,
images, ratings, upsells and cross-sells. Product REST synchronization and signed product webhooks
copy those fields into PostgreSQL; product-page requests never call WooCommerce.

## Native WooCommerce fields

Cake City uses `images` for the gallery, `attributes` for flavour or finish information,
`categories` for discovery, `average_rating` and `rating_count` for verified-review summaries,
and `upsell_ids` plus `cross_sell_ids` to rank the “Often chosen together” edit.

## Cake City product metadata

Add these optional keys to WooCommerce product metadata:

- `_cakecity_ingredients`: plain ingredient statement.
- `_cakecity_allergens`: JSON array or comma-separated allergen names.
- `_cakecity_nutrition`: JSON object such as `{"serving":"100 g","energy":"382 kcal"}`.
- `_cakecity_preparation_minutes`: integer from 15 to 10080.
- `_cakecity_video_url`: HTTPS product-video URL.
- `_cakecity_360_images`: JSON array of up to 36 HTTPS image URLs.

Absent optional data is shown honestly as available on request; the storefront never invents
nutrition, allergen or customer-review content.

## Revenue and customer controls

Size and add-on prices are calculated again by the FastAPI checkout boundary. Browser totals are
only a responsive preview. Current supported add-ons are candles, handwritten greeting card,
signature gift wrap and seasonal flowers. Recommendations remain in-stock, locally synchronized
products, with WooCommerce upsells and cross-sells ranked first.
