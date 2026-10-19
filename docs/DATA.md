# Where every number comes from

This file exists because the most dangerous thing an agricultural advisory tool can do is state
a figure with more confidence than it has earned. A farmer who commits a season's capital to a
yield estimate that is twice reality is harmed by the product, not merely misinformed by it.

## Scope

Reference data covers the **irrigated North-Indian plains**: Haryana, Punjab and western Uttar
Pradesh. The API publishes this scope at `GET /crops` under `provenance`, and the PDF report
prints it. Figures outside this region need revalidation before they should be trusted.

## Prices

`reference_price_per_quintal` in `backend/app/crop_data.py` is an **announced support price**
(MSP), not an expected sale price, and the API labels it that way everywhere it appears. Farmers
routinely sell below MSP outside procurement windows.

| Crop | Reference price (₹/quintal) | Basis |
| --- | --- | --- |
| Rice | 2,441 | MSP, paddy common grade, Kharif 2026-27 |
| Maize | 2,400 | MSP, maize, Kharif 2026-27 (approximate — confirm the notified rate) |
| Cotton | 8,267 | MSP, medium-staple kapas, cotton season 2026-27 |
| Wheat | 2,585 | MSP, Rabi marketing season 2026-27 (₹2,610 announced for 2027-28) |
| Mustard | 6,200 | MSP, rapeseed and mustard, Rabi 2026-27 (₹6,613 announced for 2027-28) |
| Chickpea | 5,875 | MSP, gram, Rabi 2026-27 |
| Sugarcane | 360 | Fair and Remunerative Price basis; state advised prices differ |
| Pearl Millet | 2,900 | MSP, bajra, Kharif 2026-27 |

When a live price is available it replaces the reference price and `price_basis` changes to
`live mandi modal price`.

### Where a live price comes from

Prices are resolved in this order, and the response always says which one answered:

1. **AGMARKNET via data.gov.in**, when `AGMARKNET_API_KEY` is set. The official feed: every
   state, district-level prices, and a quota of your own. Free, registration only.
2. **A keyless community mirror** of the same government dataset, when no key is configured.
   Covers Karnataka, Madhya Pradesh, Maharashtra, Punjab and Uttar Pradesh only, state-level
   rather than district-level, rate limited to 100 requests per 15 minutes shared across all its
   users, and with no uptime guarantee. It exists so a fresh clone shows real prices rather than
   nothing. Disable with `KEYLESS_MARKET_FALLBACK=false`.
3. **The announced support price**, clearly labelled as MSP.

Two details that matter for correctness:

- **The newest record wins.** A page from either feed mixes commodities and arrival dates in no
  guaranteed order, so taking the first parseable record could quote a price from weeks ago — or
  from a different commodity whose name merely overlapped. Exact commodity matches beat partial
  ones, and within each group the latest arrival date wins.
- **Failures are remembered briefly.** A crop a feed does not report would otherwise cost a fresh
  upstream request on every analysis, which is how a shared quota gets exhausted. Misses are
  cached for `MARKET_MISS_TTL_SECONDS` (default 30 minutes).

### Where no feed reaches: the farmer's own price

No keyless source covers every state. Tested, as of 2026-10-19:

| Source | Keyless | Haryana | Result |
| --- | --- | --- | --- |
| data.gov.in AGMARKNET (official) | no | yes | free, but needs registration |
| CEDA / Ashoka Agmarknet mirror | no | yes | `401 Unauthorised, no api key passed` |
| mandi-api community mirror | yes | **no** | works; 5 states only |
| tgkagro price feed | yes | no | export FOB pricing, no mandi breakdown |
| agmarknet.gov.in website | yes | yes | scraping only: fragile, ToS risk |

So for a Haryana farmer with no key there is no feed at all. The answer is not to invent one:
**the farmer's own mandi price is a first-class input.** `FarmProfile.known_market_prices` maps a
crop to the rate they know, entered inline on the crop card next to the figure it replaces, and
it overrides both the live feed and the reference price everywhere — ranking, revenue, profit,
break-even and every scenario — labelled `the price you entered for your own mandi`.

