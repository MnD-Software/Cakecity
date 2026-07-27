# Cart continuity and recovery

Cake City v1.6 keeps signed-in bags synchronized across devices and safely recovers eligible
abandoned carts.

## Continuity

The installable PWA remains local-first. After identity refresh succeeds, it merges the local bag
with the customer's PostgreSQL cart and then synchronizes bounded snapshots after changes. Product
identity, availability and base prices are always resolved from the WooCommerce-synchronized
catalogue; the browser cannot set authoritative prices.

Configuration hashes are calculated from a strict canonical shape, allowing the same cake with
different sizes, inscriptions or add-ons to remain separate while deduplicating identical lines.

## Recovery eligibility

The worker checks every five minutes and claims up to 100 carts with `SKIP LOCKED`. A cart is
eligible only when it:

- belongs to a signed-in customer;
- contains at least one line;
- has been inactive for at least two hours;
- has not already received a recovery;
- is not in an active checkout started within the last 24 hours.

One recovery notification is created through the transactional outbox. Its deep link restores the
server bag into the PWA and opens checkout. A verified wallet, M-Pesa or card payment closes the
server cart even when the customer does not return to the browser callback.

No automatic coupon is issued. This avoids training customers to abandon carts and protects margin;
future incentives can be attached through the existing segment/campaign system with explicit rules.
