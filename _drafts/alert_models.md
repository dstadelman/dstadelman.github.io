# P1 War Room Detection — Implementation Plan

Anomaly detection on an org-wide alert stream to detect P1 incident regimes ("war rooms").
Stack: **Python + PostgreSQL**. Ordered by effort-vs-payoff: each phase ships a working detector before the next begins.

---

## Architecture Overview

```
alerts (raw stream)
   │
   ▼
[Phase 1] Baselines: per-service negative binomial rate models (hour-of-week seasonal)
   │
   ▼
[Phase 2] Window features every 5 min: surprise, breadth, entropy, novelty
   │
   ▼
[Phase 3] CUSUM detector on combined surprise score  ──► pages / flags war room
   │
   ▼
[Phase 4] Backtest + evaluation harness against labeled historical P1s
   │
   ▼
[Phase 5+] v2 upgrades: Hawkes intensity, supervised classifier, eigenvalue correlation
```

Design principle: **volume alone is not the signal.** War rooms are regime changes visible in
*breadth* (many services), *entropy* (diverse alert mix), and *novelty* (rare signatures), not just count.

---

## Postgres Schema

```sql
-- Raw alert stream (assumed to already exist in some form)
CREATE TABLE alerts (
    alert_id      BIGSERIAL PRIMARY KEY,
    fired_at      TIMESTAMPTZ NOT NULL,
    signature     TEXT NOT NULL,          -- normalized alert identity
    service       TEXT NOT NULL,
    team          TEXT,
    severity      TEXT,
    host          TEXT
);
CREATE INDEX idx_alerts_fired_at ON alerts (fired_at);
CREATE INDEX idx_alerts_service_time ON alerts (service, fired_at);
CREATE INDEX idx_alerts_signature_time ON alerts (signature, fired_at);

-- Per-service seasonal baselines (hour-of-week buckets: 0..167)
CREATE TABLE service_baselines (
    service       TEXT NOT NULL,
    hour_of_week  SMALLINT NOT NULL,      -- 0 = Mon 00:00 UTC
    mu            DOUBLE PRECISION,       -- mean alerts per 5-min window
    r             DOUBLE PRECISION,       -- NB dispersion parameter
    p             DOUBLE PRECISION,       -- NB success prob (derived)
    n_windows     INTEGER,                -- sample size behind the fit
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (service, hour_of_week)
);

-- Signature frequency table for novelty scoring
CREATE TABLE signature_stats (
    signature     TEXT PRIMARY KEY,
    first_seen    TIMESTAMPTZ,
    last_seen     TIMESTAMPTZ,
    count_30d     INTEGER,                -- rolling 30-day count, refreshed nightly
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Computed window features (the detector's input)
CREATE TABLE window_features (
    window_start  TIMESTAMPTZ PRIMARY KEY,   -- 5-min aligned
    total_alerts  INTEGER,
    surprise      DOUBLE PRECISION,          -- sum of per-service -log P(X >= k)
    breadth_svc   INTEGER,                   -- distinct services alerting
    breadth_team  INTEGER,                   -- distinct teams alerting
    entropy       DOUBLE PRECISION,          -- Shannon entropy of signature mix
    novelty_frac  DOUBLE PRECISION,          -- fraction of alerts w/ rare signatures
    score         DOUBLE PRECISION           -- combined weighted score
);

-- Detector state + emitted events
CREATE TABLE detector_state (
    detector      TEXT PRIMARY KEY,          -- e.g. 'cusum_v1'
    state         JSONB,                     -- e.g. {"S": 3.2, "last_window": "..."}
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE detections (
    detection_id  BIGSERIAL PRIMARY KEY,
    detector      TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    ended_at      TIMESTAMPTZ,
    peak_score    DOUBLE PRECISION,
    features      JSONB                      -- snapshot of contributing features
);

-- Ground truth for evaluation
CREATE TABLE incidents (
    incident_id   TEXT PRIMARY KEY,          -- e.g. Jira/PagerDuty ID
    declared_at   TIMESTAMPTZ NOT NULL,      -- war room opened
    resolved_at   TIMESTAMPTZ,
    severity      TEXT,                      -- 'P1', 'P2', ...
    services      TEXT[]
);
```

