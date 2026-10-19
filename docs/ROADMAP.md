# Roadmap

What is deliberately not built, in the order it would be worth building.

## 1. Real field data for the crop table

Today the agronomic table is one regional range per crop, cited but coarse, and the trained model
learns from rows derived from those same ranges — so it re-learns the rules rather than adding
evidence. Its accuracy against the small observational sample is 0.38, which is why its influence
on the ranking is scaled down rather than assumed.

District-level yield and cost datasets from state agriculture departments would improve every
number the product shows, and nothing else has to change to absorb them. This is the single
highest-value item on this list.

## 2. Review by regional agronomists

Each crop's figures should carry a reviewer and a review date, enforced in CI so a stale table
fails the build rather than quietly ageing. Support prices change every season.

## 3. A real disease model

Image screening currently relies on a general-purpose vision model with a conservative prompt,
and refuses outright when that is unavailable. A validated, labelled disease dataset and a
specialist classifier with calibrated confidence thresholds would make it a feature rather than
an aid, along with an escalation path to a human expert.

## 4. Shared rate limiting and background work

The limiter is in-process, so it is correct for one API replica only. Redis would fix that and
also allow a scheduled job to warm the mandi price cache rather than filling it on demand.

## 5. Account recovery

There is no email or SMS delivery, so there is no password reset. This needs a provider, rate
limiting on the reset path, and a decision about whether SMS cost is justified.

## 6. Offline use

Farmers with intermittent connectivity would benefit from queuing an analysis and syncing later.
The service worker currently caches the shell only.

## 7. Observability

Request ids and structured logs exist. Metrics, tracing and alerting do not.

---

## Explicitly out of scope

**Lending, credit scoring, and payments.** The finance planner is a budgeting tool. Offering
credit products to smallholders is a regulated activity requiring a licensed partner and a
separate compliance design, and nothing in this codebase should drift towards it. No bank
account, payment or credit data is collected anywhere.

**Guaranteed outcomes.** Every number is an estimate with a stated basis, and the product says so
in the UI, both report formats and the API. That is a product commitment, not a disclaimer.
