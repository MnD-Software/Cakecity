# Intelligent discovery

Cake City v1.2 provides explainable retrieval and ranking without sending customer text or order
history to a third-party model.

## Customer capabilities

- Natural-language search extracts occasion, flavour, style, recipient, age, budget and serving
  intent from phrases such as “a chocolate birthday cake for a 6 year old under KES 4,000.”
- The Cake Concierge converts a short structured brief into four ranked, in-stock suggestions.
- Signed-in recommendations use categories and flavour attributes from eligible order history.
- Guest recommendations rank synchronized products by rating and verified-review volume.
- Every result includes human-readable reasons such as flavour match or budget fit.

## Operational boundary

WooCommerce remains the catalogue authority. Ranking operates only on the PostgreSQL product read
model and never calls WooCommerce during a customer request. Redis caches anonymous search,
concierge and trending results for five minutes; Redis failure degrades to live PostgreSQL ranking.

Discovery events store a SHA-256 hash of the browser session, never a raw IP address. Context is
limited to twelve primitive values, and analytics failure never blocks shopping. Customer history
is used only when a valid access token identifies an active customer.

## Ranking behavior

Intent matches receive the largest weight, followed by budget fit, customer category/flavour
affinity, average rating and capped review volume. Out-of-stock and unpublished products are always
excluded. The implementation is deterministic and fully testable; a future learned ranker can
replace the scoring function without changing API or UI contracts.
