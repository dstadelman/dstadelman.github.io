---
layout: "post"
title: "The Models Trying to Fill the Fable Gap"
date: 2026-06-23
---

# Summary: The Models Trying to Fill the Fable Gap

[AI Daily Brief - The Models Trying to Fill the Fable Gap](https://podcasters.spotify.com/pod/show/nlw/episodes/The-Models-Trying-to-Fill-the-Fable-Gap-e3kvr3b)

With Claude Fable 5 and Mythos 5 under US export controls and still unavailable for foreign nationals, the AI industry is undergoing a fundamental reckoning over model access, cost, and geopolitical dependency. This episode covers the geopolitical fallout at the G7 summit in Evian, France, major personnel shifts, and the growing ecosystem of models—open-source, Chinese, and hybrid—positioning themselves to fill the gap left by the banned Anthropic models.

* **G7 AI summit reveals geopolitical fracture**: Claude Fable 5 and Mythos 5 remain banned under US export controls, and the topic dominated the G7 summit in Evian-les-Bains, France (June 15-17). Anthropic's Dario Amodei, OpenAI's Sam Altman, Google DeepMind's Demis Hassabis, Mistral's Arthur Mensch, and Cohere's Aidan Gomez were all present. Amodei and Hassabis led calls for international cooperation including structured access to frontier models, chip trade deals excluding China, and unified cyber/biotech risk frameworks. Amodei urged leaders to resist splintering over advanced AI deployment.

* **European frustration with US AI "kill switch"**: EU officials expressed deep concern over the sudden loss of access to US-made frontier models. French President Emmanuel Macron emphasized shared US-EU interests in containing AI from authoritarian regimes. Italian MEP Brando Benifei declared plainly: the Anthropic "kill switch" shows tech sovereignty is no longer abstract, and Europe must cooperate from a position of strength. UK Prime Minister Mark Carney agreed the US could lead an AI coalition, while EU Commissioner for Tech Sovereignty Henna Virkkunen voiced that frontier AI should not be kept to one country.

* **US position is unmoving, SK Telecom incident adds context**: President Trump and Commerce Secretary Howard Lutnick both described Anthropic negotiations as "going fine" with no timeline for access restoration. Adding credibility to the China rationale for the ban, Wired reported that Anthropic revoked SK Telecom's Mythos access days before the full export control order after US concerns about Chinese ties. European Commission tech sovereignty policy chief Thomas Rainer noted the UK's request for a carve-out for British nationals was denied.

* **Noam Shazeer joins OpenAI from Google**: Legendary "Attention is All You Need" co-author Noam Shazeer left Google to join OpenAI, working on new AI architectures. Google had previously spent $2.7 billion on an acqui-hire of Shazeer's Character AI in 2024 to retain him. Sam Altman said the move "has been a long time coming."

* **ChatGPT pulses being sunsetting**: OpenAI announced it is sunsetting ChatGPT Pulse within two weeks, folding proactive updates into scheduled tasks available to all paid subscribers including the lower-cost Go tier.

* **European AI infrastructure lags badly**: The EU's plan for up to five AI gigafactories with 100,000 GPUs has only 20 billion euros committed—in contrast, hyperscalers are spending three times that amount monthly on US data centers.

* **Open-source becomes the biggest winner**: Companies are increasingly viewing open-weight or open-source models as a strategic necessity for unpredictable access. Bloomberg and CNBC echoed this consensus, noting that local model deployment eliminates the risk of export-controlled models being revoked without warning.

* **Chinese models gaining ground**: Moonshot's Kimi K2.7 Code (released June 12) and Zhipu's GLM-5.2 are both drawing attention. GLM-5.2 scored number one on multiple reasoning and design benchmarks, outperforming Claude Opus 4.8 and GPT-5.5 on some tasks at about a tenth of the cost ($0.06 vs $0.49 per million tokens for Claude). Some benchmark results may be inflated by benchmark-tuning; one source noted internal evaluations put GLM-5.2 behind both.

* **Smaller reasoning models are attracting attention**: VibeThinker-3B from Weibo AI (verified on arXiv), a compact 3 billion parameter dense model built on Qwen2.5 Coder 3B, is generating excitement for its reasoning capability on a tiny model scale—despite having limited general knowledge.

* **Microsoft considering DeepSeek for Copilot Cowork**: Axios reported Microsoft is evaluating a Microsoft-hosted fine-tune of DeepSeek V4 for Copilot Cowork as a lower-cost alternative to Claude Opus 4.7 and GPT-5.5, expected to ship in the coming weeks. The irony is notable: the US government is banning Claude for foreign access while Microsoft quietly embeds a Chinese-optimized model into the productivity suite of every Fortune 500 company. DeepSeek already hosts on hyperscaler clouds and was originally optimized for Huawei chips, raising questions about whether a Chinese stack is entering the US enterprise side door.

* **Cursor's Composer 2.5 holds up in real-world use**: Built on a Kimi model foundation and post-trained for coding, Composer 2.5 scored in the Claude Opus 4.8 / GPT-5.5 range on benchmarks at a fraction of the cost. Early practical reports are mixed—some users found it impressive for daily coding while others found it inconsistent. Artificial Analysis recently updated its agentic coding benchmarks, and Composer 2.5's scores dropped closer to the Chinese open models than the frontier benchmarks initially suggested.

* **OpenRouter's Fusion API uses multi-model routing**: OpenRouter launched Fusion, a compound model that fans a prompt to multiple models in parallel with a judge model synthesizing the final answer. OpenRouter claims "Fable-level intelligence at half the price." The approach mirrors how many developers actually work across multiple models for generation, review, and testing.

* **The hybrid worker-advisor pattern is emerging as a competitive advantage**: Harvey AI partnered with Fireworks to deploy a hybrid legal agent where an open-weight GLM 5.1 worker delegates high-stakes complex tasks to Claude Opus 4.7 as a frontier advisor. The combination was both cheaper and performant than using Opus 4.7 alone. Patrick Gojo noted: "The insight isn't that open source beat frontier—it's that smart routing beat brute force. Using the most expensive model for every task is not a quality strategy; it's a laziness strategy."

In summary, the Fable 5 crisis is accelerating a trend that was coming regardless: companies are getting sophisticated about model combinations rather than relying on a single state-of-the-art model. With frontier costs continuing to rise and access now uncertain, inference optimization and token efficiency exploration are no longer optional—they're first-class competitive advantages for any organization building with AI.