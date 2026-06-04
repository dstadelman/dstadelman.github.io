# Alert Correlation Engine — Technical Approach & Positioning

## The problem

We want to take alerts firing **right now** and surface the alerts that historically
correlate with them, using ~5 years of alert history. Constraints and facts:

- All alerts live in **PostgreSQL**; there are on the order of **millions of records**.
- Only ~**20%** of alerts have an associated service.
- We have a **service dependency / supply-chain graph** (which service depends on which).
  It is **available but known to be inaccurate**.
- Services have **priorities**.
- Target: a working, demonstrable result in **~1.5 weeks**.

## Core idea: split it into two problems

The single most important decision is to separate the heavy work from the fast work.

1. **Offline — mine correlations from history.** Expensive, runs in SQL/Python over the
   full 5 years. Done once, then refreshed on a schedule (e.g. nightly). Produces a small
   "correlation knowledge base."
2. **Online — "what correlates with this alert right now."** Just a lookup against what
   was precomputed offline. Cheap, fast, real-time.

A common instinct is to push everything into an LLM. That fails here: an LLM cannot hold
millions of records in context, and — more fundamentally — finding co-occurrence across
millions of records is a **counting/statistics problem, not a reasoning problem**. The LLM
has a real role, but at the end of the pipeline, not the middle (see "Where the LLM fits").

## The reframe that makes millions of rows manageable

We do **not** correlate alert *records*. We correlate alert *signatures* —
`alert_name + service + (optionally host/check)`, normalized to a canonical form.

There are millions of records but likely only a few **thousand distinct signatures**. Once
collapsed to signatures, the entire correlation matrix fits comfortably in memory.

> **First thing to run:** `SELECT COUNT(DISTINCT signature) FROM alerts;`
> This number drives feasibility. Under ~10k is ideal. If it is very large
> (e.g. hundreds of thousands), we have a signature-normalization problem to solve first
> (see DBSCAN note below).

## The method (the analytical spine)

We measure how often pairs of alert signatures occur close together in time, across all of
history, and turn that into a directional correlation score.

### Why an interval join, not fixed time buckets

The naive approach is to chop time into fixed 15-minute buckets and pair alerts that share a
bucket. That has a fatal flaw: the **boundary problem**. If alert A fires near the end of one
bucket and alert B fires shortly after, in the *next* bucket, they are only seconds apart but
land on opposite sides of an arbitrary line — so a bucket-based join never pairs them. Real
correlations get silently dropped depending on where the clock happens to fall.

The fix is an **interval (range) join**: pair A and B whenever B fires within **15 minutes**
*after* A, measured directly against the actual timestamps. There are no buckets and no
boundaries, so nothing falls through a crack. Pairing "B after A" also makes the relationship
**directional**, which is exactly what we want for "when A fires, B tends to follow."

### Core engine (interval join)

```sql
-- For each A-event, find the B-signatures that fire within 15 minutes after it
WITH followed AS (
  SELECT a.signature AS sig_a, a.alert_time AS a_time, b.signature AS sig_b
  FROM alerts a
  JOIN alerts b
    ON b.alert_time >  a.alert_time
   AND b.alert_time <= a.alert_time + interval '15 minutes'
   AND b.signature <> a.signature
),
-- collapse so multiple B-firings don't overcount a single A-event
pair_events AS (
  SELECT DISTINCT sig_a, a_time, sig_b
  FROM followed
),
pair_counts AS (
  SELECT sig_a, sig_b, COUNT(*) AS a_events_followed_by_b
  FROM pair_events
  GROUP BY 1, 2
  HAVING COUNT(*) >= 5          -- minimum support; kills noise
),
sig_counts AS (
  SELECT signature, COUNT(*) AS n_events
  FROM alerts
  GROUP BY 1
)
SELECT pc.sig_a, pc.sig_b,
       pc.a_events_followed_by_b,
       pc.a_events_followed_by_b::float / sa.n_events AS p_b_follows_a
FROM pair_counts pc
JOIN sig_counts sa ON sa.signature = pc.sig_a
ORDER BY p_b_follows_a DESC;
```

The headline signal is **`p_b_follows_a`** = "of all the times A fired, the fraction where B
followed within 15 minutes." It is directional and intuitive, and it *is* the correlation
knowledge base. Store the output as a Postgres table; runtime correlation is then just:

```sql
SELECT sig_b, p_b_follows_a
FROM correlations
WHERE sig_a = $firing_signature
ORDER BY p_b_follows_a DESC
LIMIT 20;
```

Notes and refinements:

- **Index `alert_time`** (btree). The interval join's cost scales with alert *density* — how
  many alerts fall inside any 15-minute span — not with total row count. A wider window (we
  chose 15 min) is more forgiving of timing but pulls in larger neighborhoods, so the join
  does more work and storms can spike it. Cap or sample pathological storm windows if needed.
- **Direction vs symmetry.** As written this captures "B follows A." That directionality is
  usually what you want (lead/lag, root cause). For a symmetric "they co-occur" view, also
  count the reverse direction, or use `abs(b.alert_time - a.alert_time) <= interval '15 minutes'`.
