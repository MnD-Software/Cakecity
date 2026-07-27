# Address book and checkout prefill

Cake City v1.4 removes repeated delivery entry for signed-in customers.

## Customer workflow

- Customers create, edit, remove and choose a default address at `/account/addresses`.
- The first saved address becomes the default automatically.
- Checkout loads the default place first and prefills recipient, phone, street, area and delivery
  notes while keeping every field editable for the current order.
- Guest checkout remains fully available and does not require an account.

## Safety and ownership

All address reads and mutations are scoped to the active customer from the access-token boundary.
Collections are capped at 20 saved places per customer. Removing a default promotes the newest
remaining address in the same transaction, so checkout never points at a deleted default.

The payment intent still receives a checkout snapshot rather than a mutable address identifier.
This preserves the exact delivery destination agreed at payment time.