---

## Implementation Order (GitHub Issues)

Copy each block below into a GitHub issue. Labels suggested: `phase-1` … `phase-6`, `model`, `infra`, `eval`.

---

### Issue #1 — Alert normalization & ingestion audit
**Labels:** `phase-1`, `infra`
**Effort:** S

Everything downstream depends on clean `signature` and `service` fields.

**Tasks**
- [ ] Define signature normalization (strip hostnames, IDs, timestamps from alert titles → stable identity)
- [ ] Verify `fired_at` is event time, not ingest time; document any lag
- [ ] Backfill `alerts` table with ≥ 90 days of history
- [ ] Nightly job to refresh `signature_stats` (rolling 30-day counts)

**Acceptance criteria**
- Top 50 signatures by volume manually reviewed: no two rows that are "the same alert" with different signatures
- 90 days of history loaded; row counts match source system ±1%

---

### Issue #2 — Per-service negative binomial baselines
**Labels:** `phase-1`, `model`
**Effort:** M

Fit seasonal rate baselines. Use **negative binomial**, not Poisson — alert counts are overdispersed
(variance >> mean), and Poisson baselines will page you every deploy.

**Python outline**
```python
import pandas as pd
from scipy import stats

def fit_baselines(engine, lookback_days=60):
    df = pd.read_sql("""
        SELECT service,
               date_trunc('hour', fired_at)
                 + floor(extract(minute from fired_at)/5) * interval '5 min' AS w,
               count(*) AS k
        FROM alerts
        WHERE fired_at > now() - interval '%s days'
        GROUP BY 1, 2
    """ % lookback_days, engine)

    # hour-of-week bucket, densify zero-count windows (important!)
    df["how"] = (df.w.dt.dayofweek * 24 + df.w.dt.hour)

    rows = []
    for (svc, how), g in df.groupby(["service", "how"]):
        counts = densify_with_zeros(g, lookback_days)   # include windows with 0 alerts
        mean, var = counts.mean(), counts.var()
        if var <= mean:                                  # underdispersed → Poisson fallback
            r, p = None, None
        else:
            r = mean**2 / (var - mean)                   # method of moments
            p = r / (r + mean)
        rows.append((svc, how, mean, r, p, len(counts)))
    upsert_baselines(engine, rows)
```

**Tasks**
- [ ] Fit job (weekly cron), writing to `service_baselines`
- [ ] Zero-window densification (a service that fired nothing still counts as an observation)
- [ ] Poisson fallback when variance ≤ mean or sample size is small
- [ ] Minimum-rate floor so dead-quiet services don't produce infinite surprise on 1 alert

**Acceptance criteria**
- Baselines exist for every service with ≥ 100 alerts in lookback
- Spot check 5 known-noisy and 5 known-quiet services: fitted mean within eyeball range of reality
- Q–Q plot or PIT histogram for 3 services shows NB fits better than Poisson

---

### Issue #3 — Window feature pipeline (every 5 min)
**Labels:** `phase-2`, `model`
**Effort:** M

Compute the four features that separate "noisy Tuesday" from "P1".

**Python outline**
```python
import numpy as np
from scipy import stats

def compute_window(engine, window_start, window_end):
    alerts = load_alerts(engine, window_start, window_end)
    baselines = load_baselines(engine, hour_of_week(window_start))

    # 1) Surprise: sum over services of -log P(X >= k)
    surprise = 0.0
    for svc, k in alerts.groupby("service").size().items():
        b = baselines.get(svc)
        if b and b.r:
            tail = stats.nbinom.sf(k - 1, b.r, b.p)
        else:
            tail = stats.poisson.sf(k - 1, max(b.mu, RATE_FLOOR))
        surprise += -np.log(max(tail, 1e-300))

    # 2) Breadth
    breadth_svc = alerts.service.nunique()
    breadth_team = alerts.team.nunique()

    # 3) Entropy of signature mix
    p = alerts.signature.value_counts(normalize=True).values
    entropy = -(p * np.log(p)).sum() if len(p) else 0.0

    # 4) Novelty: fraction with rare signatures (< N sightings in 30d)
    rare = load_rare_signatures(engine, threshold=5)
    novelty = alerts.signature.isin(rare).mean() if len(alerts) else 0.0

    score = combine(surprise, breadth_svc, entropy, novelty)  # z-score & weight
    insert_window_features(engine, window_start, ...)
```

