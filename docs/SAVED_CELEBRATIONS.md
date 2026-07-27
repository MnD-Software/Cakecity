# Saved celebrations

Cake City v1.3 turns wishlist hearts and repeat inscriptions into persistent customer workflows.

## Customer behavior

- Guest favourites are stored locally in the installable PWA and remain available after reload.
- After sign-in, local favourites merge idempotently into the customer's private server collection.
- Signed-in customers can manage synchronized cakes and reusable inscription messages at
  `/account/saved`.
- Product availability and current pricing always come from the PostgreSQL catalogue synchronized
  from WooCommerce; saved entries never copy or override catalogue authority.

## Privacy and limits

Every API operation is scoped to the active customer from the rotating-token identity boundary.
Customers cannot address another customer's saved entry. Cake collections are limited to 100 items
and message collections to 30 items. Product deletion cascades safely from saved collections.

## API

- `GET /v1/account/saved/cakes`
- `PUT /v1/account/saved/cakes/{slug}`
- `DELETE /v1/account/saved/cakes/{slug}`
- `GET /v1/account/saved/messages`
- `POST /v1/account/saved/messages`
- `DELETE /v1/account/saved/messages/{id}`
