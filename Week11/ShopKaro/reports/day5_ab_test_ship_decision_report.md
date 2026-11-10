# A/B Test Result: SHIP

**Experiment:** `EXP-2026-REC-ITEMCF-V1` · **Decision:** **SHIP** · **Visitors:** 162,386 (81,163 control / 81,223 treatment)

**Why:** Primary metric significantly better and all guardrails pass.

## Design (fixed before analysis)
- **Hypothesis:** personalised homepage recommendations increase homepage conversion vs popular items.
- **Control A:** top-10 most popular in-stock products. **Treatment B:** item-to-item CF + business re-ranker (production pipeline), trained only on data before the test window (train_interactions + val_interactions).
- **Visitors:** everyone active in the 4-week test window from 2025-06-19; 6.9% had earlier history (returning), the rest are new visitors who get the cold-start page.
- **Assignment:** 50/50 by hashing user ID with an experiment salt.
- **Behaviour (replay):** a shown item is clicked only if the visitor really interacted with it in the test window and the slot is examined (probability 1/log2(rank+1)); a purchase only if they really bought it. No effect size is assumed.
- **Primary metric:** Conversion Rate (CVR). Secondary: CTR, discovery CTR and discovery CVR (clicks / purchases of products the visitor never interacted with before the test, i.e. excluding re-shown history), revenue per visitor, AOV (Holm-corrected). Proportions with fewer than 10 events per arm use Fisher's exact test. Minimum detectable effect: 20% relative.
- **Decision rule:** SHIP: primary metric significantly better (alpha=0.05) and all guardrails pass. DO NOT SHIP: primary metric significantly worse, or any guardrail fails. EXTEND / RAMP: otherwise; keep running until the pre-registered sample size is reached (if the leading indicator CTR is significantly better, ramp traffic to reach it sooner).

## Results
| Metric | Control | Treatment | Relative lift [95% CI] | p | p (Holm) | Significant |
|---|---|---|---|---|---|---|
| Conversion Rate (CVR) (primary) | 0.0086 % | 0.0517 % | +499.6% [+303.7%, +695.4%] | 3.61e-07 | 3.61e-07 | yes |
| Click-Through Rate (CTR) (secondary) | 0.844 % | 2.502 % | +196.4% [+181.7%, +211.2%] | 0.00e+00 | 0.00e+00 | yes |
| Discovery CTR (items not seen before) (secondary) | 0.8292 % | 0.948 % | +14.3% [+3.3%, +25.3%] | 0.011 | 0.021 | yes |
| Discovery CVR (items not seen before) (secondary) | 0.0086 % | 0.0062 % | -28.6% [-125.6%, +68.3%] | 0.581 | 0.581 | no |
| Revenue Per Visitor (RPV) (secondary) | 0.2 PKR | 8.51 PKR | +4230.6% [+1209.8%, +7251.5%] | 0.006 | 0.018 | yes |

AOV not tested: fewer than 20 converters in an arm (7 vs 42).

## Where the gain comes from
- Treatment converters: **42**, of whom **37** bought a product they had already browsed before the test and **5** bought a product they had never seen. Control: 7 converters, 7 on never-seen products.
- Discovery conversion (never-seen products only): 0.0086% vs 0.0062%, p = 0.581 (Holm) — **not significant**: no evidence yet that recommendations sell products shoppers had not already found.
- **Interpretation:** most of the conversion gain comes from re-surfacing products the shopper already browsed (a 'continue shopping' effect). That is real value, but a simple 'recently viewed' row would capture much of it; the ML model's extra value is discovery, measured by the discovery metrics above.
- **Estimated revenue impact** (homepage-attributed only, at 1,000,000 visitors/month): PKR 8,310,000/month, 95% CI PKR 2,380,000 to 14,250,000. Wide interval: based on 49 converters.

### Returning vs new visitors (exploratory)
| Visitors | Users | CTR control | CTR treatment | CTR lift | p | CVR control | CVR treatment |
|---|---|---|---|---|---|---|---|
| New | 151,248 | 0.86% | 0.93% | +8.2% | 0.143 | 0.008% | 0.007% |
| Returning | 11,138 | 0.59% | 23.96% | +3973.2% | 0.00e+00 | 0.018% | 0.669% |

## Power and duration
- Control conversion is 0.009%. To detect a 20% relative change with 80% power this test would need **5,019,157 visitors per arm**; it had 81,163 (power 5%).
- At ShopKaro's traffic (~33,333 visitors/day, from 1M monthly visitors) the full test takes **about 301 days**. Run whole weeks (at least 2) to cover weekday/weekend patterns.

## Guardrails
| Guardrail | Value | Result |
|---|---|---|
| Sample ratio mismatch (chi-square) | p = 0.882 | PASS |
| Out-of-stock impressions | control 0.00% / treatment 0.00% | PASS |
| Max items from one brand (treatment) | 2 (limit 2) | PASS |
| Recommendation latency p95 | 7.0 ms (limit 100) | PASS |

## Sanity check and common mistakes
- **A/A test** (both arms see the control page, different salt): CTR p = 0.450, CVR p = 0.606. Not significant, as expected: the pipeline does not create false differences.
- **Peeking:** in 2,000 simulated A/A tests, testing once at the end gives 5.2% false positives; checking daily and stopping at the first p < 0.05 gives **26.8%**. Fix the sample size in advance (or use a sequential test).
- **Multiple testing:** secondary metrics use Holm correction; subgroup tables are exploratory and not used for the decision.
- **Novelty effect:** real users may click new recommendations just because they are new, and the effect fades; in a live test, compare lift by week and discount the first week. Replayed behaviour cannot contain novelty, yet treatment CTR still falls over the test (week 1: 10.3% returning, returning-visitor CTR 35.5%; week 2: 6.2% returning, returning-visitor CTR 20.1%; week 3: 5.7% returning, returning-visitor CTR 14.3%; week 4: 4.6% returning, returning-visitor CTR 12.3%). That decline is **recency decay**: later visitors are less often returning, and returning visitors' old history predicts less the longer ago it was. A live test would show the same shape and could be misread as novelty; the remedy here is daily retraining plus live session updates (`POST /events`), not discounting week 1.

## Limitations
- Replay only credits items visitors engaged with anyway, so it ignores demand a recommendation creates: lifts are a conservative estimate.
- Visitors see one homepage at their first visit; live session updates (`POST /events`) are not replayed.
- New visitors (93%) get a cold-start page in treatment, which dilutes the overall effect.

_Generated by `scripts/run_day5.py` (`src/shopkaro/ab_testing/experiment.py`). Figure: `reports/figures/14_ab_testing_and_api_latency.png`._
