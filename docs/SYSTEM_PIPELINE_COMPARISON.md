# System Pipeline Comparison

Measured 2026-07-29. Artifact: `evaluation/results/system_pipeline_comparison.json`.

Two candidate product architectures, scored on the **same** internal held-out split
(34 records) with the **same** frozen `compact_router_v1` prompt and the same scoring code.

| | Pipeline A | Pipeline B |
|---|---|---|
| Routing | hosted `gemma-4-26b-a4b-it` | fine-tuned `gemma-4-E2B-it` adapter |
| Image analysis | hosted `gemma-4-26b-a4b-it` | hosted `gemma-4-26b-a4b-it` |
| Hosted calls per routing request | **1** | **0** |

---

## 1. Pipeline A — measured

Hosted 26B routing the Step-3 internal test split under the compact prompt.

| Metric | Value |
|---|---|
| Intent accuracy | **70.6%** |
| Tool-selection accuracy | **50.0%** |
| Structured-output validity | 97.1% |
| Valid intent-enum rate | 97.1% |
| Tool allow-list rate | **100%** |
| Unknown-function rate | **0%** |
| Safety pass rate | **100%** |
| Uncertainty accuracy | 100% |
| API failure rate | 2.9% (1 of 34) |
| Median latency | **18 546 ms** |
| p90 latency | 32 266 ms |
| Hosted calls | 33 |

## 2. Pipeline B — not measured

**Status: no accepted adapter.** The Kaggle run reached a passing memory smoke test and a
correctly attached LoRA (5.7 M trainable / 3.94 B, 0.14%), but full training had not
completed at the time of writing. Pipeline B's routing row is therefore empty.

**Pipeline B is not claimed to be better.** The comparison JSON encodes that explicitly and
will only render a verdict once tuned routing numbers exist:

```
"verdict": "Pipeline B is NOT claimed better. Its routing half is unmeasured
            until a tuned adapter passes the Step-3 acceptance gate."
```

## 3. What Pipeline B would have to beat

| Bar | Value | Source |
|---|---|---|
| Intent accuracy | **> 70.6%** | Pipeline A, this document |
| Tool accuracy | **> 50.0%** | Pipeline A, this document |
| Structured validity | ≥ 97.1% | Pipeline A |
| Safety pass | 100% (no regression permitted) | Pipeline A |
| Untuned E2B floor | 0.0% intent | `docs/E2B_UNTUNED_BASELINE_REPORT.md` |

The acceptance gate additionally demands ≥90% intent, ≥90% tool, 100% structured validity,
100% safety, and ≥15 pp improvement over untuned E2B. Note that the last of those is the
*weakest* of the criteria here, because the untuned floor is 0.0% — clearing it proves the
adapter learned the output contract, not that it beats the hosted model.

**The decision-relevant bar is Pipeline A's 70.6%, not the untuned 0.0%.**

## 4. Why Pipeline B is attractive if it clears the bar

- **Removes one hosted call per routing request.** Routing is the most frequent
  interaction; image analysis is comparatively rare.
- **Latency.** Pipeline A's routing median is 18.5 s. The untuned E2B produced its (unusable)
  output with a median of **472 ms** on a T4 — roughly 40× faster. Even allowing for a
  slower tuned model and cold starts, local routing is a different order of magnitude.
- **Offline capability.** A local router keeps intent classification and tool selection
  working when the network does not, feeding the existing offline sync queue.
- **Cost and rate limits.** Pipeline A hit one API failure in 34 requests (2.9%). Every
  routing request avoided is one fewer chance to hit a quota or a 5xx.

## 5. Why Pipeline A stays production for now

It is measured, it is safe (100% safety pass, 0% unknown-function), and it is what the
Step-1 and Step-2 gates validated. Pipeline B has no measured routing half.

**No switch is made on speculation.** Section 15 of the Step-3 brief is explicit: when the
adapter does not pass, it is not integrated as the default. `FineTunedE2BRouterProvider`
therefore ships disabled — `readiness()` reports `available: false` with the reason, and
`route()` raises rather than silently falling back.

## 6. Honest caveats about this comparison

1. **The E2B baseline and Pipeline A did not get identical prompts.** Pipeline A received
   the frozen compact prompt **plus a one-line JSON format hint**; the untuned E2B baseline
   received the compact prompt alone. That is why the E2B floor is 0.0% structured
   validity. The tuned-vs-untuned comparison inside the notebook *is* like-for-like; this
   cross-pipeline comparison is not, and should not be quoted as if it were.
2. **34 records is a small test set.** One record is worth 2.9 pp. Differences under ~6 pp
   are not meaningful here.
3. **Latency is not measured on equal hardware.** Pipeline A is a hosted API call over the
   internet; E2B latency was measured on a Kaggle T4. A phone or laptop would be slower.
4. **Image analysis is unchanged in both pipelines**, so this comparison is about routing
   only — it says nothing about catch-photo quality.
