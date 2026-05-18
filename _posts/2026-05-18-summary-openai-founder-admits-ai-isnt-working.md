---
layout: "post"
title: "Summary: OpenAI founder admits AI isn't working"
date: 2026-05-18 19:47:21 -0600
---

[BridgeMind - Summary: OpenAI founder admits AI isn't working](https://www.youtube.com/watch?v=ZugX7a99dLk)

# Summary: OpenAI founder admits AI isn't working
[Mo Bitar — OpenAI founder admits AI isn't working](https://www.youtube.com/watch?v=ZugX7a99dLk)

## Summary

Mo Bitar examines a recent interview with Andre Karpathy that exposes a fundamental contradiction at the heart of the AI coding tool narrative: Karpathy claims he no longer needs to review AI-generated code because the models have improved to the point of trust, yet simultaneously describes getting "heart attacks" when actually inspecting the output, calling it "bloaty," "copypaste-heavy," and filled with "awkward brittle abstractions." The code "works" but is "really gross" — a detail Bitar rightly flags as anything but charming when this same technology is being sold as a replacement for human judgment across domains.

Karpathy's workflow, as described, hinges on spec-first engineering. He writes an extremely detailed markdown document covering every edge case, then prompts the AI to generate code from it. When the generated code can't be simplified (which the AI insists is already optimal), Karpathy can see a cleaner path — the model cannot. The core explanation Karpathy offers centers on RL (reinforcement learning) as the limiting factor: if a task isn't well-represented in either the base training data or the RL fine-tuning data, no amount of prompting or inference-time compute can make the model solve it. In other words, LLMs for coding are fundamentally sophisticated autocomplete, and their blind spots are a function of data distribution, not latent capability waiting to be unlocked.

Bitar also draws out Karpathy's point about hiring. Karpathy observes that most companies are still interviewing engineers using leetcode puzzles while simultaneously claiming to want "agentic engineers." What Karpathy proposes is radically simpler and more practical: take the candidate through a large real-world project (he suggests building a Twitter/X clone), and evaluate them not on trivia recall but on their capacity to write specs that the agent can actually execute. The interviews of tomorrow will be about whether you can one-shot a spec for session management, token handling, rate limiting, and cookie expiration — without needing iterative back-and-forth to discover what you forgot.

Bitar extends this into advice for aspiring agentic engineers: practice writing specs at home. Writing a recommendation engine spec as part of your normal preparation, even if you know it's not on the interview brief, would position you significantly ahead of candidates who don't. The core skill in agentic coding isn't getting Claude to do things — it's not giving it something until it's ready enough to one-shot successfully. Iterative refinement with an agent costs time; precision saves it.

The interview's closing exchange reinforces Bitar's skepticism. When asked what's actually worth learning in the age of AI, Karpathy essentially admits he doesn't know, and Bitar reads that honestly as the real takeaway: even the architect of the modern AI stack is feeling lost. For anyone navigating the current landscape, Bitar suggests taking solace in that fact rather than pretending certainty we don't have.
