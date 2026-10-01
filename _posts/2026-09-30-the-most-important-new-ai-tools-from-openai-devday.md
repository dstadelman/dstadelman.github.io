---
layout: "post"
title: "The Most Important New AI Tools from OpenAI DevDay"
date: 2026-09-30
---

# Summary: The Most Important New AI Tools from OpenAI DevDay

[The AI Daily Brief - The Most Important New AI Tools from OpenAI DevDay](https://podcasters.spotify.com/pod/show/nlw/episodes/The-Most-Important-New-AI-Tools-from-OpenAI-DevDay-e3pl7uv)

On The AI Daily Brief, host Nathaniel Whittemore breaks down the headlines from OpenAI's DevDay, held September 29 in San Francisco, where the company said its flagship GPT-6 Astra model had accelerated internal development so much that capabilities it had slated for 2027 instead shipped that day. Across more than 20 announcements, the throughline is not a new direction but a confirmed one: cheaper, general-purpose models; persistent always-on agents; and a move from single-player to team-mode AI. Whittemore walks through each major launch, who is reacting and how, and what the day says about the next phase of AI in general.

* **Astra pulled the 2027 roadmap into 2026:** OpenAI says the newest generation of models, led by its flagship GPT-6 Astra, increased the speed of its internal development enough that work planned for next year arrived at DevDay -- more than 20 distinct launches and announcements in a single day, the company's biggest ever.

* **Dots is the answer to Meta's Muse and xAI's Grokbot:** Sam Altman pitched them as "remarkably capable, always-on agents" that "bring AI to a whole new form factor." Each dot gets its own cloud computer and browser, works through a text-message-style interface, takes voice calls, and moves across Slack and Microsoft Teams with context carried between sessions -- and can act on more than 4,000 apps through OpenAI's plugin ecosystem (the audio said 40,000; OpenAI's own materials and reporting put it above 4,000).

* **Dots ships paid-only, one at a time:** Unlike Meta's free tier, dots are limited to Pro, Business, and Enterprise customers and only one dot per user right now, with team agents planned. CFO Sarah Friar said the long-term vision is the whole consumer base, and Altman framed it as a premium product that "uses a lot of compute" -- the first time a truly frontier model pilots a first-party personal agent, running on GPT-6 Astra.

* **Early verdict: flashes of brilliance, real bugs:** Early adopters reported lost work sessions and no way to connect multiple computers for full context, while others said dots nailed an autonomous expense task that Grokbot botched. The newsletter Every landed at "tbd" -- truly excellent at moments, extremely frustrating at others -- and one early user argued dots are less a personal assistant and more a "codex orchestrator and slack collaborator."

* **GPT-6.1 Sol: near-Astra intelligence for a fifth of the price:** The day's big model launch matches GPT-6 Astra on several benchmarks at roughly 13% of Astra's cost per task (about a third of GPT-6 Sol). Its top DeepSWE score was 75.2% at the high setting, edging Astra's best, and OSWorld (long-horizon computer use) hit 71.4% at max, ahead of GPT-6 Sol's 64.4% and close to Astra's 73.5% -- while extra-high and max settings actually degraded performance, the same overthinking effect first seen with Claude Opus 5.

* **Artificial Analysis puts it fifth, but cheap:** The firm's Intelligence Index scores GPT-6.1 Sol (max) at 52, a point below Astra and behind Opus, Sonnet, and one other frontier model, while praising cost efficiency that pushes the price-performance frontier. Impressions on X split between "this makes Opus look expensive" and "it barely rendered my test," so first-hand judgment is still pending.

* **The Decisions API is OpenAI's answer to Jev:** Jev, from TypeSafe AI, is not a text generator -- it is a judgment and classification model that returns confidence scores from 0 to 1 rather than prose, and it went viral because so many real "use cases" (routing, triage, judging) are exactly what traditional LLMs do poorly. OpenAI's Decisions API calls a version of GPT-6 Luna to classify inputs, route requests, or choose an agent's next action from a fixed set of answers, claims 10x faster decisions than its Responses API, and -- unlike Jev -- accepts visual input.

* **A new primitive, not just a new model:** Whittemore's read is that the Decisions API marks a recognition that judgment models are becoming a fundamental primitive that sits alongside generative models, and that nearly every frontier lab will ship some version in the very near future.

* **OpenAI Space is the multiplayer workspace:** A Google Drive / Notion / Microsoft 365 rival that gives human teams and agents a shared home for spreadsheets, slide decks, and other documents, plus scheduled workplace automations that deposit deliverables into the space; dots can work natively on documents and even be tagged inside a comment. Power users were in love immediately -- one called dots slightly overhyped and Space underhyped, and Every's founder Dan Shipper described tagging his dot in a document comment and getting an in-line revision, "more like collaboration."

* **The app-store swing, again:** Plugin extensions let outside developers build full native apps into ChatGPT's sidebar, panels, and file viewers, surfaced to OpenAI's 1.2 billion weekly users, and Sign in with ChatGPT extends that by letting users log into 16 partner apps (including Devin, Notion, and Vercel) and spend their existing plan allowance there. It is OpenAI's third or fourth swing at becoming the platform and distribution layer of AI.

* **The smaller, still-significant launches:** an Ultrafast speed tier (8x faster token generation in Codex, 6x in the app); a $500 "Pro 500" tier with 25x the usage of Plus and the only current access to Ultrafast; the reopened $200 Pro tier with usage cut roughly in half; Codex in a dedicated cloud environment plus a refreshed CLI for managing parallel work; Private Intelligence (zero data retention, including at inference); and a marketplace to buy open-weight model inference via Baseten through OpenAI's Responses API in Codex.

* **The catch -- they shelved GPT-6.1 Astra:** Per the Wall Street Journal, OpenAI decided not to release its next flagship over safety concerns. Saachi Jain, OpenAI's head of safety systems, said the model was less lazy than its predecessors but did not meet the bar on staying within scope and authorization, a sign the company needs further technical breakthroughs before the next frontier step feels safe to ship.

* **The subtext is compute:** Whittemore reads the $200 tier's reduced value as an admission that compute constraints are "real, present, and permanent" -- usage is outrunning the arrival of new compute -- which forces the industry's current efficiency push and, in the long run, should net out to cheaper and better experiences for everyone.

* **What DevDay actually tells us:** cheaper and more capable general-purpose models that can just do everything (Sol 6.1 and the Decisions API); persistent, proactive agents that capitalize on that to actually do the work (Dots); an open platform that brings everything in and goes everywhere (plugin extensions and Sign in with ChatGPT); and native multiplayer collaboration (Space).

The takeaway, as Whittemore puts it, is that DevDay didn't hand the industry anything blisteringly new -- it confirmed the trends this show has been cataloging for months. Models are becoming good enough and cheap enough that you no longer have to switch them on and off for each task, persistent agents are turning that "good enough" into work that genuinely gets done, the platforms are opening up to ship to everyone and everywhere, and the center of gravity is shifting from a single user's chatbot to a team's shared workspace. Those are the four patterns that will reshape how all of us use AI over the months that come.