**Combining:** z-score each feature against its own trailing 30-day distribution, then
`score = 1.0*z_surprise + 1.0*z_breadth + 0.5*z_entropy + 0.5*z_novelty`. Weights are a starting
point; Phase 4 backtesting tunes them (or Phase 6 replaces them with a classifier).

**Tasks**
- [ ] 5-min cron (or streaming consumer) computing and inserting `window_features`
- [ ] Backfill features for the full 90-day history (needed for evaluation)
- [ ] Trailing z-score normalization with robust stats (median/MAD, not mean/std — features are heavy-tailed)

**Acceptance criteria**
- Features backfilled for 90 days with < 0.1% missing windows
- Pipeline latency: window features available < 60 s after window close
- Sanity check: pull the 10 highest-`score` windows — a human agrees most look "interesting"

---

### Issue #4 — CUSUM changepoint detector
**Labels:** `phase-3`, `model`
**Effort:** S

Page on sustained regime change, not single spiky windows.

**Python outline**
```python
def cusum_step(engine, window_start):
    feat = load_window(engine, window_start)
    st = load_state(engine, "cusum_v1")     # {"S": float, "active": bool, ...}

    drift = feat.score - K_ALLOWANCE        # K ≈ 0.5 * expected shift, in z units
    S = max(0.0, st["S"] + drift)

    if S > H_THRESHOLD and not st["active"]:
        open_detection(engine, window_start, feat)      # → page / Slack
        st["active"] = True
    elif st["active"] and S < H_CLEAR:                   # hysteresis on the way down
        close_detection(engine, window_start)
        st["active"] = False

    save_state(engine, "cusum_v1", {**st, "S": S})
```

**Tasks**
- [ ] CUSUM with hysteresis (separate open/close thresholds) writing to `detections`
- [ ] Cooldown: don't emit a new detection < 30 min after closing one (merge instead)
- [ ] Shadow mode first: log detections, no paging

**Acceptance criteria**
- Runs continuously for 1 week in shadow mode with zero crashes / state corruption
- Detection open/close events visible in `detections` with feature snapshots

---

### Issue #5 — Ground truth + backtest harness
**Labels:** `phase-4`, `eval`
**Effort:** M

This is where "is the model working" becomes a number. **Do not skip.**

**Tasks**
- [ ] Load historical P1 incidents into `incidents` (from PagerDuty/Jira/incident tool) — target ≥ 30 incidents
- [ ] Backtest runner: replay `window_features` history through the detector with configurable (K, H)
- [ ] Matching rule: a detection is a **true positive** if it overlaps `[declared_at − 30 min, resolved_at]` of a P1
- [ ] Grid search over (K, H, feature weights); produce precision/recall/lead-time table
- [ ] Report notebook: per-incident timeline plots (score vs. time, detection spans, incident spans)

**Acceptance criteria**
- Backtest of 90 days completes in < 10 min
- Report shows the metric table below for at least 3 threshold settings

---

### Issue #6 — Go-live gate & alerting integration
**Labels:** `phase-4`, `infra`
**Effort:** S

**Tasks**
- [ ] Wire detections to Slack channel (not paging yet)
- [ ] 2-week live shadow evaluation against real incidents
- [ ] Go/no-go review against success criteria (below)
- [ ] If go: page on detection open; runbook link in the page

---

### Issue #7 — v2: Hawkes process intensity feature
**Labels:** `phase-5`, `model`
**Effort:** L

