---
layout: "post"
title: "Summary: OpenAI founder admits AI isn't working"
date: 2026-05-19
---

[Mo Bitar - OpenAI founder admits AI isn't working](https://www.youtube.com/watch?v=ZugX7a99dLk)

Mo Bitar analyzes Andre Karpathy's recent interview remarks about the current state of AI coding tools, where Karpathy's own words expose a deep contradiction: he claims to have stopped checking AI-generated code because the models have improved, yet admits he gets a medical-level heart attack every time he reviews the output. The video dissects Karpathy's description of his workflow -- writing exhaustive markdown specs for the AI to follow -- and his frustration that the model can refactor 100,000-line codebases but still chokes on counting Rs in "strawberry" or catching simple bugs in his own projects.

* *The code quality heart attack*: Karpathy describes his generated code as "bloaty" with "a lot of copypaste" and "awkward abstractions that are brittle." For an OpenAI co-founder, this represents the frontier of what these models can actually deliver -- the kind of honesty that engineers on the payroll won't share publicly.
* *Spec writing is the new interviewing skill*: Karpathy suggests the real test for hiring AI-era engineers shouldn't be leak coding puzzles but the ability to write specs precise enough that an AI agent can execute them on the first pass without back-and-forth corrections. A practice Twitter clone spec should cover tokens, sessions, rate limiting, cookie expiration, and password flows.
* *The limitation is fundamental, not technical*: Karpathy attributes these failures to RL -- if a task isn't well-represented in the model's training or reinforcement learning data, "there's no force on this planet" that can make it solve the problem. This reframes AI coding tools as extremely sophisticated autocomplete rather than autonomous agents.
* *Nobody even knows what to learn*: When asked what skills are still valuable as AI improves, Karpathy essentially couldn't answer. The video concludes this might bring solace to job seekers feeling lost -- even the people who built this technology don't have answers either.

The video highlights a tension that Karpathy himself seems unable to resolve: he identifies as an AI accelerationist eager to promote agentic coding, yet his own honest descriptions of using AI tools reveal a process that's more error-prone and labor-intensive than most proponents admit. The real skill in AI-assisted development right now isn't prompting -- it's precision writing under pressure when there's no time for iteration.