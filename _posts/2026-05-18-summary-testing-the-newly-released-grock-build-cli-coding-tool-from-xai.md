---
layout: "post"
title: "Summary: Testing the Newly Released Grock Build CLI Coding Tool from XAI"
date: 2026-05-18 13:17:41 -06:00
---

## Summary

The BridgeMind creator tests **Grok Build**, XAI's newly released AENT CLI coding tool positioned to compete with Claude Code and Codex. He's purchased a Super Grok Heavy subscription to put it through real workflow tasks on the BridgeMind ecosystem.

The video opens with benchmark context. On the Artificial Analysis coding index, Grok 4.3 (500B parameters) scores 41 — behind GPT-5.5 at 59, Gemini 3.1 at 55, and Claude Opus 4.7 at 53. But on the intelligence index, Grok scores 53, much closer to the frontier models. The reviewer notes that a 500B parameter model performing near frontier models is notable, suggesting Grok 5 could be very competitive.

**Sub-agent stability.** Requesting 50 sub-agents for a security audit crashes Grok Build entirely — a thread stack panic in `crates/codegen/xi/groq_shell/src/session`. Requesting 200 sub-agents for a performance review has the same result. Claude Code handles 100 sub-agents without issue. When Grok Build does process requests, it often under-delivers: 50 requested yields 7, 100 requested yields 14.

**Plan mode UI.** Praise is reserved for the plan mode implementation. A modal popup displays the structured plan with approve (A), comment (C), and quit (Q) actions. The reviewer calls the UI clean and well-designed.

**Slow planning times.** A Remotion marketing video task took 24 minutes and 32 seconds just to produce a plan. Even accounting for scope, the reviewer finds this excessive.

**Design output quality.** Asked to rebuild the BridgeMind website as a Next.js/Shadcn revamp using 10 sub-agents, the output is severely flawed. Products page contains a double navbar — a fundamental layout bug. The reviewer calls the result "worse than Kimi K2.6" and "GPT-4 type stuff," stating that using Grok 4.3 in a serious vibe-coding workflow is not viable.

**Built-in image generation (`grok imagine`).** Highlighted as a unique advantage over Claude Code. The reviewer tests it by requesting an infographic for the BridgeVoice product page. It successfully generates and applies an image through the code generation pipeline — an end-to-end workflow Claude Code cannot complete. Note: GBT 5.5 Image Gen 2 still produces better images, but the capability itself is valued.

**Usage rate limits.** The most critical finding. After roughly one hour of workflow testing, the Super Heavy plan already shows 8% usage on a two-week billing cycle (resets May 31). The reviewer calls this "a complete ripoff" and notes that typical 6-8 hour sessions would consume 50% of the two-week allowance in a single sitting, making serious usage impossible.

**Verdict:** Grok Build does not earn the "BridgeMind stamp of approval" for two reasons: the rate limits that make the $300/month plan financially impractical, and the underlying Grok 4.3 model being far behind frontier models in coding and design tasks. Claude Code with Opus 4.7 and Codex with GPT-5.5 are identified as objectively superior choices.