Self-exciting point process — the principled version of "alert A raises P(alert B)".
`λ(t) = μ + Σ α·exp(−β(t − tᵢ))`. Fit μ, α, β per service (MLE via `tick` library or hand-rolled
EM); add instantaneous intensity ratio `λ(t)/μ` and branching ratio `α/β` as window features.

**Acceptance criteria**
- Adding Hawkes features to the backtest improves precision at fixed recall by a measurable margin (else: close as not-worth-it — that's a valid outcome)

---

### Issue #8 — v2: Supervised classifier on window features
**Labels:** `phase-6`, `model`
**Effort:** M

Once ≥ 30–50 labeled P1s exist: gradient-boosted trees (XGBoost/LightGBM) on window features,
labels = "window overlaps a P1". Time-based train/test split (never random — leakage).
Replaces the hand-weighted `score`; CUSUM then runs on the classifier probability.

**Acceptance criteria**
- Beats the hand-tuned v1 on time-split holdout (PR-AUC), or issue is closed with findings

---

### Issue #9 — v2 (optional): Cross-service correlation eigenvalue
**Labels:** `phase-6`, `model`
**Effort:** L

Rolling co-firing correlation matrix across top-N services; track largest eigenvalue vs.
Marchenko–Pastur null. Spikes when services fail *together*. Only pursue if breadth/novelty
still miss correlated multi-service incidents in the backtest error analysis.

---

## Success / Failure Criteria

### Primary metrics (measured on backtest + 2-week live shadow)

| Metric | Definition | Success | Failure |
|---|---|---|---|
| **Recall (P1 detection rate)** | % of P1 war rooms with an overlapping detection | ≥ 80% | < 60% |
| **Precision** | % of detections that overlap a real P1 (or P2+) | ≥ 50% | < 25% |
| **False alarms / week** | Detections matching no incident | ≤ 3 | > 10 |
| **Detection lead/lag time** | Median (detection open − war room declared). Negative = we saw it first | ≤ +10 min (ideally negative) | > +30 min |
| **Time to detect from first symptom** | Detection open − first related alert | ≤ 15 min | > 45 min |

### Secondary / operational

| Metric | Success | Failure |
|---|---|---|
| Pipeline latency (window close → score) | < 60 s | > 5 min |
| Pipeline uptime over shadow period | > 99% | < 95% |
| Baseline fit coverage | Every service ≥ 100 alerts/60d has a baseline | Major services missing |
| On-call trust (survey after 1 month live) | "Useful, keep it" majority | "Muted the channel" |

### Interpretation guide

- **High recall, low precision** → detector fires on deploy storms / monitoring flaps. Fix: raise CUSUM allowance K, upweight breadth & novelty over raw surprise, add deploy-window suppression.
- **Low recall, high precision** → thresholds too conservative, or some P1s are "quiet" (low alert volume, e.g. silent data corruption). Check per-incident plots: if the score never moved during a missed P1, no threshold will fix it — you need a new feature (that's what Issues #7–#9 are for).
- **Good backtest, bad live** → data drift or leakage in the backtest (e.g. baselines fitted on data that includes the test incidents). Refit baselines walk-forward.
- **Detection consistently lags war room declaration by > 30 min** → the model is confirming what humans already know = not useful. Investigate faster windows (1 min) and per-alert streaming scoring.

### Kill criteria

Stop and rethink (rather than endlessly tuning) if, after Phase 4 grid search:
- No (K, H, weights) setting achieves recall ≥ 60% at ≤ 10 false alarms/week, **and**
- Error analysis shows missed P1s produce no visible movement in *any* feature.

That outcome means the alert stream itself doesn't carry the P1 signal for your org, and the next
step is new data sources (deploy events, SLO burn rates, traffic metrics), not new math on alerts.

---

## Suggested Milestones

| Milestone | Issues | Target |
|---|---|---|
| M1: Data foundation | #1, #2 | Week 1–2 |
| M2: Scoring live | #3, #4 | Week 3 |
| M3: Evaluated | #5, #6 | Week 4–5 |
| M4: v2 iteration | #7–#9 | As justified by M3 error analysis |