- **Base-rate correction (optional).** A noisy alert that fires constantly will look correlated
  with everything. To correct, divide `p_b_follows_a` by B's background rate over a 15-minute
  span (roughly `n_events_B * 15min / total_time_span`). Values well above 1 are genuinely
  associated beyond chance. Add this once the core is working.
- **Alternative view for validation (optional).** *Sessionization* — grouping alerts into
  bursts that break only after a quiet gap — matches how incidents actually behave and can be
  run as a second opinion to sanity-check the interval results on a known past incident.

### Clustering: where it actually belongs

Take the correlation table, threshold it, and run **graph community detection**
(Louvain / Leiden via networkx or igraph — minutes of work). This yields **groups of alerts
that storm together**, so at runtime we can collapse, say, 40 active alerts into
"one incident — community #7." This is the right kind of clustering for this problem.

**On DBSCAN** (Density-Based Spatial Clustering of Applications with Noise): it groups points
packed tightly together and flags isolated points as noise/outliers. Knobs are `epsilon`
(neighbor radius) and `minPts` (density threshold). Advantages over k-means: no need to
predeclare the number of clusters, finds non-spherical shapes, explicitly handles outliers.

DBSCAN is **not** the correlation engine here — run on raw alert points it mostly rediscovers
"it's busy right now." Its one genuinely useful role is **signature normalization**: cluster
alert *message text* (via embeddings) with DBSCAN/HDBSCAN to fold messy free-text into clean
canonical signatures. Use it there if signatures are dirty.

## Using the dependency graph and the 20%

Because only ~20% of alerts carry a service, **co-occurrence must be the backbone** — it works
on every alert regardless of service annotation. Layer the dependency graph in as a
**secondary, lower-weighted** signal, used mainly for:

- **Direction / root cause**: if A depends on B and both fire, B is the likelier cause.
- **Ranking the cluster head**: service priority indicates which alert to surface first.

Since the graph is inaccurate, **validate it against the empirical co-occurrence**. If a
dependency edge never shows up in the historical counts, distrust it. The data overrides the
declared topology, not the other way around.

## Where the LLM fits

Once the system has produced a **small** correlated cluster (5–20 signatures + dependency
context + priorities), pass *that* to an LLM to generate a plain-English incident summary /
probable-root-cause hypothesis. Tiny context, high value. This is the version of
"use an LLM" that actually works — the LLM explains the result; it does not do the
cross-history analysis.

## Suggested 1.5-week sequence

| Days | Work |
|------|------|
| 1–2  | Define the signature, check distinct-signature cardinality, confirm 15-min window |
| 3–5  | Build the interval-join co-occurrence job → produce the correlation table |
| 6–7  | Build the correlation graph + community detection + the runtime lookup query |
| 8–9  | Wire live alerts to the lookup, basic output, add the LLM summary layer |
| 10   | Buffer: validate and tune thresholds |

**Validation tip (worth a half-day):** if we have past incidents with IDs or postmortems,
use them as ground truth — confirm the communities recover those known groupings. This is how
we defend the thresholds when someone asks "why these numbers?"

## Executive positioning

The audience wants "AI." The point to make is that this *is* AI — it is simply the **right**
AI for the job, not a generative LLM. The recommended framing is honest and defensible:

- **Keep the LLM in the architecture** at the summary layer, so "AI-powered, uses an LLM"
  is literally true — while the analytical engine underneath does the heavy lifting.
- **Lead with outcomes**, not methods: fewer pages, faster root cause, "40 alerts collapse
  into 1 incident with a one-line explanation."
- **Demo on a real past incident**: show a storm that historically took hours to untangle,
  then show the system grouping it instantly. One before/after slide beats any architecture
  diagram.

Technique-to-business-language translation:

| What it is | How to describe it |
|------------|--------------------|
| Interval co-occurrence mining | Unsupervised pattern learning across 5 years of incidents |
| `p_b_follows_a` / base-rate correction | Probabilistic correlation scoring |
| Graph + community detection | AI-driven incident graph that discovers how failures cascade |
| Dependency overlay | Topology-aware root-cause inference |
| The whole system | A self-learning correlation engine that improves every night |

**One-line pitch:** *"It learns from every alert we've ever fired, predicts which alerts are
really one incident, and uses an LLM to explain it in plain English to the on-call engineer —
cutting alert noise and mean-time-to-resolution."*

**Caution:** do not let it get sold as "the LLM does it." If leadership believes it is a thin
LLM wrapper, we inherit LLM expectations (and eventually "why not just use ChatGPT?").
Framing it as *"AI-powered with an LLM explanation layer, built on a purpose-built correlation
engine"* earns the credit while protecting the work technically and politically.

## Open questions that would refine the plan

1. **Distinct-signature count** — determines feasibility and whether normalization is needed first.
2. **Labeled past incidents** — availability determines how rigorously we can validate and tune.
3. **Runtime latency target** — affects how the online lookup is served.