This is not a consolation prize. A national feed reports a market average for a district; a
farmer standing in their mandi knows the rate they can actually get, which is the number their
break-even genuinely depends on. Where a feed does reach, theirs still wins, for the same reason.

### Commodity naming

AGMARKNET filters are exact-match and the dataset does not use everyday crop names. Filtering on
`Rice` returns nothing; the dataset calls it `Paddy(Dhan)(Common)`. Each crop therefore carries an
ordered list of the dataset's own spellings in `market_data.COMMODITY_CANDIDATES`, tried until one
reports a price. This was a live bug: before it was fixed, every official price lookup would have
silently returned no data.

**These must be rechecked every season.** `crop_data.PRICE_SEASON` and `LAST_REVIEWED` record
which season the table belongs to, and both are returned by the API.

## Yields and costs

Every crop carries `low / typical / high` for both yield and cost, because a single number reads
as a promise. The poor-season case pairs the low yield with the high cost; the good season the
reverse. The UI and both report formats show all three.

Sources are recorded per crop in `crop_data.py` and surfaced in the API response, the PDF and the
text report. They are drawn from state package-of-practices documents, university
cost-of-cultivation studies and state crop-cutting reports.

### Corrections made during the audit

Two figures in the original table were wrong in a way that would have caused real harm:

- **Cotton: 16 quintal/acre.** Roughly 2-3x the realistic kapas yield for Haryana, where pink
  bollworm and whitefly pressure have driven yields down sharply. At the price in the same row
  it implied about ₹75,000/acre profit, while a Haryana agricultural-university cost study
  records an average **loss** of about ₹15,000/acre once realistic yields are used. Now
  `3 / 6 / 10 q/acre`, and the advisory says plainly that a profitable cotton estimate is the
  good-year case.
- **Chickpea: 13 quintal/acre.** Around 2.5-3x published Indian productivity, which made it the
  highest-margin crop in the catalogue purely as an artefact. Now `4 / 6 / 8 q/acre`.

Mustard, bajra and paddy yields were also revised down towards published regional figures, and
every support price was updated to the current season.

## Rainfall

`rainfall` is the **total expected across the season, in millimetres**. This is stated in the
schema, the form label and the field hint, because the original had no stated basis at all: the
UI slider capped at 300 mm, the crop bands were written as if monthly, and live weather
substituted OpenWeather's `rain.1h` — millimetres in the *last hour* — into the same field.

Water availability is now `rainfall + an irrigation allowance` set by the farmer's stated
irrigation access (`Rainfed` 0 mm, `Limited` 250 mm, `Assured` 900 mm). Live weather updates
temperature and humidity only; it never touches the seasonal rainfall figure.

## Soil

pH and NPK are **farmer-entered**, interpreted against standard soil-health-card bands. No soil
laboratory or satellite feed is connected, and the response says so in `note` and `live: false`.
The NPK values are a relative 0-100 index, not kg/ha.

## The crop model

`backend/scripts/build_dataset.py` derives training rows by sampling each crop's documented
envelope. **These rows are derived, not observed** — they encode the same agronomic knowledge the
rule engine uses, so a model trained on them largely re-learns those rules.

The 24-row `crop_training_sample.csv` is hand-written observational data. It is never trained on
and is used only to score the model.

As of the last training run:

| Measure | Value |
| --- | --- |
| Holdout accuracy (derived data) | 0.85 |
| 5-fold cross-validation | 0.82 ± 0.01 |
| Most-frequent-class baseline | 0.13 |
| **Observational sample accuracy** | **0.38** |

That last number is the honest one, and it is why the model's influence on the ranking is scaled
by it rather than assumed. A model with no metrics, or one that cannot beat its baseline, is not
loaded at all. `GET /admin/summary` reports all of this.

Replacing the derived rows with real field records from state agriculture departments is the
single highest-value upgrade available, and nothing else has to change when that happens.

## What would make this trustworthy at scale

1. District-level cost and yield datasets rather than one regional range per crop.
2. A validated, labelled crop-disease image dataset, and a specialist model to replace
   general-purpose vision screening.
3. Review of the whole table by regional agronomists, recorded per crop with a review date.
4. A seasonal process for refreshing support prices, with the review date enforced in CI.
