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

1. **Bucket** alerts into time windows (start with 5 minutes).
2. For each **pair of signatures**, count how often they land in the same window across all
   of history.
3. From those counts, compute **association strength**:
   - **Lift** — values > 1 indicate a real positive association (beyond base rates).
   - **Conditional probability** `P(B | A)` — directional: "when A fires, B follows X% of
     the time."
4. Keep pairs that clear a **minimum support** count (kills noise) and a strength threshold.

The output is an **edge list**: `(signature_A, signature_B, strength)`. That edge list *is*
the correlation knowledge base. Store it as a Postgres table. Runtime correlation becomes a
simple ordered lookup.

### Core engine (SQL sketch)

```sql
WITH bucketed AS (
  SELECT date_bin('5 minutes', alert_time, TIMESTAMP '2020-01-01') AS bucket,
         signature
  FROM alerts
  GROUP BY 1, 2            -- dedupe within bucket; keeps the self-join sane
),
pairs AS (
  SELECT a.signature AS sig_a, b.signature AS sig_b, COUNT(*) AS cooccur
  FROM bucketed a
  JOIN bucketed b ON a.bucket = b.bucket AND a.signature < b.signature
  GROUP BY 1, 2
  HAVING COUNT(*) >= 5     -- support threshold
)
SELECT sig_a, sig_b, cooccur,
       cooccur::float / ca.n AS p_b_given_a,
       (cooccur::float * t.N) / (ca.n * cb.n) AS lift
FROM pairs
JOIN (SELECT signature, COUNT(DISTINCT bucket) n FROM bucketed GROUP BY 1) ca
  ON ca.signature = sig_a
JOIN (SELECT signature, COUNT(DISTINCT bucket) n FROM bucketed GROUP BY 1) cb
  ON cb.signature = sig_b
CROSS JOIN (SELECT COUNT(DISTINCT bucket) N FROM bucketed) t;
```

Notes:
- Cost scales with **signatures-per-bucket**, not total row count, which is why the
  dedupe-within-bucket `GROUP BY` matters.
- Fixed time bins can miss correlations that straddle a bin boundary. Ship fixed bins first;
  if accuracy needs improving, switch to an interval join on
  `abs(a.alert_time - b.alert_time) <= window`.

### Clustering: where it actually belongs

Take the edge list, threshold it, and run **graph community detection** (Louvain / Leiden via
networkx or igraph — minutes of work). This yields **groups of alerts that storm together**,
so at runtime we can collapse, say, 40 active alerts into "one incident — community #7."
This is the right kind of clustering for this problem.

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
| 1–2  | Define the signature, check distinct-signature cardinality, pick window size |
| 3–5  | Build the co-occurrence job → produce the edge table |
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
| Co-occurrence mining | Unsupervised pattern learning across 5 years of incidents |
| Lift / conditional probability | Probabilistic correlation scoring |
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
