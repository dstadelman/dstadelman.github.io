# Handoff prompt — "The Corporation as a Force of Nature" lecture series

Paste this into a fresh session to continue the work.

---

We are building a three-part lecture series (three one-hour talks, ~26 slides each) titled **"The Corporation as a Force of Nature."** The audience is working professionals. The presenter works at a large health insurer (UHG) and wants the material kept non-negative and defensible: the thesis is that the corporation is not evil and not ruined by "four bad guys" — it is a force of nature, like weather or an ocean, and understanding that is relieving and empowering, not cynical. This reframe came from the user's own experience: structural thinking made them enjoy their job more.

**The goal (check every slide against it):** bring the viewer from thinking the corporation is evil — or that a few bad apples are hurting it — to realizing what it actually is, and how they can succeed inside it. The emotional arc across the series: victim of the machine → reader of the machine → navigator of it. Naive moralism → calm clarity → calm agency.

**Canonical framing (do not contradict without discussion):**
- Act 1 — The World As It Is (History and Understanding). Dramatic question: what is this thing I live inside? Annie Leonhart quote (Attack on Titan S1) breaks naive moralism: the structure of the organization reveals what true human nature really is. History: the corporate form was patched together under pressure about capital and control (VOC/EIC, Chandler, M-form). Hierarchy re-forms even in orgs founded to prevent it (Michels, Weber, Han Feizi). Ends on relief: the org is weather; you can't fight it and don't have to be sad at it. Final image: standing at the shore.
- Act 2 — Reading the Terrain (How Power Actually Works). Dramatic question: where does power actually live in this specific organization? Formal org chart vs. the real one. Japan is the centerpiece because it names what Western orgs hide: ringi confirms decisions rather than making them; nemawashi is where decisions happen; honne/tatemae are two layers every org runs (Doi: tatemae is a second truth, not a lie). Diagnostics: follow the budget, information, promotions, the pre-meeting, the artifact (Conway's Law). Final image: the map.
- Act 3 — Moving Well (Building and Exercising Power). Dramatic question: given all this, how do I act — and how do I get more power? Navigation, not manipulation. Pfeffer (sponsorship, visibility, resource control, brokerage), the inverse Conway maneuver, doing your own nemawashi, the kiansha move (volunteer to draft the document). Stoic operating stance: Marcus Aurelius 2.1 morning prep, dichotomy of control, 5.20 "the impediment becomes the way," 4.3 the mind as retreat. Ends returning to the Annie quote from the other side: she wasn't the sad one, she was the free one. Final image: the sailor.

The Annie quote opens Act 1 and closes Act 3; the force-of-nature image (weather, ocean, mountain) threads all three. Each lecture repeats the three-act shape internally (setup, turn, resolution).

**Files (single source of truth, in GitHub repo dstadelman/dstadelman.github.io):**
- `_drafts/corporation-as-a-force-of-nature/00-series-overview.md` — the goal + canonical three-act framing (user-approved verbatim text at top)
- `_drafts/corporation-as-a-force-of-nature/01-act1-the-world-as-it-is.md` — beat-by-beat outline, 60 min / ~26 slides
- `_drafts/corporation-as-a-force-of-nature/02-act2-reading-the-terrain.md`
- `_drafts/corporation-as-a-force-of-nature/03-act3-moving-well.md`
Local working copies: `/opt/data/workspace/corporate-power-series/` (plus an older draft deck `lecture1-history-and-understanding.pptx` and its build script — superseded by the outlines; rebuild from the outlines).

**GitHub workflow:** use the post-to-github skill. The PAT is at `/opt/data/.github_pat`. CRITICAL: inside execute_code, never `cat` the token into a variable — tool output masks secrets and you'll send a masked string that 401s. Interpolate in-shell: `curl -s -H "Authorization: Bearer $(cat /opt/data/.github_pat)" ...`. For `_drafts/` files use direct Contents-API PUT (the skill's script only targets `_posts/`). Pull latest from GitHub before editing; push after.

**Book list (from user's call; if only two: The Culture Map, The Anatomy of Self):**
- Erin Meyer, *The Culture Map* — spine of Act 2's Japan section. Authority vs. decision-making are separate dimensions: Japan is simultaneously most hierarchical AND most consensual. Small-d/capital-D decisions: American fast-then-revised, Japanese slow-then-swift.
- Takeo Doi, *The Anatomy of Self* (+ *The Anatomy of Dependence*, amae) — honne/tatemae mutually constitutive; the anti-cynicism slide; amae as the psychology of sponsorship.
- Chie Nakane, *Japanese Society* — vertical society; strong vertical ties, deliberately weak horizontal ones (why brokers are rare and powerful); introduce by company not job.
- Abegglen & Stalk, *Kaisha* — seniority isn't anti-merit: the able get harder assignments years before titles change (Act 3 move: ask for the hard assignment).
- Diana Rowland, *Japanese Business Etiquette* — color details (seating, hanko, how meetings feel).

**Verified citations to use (corrected):**
- Conway's Law: Melvin Conway, 1968.
- Empirical backing: **Nagappan, Murphy & Basili, "The Influence of Organizational Structure on Software Quality," ESEC/FSE 2008 (Microsoft Research)** — org metrics mined from Windows Vista check-in data predicted post-release failures with 86% precision. (An earlier "Vaish, Gajos, Manku 2017" citation was fabricated/wrong — do not use it.) Supporting: Amrit/van Hillegersberg/Kumar TESNA 2012; Zingg et al., PLOS One 2023.
- VOC/legal-form history: Gelderblom, De Jong & Jonker (legal form followed economic function).
- Chandler, *The Visible Hand*; Michels 1911 ("Who says organization, says oligarchy"); Weber's iron cage; Han Feizi.
- Ringi details: the document confirms rather than decides; quiet veto via desk drawer / upside-down seal; the kiansha (drafter) frames the decision.
- Marcus Aurelius passages: 2.1, 4.3, 5.20, 6.30.
- Annie quote is fan-transcribed with subtitle variations — use one version consistently, credit Attack on Titan, Season 1.

**Presentation constraints:** presenter is employed at UHG — keep company examples anonymized or historical; public 10-K facts (segments, headcount, exec rotation) are fine, interpretive jabs stay general. Japan material: present the classic model as "the grammar," with one slide acknowledging lifetime employment/seniority are eroding — keeps it defensible.

**Status / next steps:**
1. Outlines for all three acts exist and are pushed (Conway + book research folded in).
2. Open: fold the goal line into the three act outlines (currently only in the overview).
3. Open: Act 2's worked example beat is the weakest — decide anonymized-vs-historical.
4. Open: build the decks from the outlines (PPTX with speaker notes, or HTML slides — user hasn't chosen; earlier draft deck was dark navy/gold PPTX).
