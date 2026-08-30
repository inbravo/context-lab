# Fulfilment Policy — Section 4.2: A-to-Z Guarantee Eligibility

**Owner:** Fulfilment Data Engineering
**Effective:** 2026-07-01
**Status:** Approved

## Purpose

This section defines when a delivered parcel qualifies for the A-to-Z
Guarantee, regardless of which seller fulfilled the order. It is the
authoritative source for this rule — any system that decides whether a
customer is covered must trace back to this document, not to a private
spreadsheet or a hardcoded assumption in application code.

## Defined terms

Delivery scans are recorded against one of the following status codes:

| Code  | Meaning |
|-------|---------|
| `DEL` | Delivered — proof-of-delivery scan confirmed |
| `ATT` | Attempted — delivery attempted, no proof-of-delivery confirmed |
| `SAF` | Safe Place — left at a customer-nominated location, photo evidence captured |
| `NEI` | Neighbour Drop — left with a neighbour, card left through the customer's door |
| `LIT` | Lost in Transit — no carrier scan recorded for 48 hours after the last known checkpoint |

## Guarantee trigger rule

A parcel qualifies for the A-to-Z Guarantee when its delivery scan status
is `DEL` and the recorded condition of that scan is `DAMAGED` — meaning
the item or its packaging was reported damaged at the point of delivery.
This applies regardless of seller type (Amazon-fulfilled or third-party).

Guarantee type: `AtoZGuarantee`
Guarantee reference: `policy:4.2`

## Out of scope

Attempted deliveries (`ATT`), safe-place drops (`SAF`), neighbour drops
(`NEI`), and lost-in-transit parcels (`LIT`) are governed by separate
sections of this policy and do not trigger the A-to-Z Guarantee directly.

## Revision history

| Version | Date       | Change |
|---------|------------|--------|
| 4.2     | 2026-07-01 | Clarified that guarantee eligibility applies regardless of seller type |
| 4.1     | 2026-02-14 | Initial publication of the damaged-on-arrival trigger rule |
