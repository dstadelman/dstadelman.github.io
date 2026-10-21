---
layout: "post"
title: "A Year of Local AI on an RTX 5090: Everything I've Tried"
date: 2026-10-21
---

# A Year of Local AI on an RTX 5090: Everything I've Tried

About a year ago I built a GPU workstation and started running AI models at home instead of only renting them by the token. This post is the logbook: what I've run on it, what worked, what didn't, and what I learned. It covers local LLMs, agents, image and video generation, voice and music, and the short-form video experiments that came out of all of it.

## Executive summary

**The machine:** one NVIDIA **RTX 5090 (32 GB VRAM, Blackwell)**, an **AMD Ryzen 9 9900X (12 cores / 24 threads)**, **96 GB of DDR5**, a **2 TB Samsung 9100 PRO PCIe 5.0 NVMe** for models, and a **16 TB hard drive** for bulk data. It runs Ubuntu 25.10 and is set up entirely with Ansible: 28 playbooks, each turning a fresh install into one more service. The 5090 is selling for more today than I paid for it.

**What I've done on it, and know how to do:**

- **Local LLM serving with four engines:** vLLM, Ollama, llama.cpp, and Strata. The biggest one runs a **125B-parameter mixture-of-experts model on a single 32 GB card at 130-190 tokens/second.**
- **Local AI coding that works.** The **Pi coding agent** pointed at Strata's 125B MoE edits code, runs commands, browses and spawns subagents, with nothing sent to the cloud. Local programming is now practical.
- **A self-hosted agent that publishes a blog by itself.** Hermes Agent, running on local models, has written and posted **135+ articles** to this site since May. It handles search, fact-checking and the GitHub commit, and it posted this article too.
- **A podcast-to-article pipeline:** RSS, then WhisperX transcription, then an LLM summary with web fact-checking, then a GitHub Pages post. Everything runs on the one GPU, and the pipeline hands the card between services as it goes.
- **Image generation in ComfyUI** with SDXL (Pony, Illustrious, RealVis), Flux.1, Flux Kontext, Flux.2 Klein, Qwen-Image, Qwen-Image-Edit, Z-Image and Anima, plus upscalers. **Krita** on my desktop uses the workstation's ComfyUI as its AI backend, so I can paint, inpaint and live-paint with the 5090 doing the work.
- **Video generation** with **Wan 2.2** (text-to-video, image-to-video, and VACE for video editing), **LTX-2.3**, and **MiniMax H3**.
- **LoRA training** with AI Toolkit on SDXL and Z-Image Turbo.
- **Voice and audio:** Kokoro and Orpheus TTS, **Chatterbox zero-shot voice cloning**, WhisperX speech-to-text, **ACE-Step** and **MiniMax Music 3** for music, and **Stable Audio Open** for sound effects.
- **Short-form video at scale, measured like an experiment:** programmatic editing with Remotion and FFmpeg, auto-captioning, posting to 7 platforms, and **balanced A/B tests on TikTok**. One finding: my AI voice clone got more views than my real voice.
- **The plumbing around it:** Open WebUI, n8n, Qdrant, Postgres, MinIO, SearXNG, a sandboxed Python REPL, Agent Zero, OmniSVG and Open Design.

The details follow.

---

## The hardware, and why it matters

| Part | Spec |
|---|---|
| GPU | NVIDIA GeForce RTX 5090, 32 GB GDDR7 (Blackwell, sm_120) |
| CPU | AMD Ryzen 9 9900X, 12 cores / 24 threads |
| RAM | 96 GB DDR5 |
| Fast storage | Samsung 9100 PRO 2 TB, PCIe 5.0 NVMe (models, Docker) |
| Bulk storage | 16 TB Seagate HDD (object storage, databases, archives) |
| OS | Ubuntu 25.10, NVIDIA 595 driver, CUDA 13 |

The 32 GB of VRAM is what makes a 5090 special for local AI. It's enough to hold a 30B model with a long context, or a 14B video model at FP8. Just as important is the **96 GB of system RAM**, which is what lets this box run models far bigger than the GPU (see Strata below). Partly offloaded image, video and music models also lean on that RAM.

Being early to Blackwell had a cost. For months, much of the ecosystem didn't support sm_120: stock PyTorch wheels had no kernels for it, and several projects pinned versions of torch that predated the card. A recurring task was rebuilding containers on CUDA 12.8/12.9 or nightly wheels so they would run at all. I also wrote an emergency "driver hang" reboot script for the times the NVIDIA driver wedged. It syncs and remounts disks read-only before rebooting, so nothing gets corrupted.

Everything is **infrastructure as code**. Each service is an Ansible playbook plus a systemd unit and a Docker container, so the whole box can be rebuilt from a blank install.

---

## Local LLMs: vLLM, then Ollama, then Strata

### vLLM (winter 2025-26)

I started with **vLLM** serving **Qwen3-Coder-30B-A3B** (a 4-bit AWQ quant), with tool calling turned on through a custom chat template. I also tried **Qwen3-Omni-30B** and **GLM-4.7-Flash** (GGUF with speculative decoding). A small second vLLM instance served **Snowflake Arctic Embed** embeddings for retrieval into Qdrant.

My main use was **batch summarization and labeling**: pushing a large backlog of documents through the model to summarize and tag each one. vLLM is excellent at this. Continuous batching means **many requests at once** cost little more than one, so throughput across parallel contexts is far beyond a single-stream server.

**The catch:** vLLM reserves a fixed share of VRAM at startup (I ran it at 80-90%) and **keeps it for as long as it runs**. It does not unload when idle. That's right for a dedicated inference server, but on a single-GPU workstation it meant nothing else could use the card. One config comment tells the story: the context window had to shrink whenever the Kokoro TTS service was also running.

### Ollama (spring - fall 2026)

In April I switched the default to **Ollama** and turned every other service off by default. Ollama **loads a model on demand and unloads it after it goes idle** (I used a 10-minute keep-alive, plus a script that forces an unload). That makes the GPU a shared resource: the LLM can answer a question and then hand the card to ComfyUI or a TTS model.

Models over time:
- **Qwen3.6**, then **Qwen3.8 27B** (dense) as the main model
- **Qwen3-VL 8B** for vision
- **Gemma 4** as an alternative

Tuning that paid off: **flash attention, a q8_0 KV cache, and a 256K context**, found with a script that steps the context length up until the model no longer fits fully on the GPU. For agent tool loops I set the reasoning effort to **low**. At higher settings the model overthought every tool call.

**Lesson:** for a multi-purpose workstation, *a model that gets out of the way* is worth more than peak throughput. For a dedicated batch job, vLLM still wins.

### Strata: a 125B MoE on one 5090 (October 2026)

The newest backend is **Strata**, an engine built on llama.cpp for very large mixture-of-experts models. It serves **Qwen3.8-Flash-Next, a 125B-parameter MoE**, at an IQ3_S quant.

The trick is that an MoE only activates a few experts per token. Strata keeps the hot experts in a **GPU cache sized to all 32 GB of VRAM**, the rest of the experts in **system RAM** (about 50-60 GB, which is where the 96 GB matters), and anything left over on the NVMe. On this box it measures:

- **~131 tokens/s** on short chats
- **~188 tokens/s at 56K context**
- **~6,000 tokens/s** prompt processing
- **256K context**
- **Vision:** the vision encoder runs on the **CPU**, so the model can read screenshots without giving up any VRAM. A 1280x900 screenshot round trip takes about 4 seconds, and text speed is unchanged.

A 125B model at those speeds on one consumer GPU is the most impressive thing this machine does. The tradeoff is the reverse of Ollama's: Strata wants the whole card, and it sizes its cache from whatever VRAM is free when it starts. So I wrote a one-command switch, `enable_llm.sh strata|ollama`. It stops one backend, starts the other, and repoints the agent and the chat UI at it.

### Local coding with Pi + Strata

The real test of a local model is whether it can **write code in an agent loop**: read files, make edits, run commands, read the errors, and try again, over hundreds of turns. Smaller local models used to fall apart here. They lost track of the task or emitted broken tool calls after a few steps.

**Pi** (a minimal, extensible terminal coding agent) pointed at Strata changed that for me. My setup:

- Pi's default provider is Strata's **Qwen3.8-Flash-Next 125B** at a **256K context**, with image input on, so it can read screenshots. Ollama's Qwen3.8 27B is configured as a lighter fallback.
- Pi packages add **web search and page reading**, a **Playwright browser** (so it can open the app it just built and look at it), **subagents** for parallel work, and a **plan mode** for thinking a change through before touching code.

At 130-190 tokens/second with fast prompt processing, the loop is quick enough to keep working in. The model is big enough that tool calls stay well-formed and it keeps the plan in its head over a long session.

**Mixture-of-experts is what makes this work at home.** A dense 125B model would need several data-center GPUs. An MoE only runs a few experts per token, so one 5090 plus 96 GB of RAM can serve it at interactive speed. **Fully local programming is possible now:** private code, no per-token bill, no rate limits, and it still works when the internet is down. Hermes uses the same "Pi approach" for keyless web search.

---

## Hermes Agent and the self-publishing blog

**Hermes Agent** (from Nous Research) is the "brain" that uses these models. It runs on the workstation with:
- a real headless browser (Camofox)
- web search through Exa, with self-hosted SearXNG as a fallback
- a skills system, including a `post-to-github` skill that commits Markdown posts to this site through the GitHub API

The flagship workflow is the **AI Daily Brief pipeline**, which produced most of the posts on this blog:

1. Read the podcast RSS feed and work out which episodes don't have a post yet.
2. Download the audio. Over SSH, **stop whatever is using the GPU**, start **WhisperX** (large-v3-turbo), transcribe, then stop WhisperX again.
3. Restart the LLM backend (now Strata) and wait until it answers.
4. Send the transcript to Hermes. Hermes writes the article, **fact-checks names and claims on the web** (speech-to-text mangles proper nouns), and publishes it to GitHub Pages.
5. Put the GPU back the way it found it.

**135+ posts since May 18.** Most of the engineering went into the unglamorous parts:
- **GPU handoffs** between services
- **catch-up logic** that works per episode, so two episodes on the same day don't hide each other
- **SSH tunnels that don't hang** the script
- making sure the agent's **background "self-review" doesn't hold the GPU** after the job finishes

**Also on the box:** Open WebUI as a ChatGPT-style front end for all of it, n8n for automations, Agent Zero (an earlier agent framework I tried), a sandboxed Python REPL, Qdrant, Postgres and MinIO for data, OmniSVG for generating SVGs, and Open Design.

---

## Image generation: ComfyUI and Krita

**ComfyUI** is the hub for image and video work. Model families I've used:

- **SDXL and its descendants:** base SDXL, RealVisXL, Pony Diffusion, Illustrious and NoobAI, with dozens of style LoRAs
- **Flux.1 dev**, **Flux.1 Kontext** (instruction-based editing) and **Flux.2 Klein** (4B/9B)
- **Qwen-Image** and **Qwen-Image-Edit 2511**, with Lightning 4-step LoRAs for speed and pose-control LoRAs
- **Z-Image / Z-Image Turbo** and **Anima**
- **Upscalers:** UltraSharp, HAT, OmniSR and Real-ESRGAN

**Techniques I'm comfortable with now:**
- **Consistent characters and settings with edit models.** Instead of generating every frame from scratch, I generate **one base photo** of a place and make every other shot an **edit** of it with Qwen-Image-Edit. Change the pose, add a prop, clear the table. Layout, lighting and characters stay consistent across a whole story.
- **Character sheets** as reference input for video models.
- **LoRA training** with **AI Toolkit**, on SDXL/Illustrious checkpoints (mounted straight from the ComfyUI model folder) and on Z-Image Turbo.

### The ComfyUI + Krita setup

The image pipeline is split between two machines:

- **On the workstation:** ComfyUI runs as a LAN server, with the GPU power-limited to 500 W for long sessions. It has the custom nodes the Krita plugin needs (tooling nodes, inpaint nodes, IP-Adapter, ControlNet preprocessors), plus GGUF loaders, LTX-Video, the Impact Pack, frame interpolation, the SeedVR2 video upscaler, Ultimate SD Upscale and the video helper suite.
- **On my desktop:** **Krita** with the **Krita AI Diffusion** plugin (v1.53), connected to that ComfyUI server as a custom backend.

This turns Krita into an AI painting studio, while it stays a normal painting app:

- **Generate** an image from a prompt straight onto the canvas.
- **Select a region and inpaint it**, to fix a hand, swap an object or extend a background.
- **Live painting:** rough strokes become a finished image in near real time as I draw.
- **Control layers:** use a sketch, line art, depth or pose as guidance, or a reference image through IP-Adapter for style and likeness.
- **Upscale and refine** in place.

All the models live on the workstation, so the desktop needs no special GPU. ComfyUI itself stays available for the node-graph workflows (video, edit chains, batch jobs) that a painting app isn't built for.

---

## Video generation

- **Wan 2.2 (14B)**, text-to-video and image-to-video, in FP8 and FP16, using the high-noise/low-noise expert pair.
- **Wan 2.2 VACE-Fun (A14B, Q8 GGUF)** for **video editing**, not just generation. My best trick with it is **screen replacement**. Video models can't draw a real app on a phone or tablet screen, so:
  1. Generate the scene with the screen dark.
  2. Track the screen through every frame with optical flow (it survives hands passing over it).
  3. Mask the screen gray, and paste the real screenshot onto a few keyframes.
  4. Let VACE fill in the rest so it looks filmed, not pasted.

  A 141-frame clip takes about 90 seconds on the 5090.
- **LTX-2.3 (22B)**, dev and distilled, for fast text/image-to-video.
- **MiniMax H3**, an open-weights video model that generates **video with synchronized audio**, run locally in ComfyUI. I set it up with **Claude as the "prompt compiler"**. Claude turns a shot list into structured H3 prompts and checks each still's blocking before spending GPU time on takes. I batch several shots' takes into one job.

A practical lesson: **one GPU means traffic control.** A small "GPU guard" frees ComfyUI's VRAM before a big video job and refuses to start if something else is holding the card.

---

## Voice, speech and music

- **Kokoro TTS:** fast, lightweight and good quality.
- **Orpheus TTS:** a 3B model on llama.cpp, more expressive, and it supports emotion tags like laughs and sighs.
- **Chatterbox (Resemble AI):** **zero-shot voice cloning from a 10-20 second clip**, with no training. I cloned **my own voice** to narrate videos without recording every take. Its output carries an inaudible watermark, and I label anything that uses it as AI-generated.
- **WhisperX:** speech-to-text with word-level timestamps. It drives both the podcast pipeline and the burned-in captions on every video.
- **ACE-Step 1.5 XL:** text-to-music, with CPU offload so it fits beside other work. I built a small pipeline that generates candidate tracks, keeps the good ones in a library, and mixes them under a video at several volume levels for review.
- **MiniMax Music 3:** another local music model, inside ComfyUI.
- **Stable Audio Open:** sound effects, served through a vLLM-Omni wrapper. Getting it running meant pinning vllm-omni to a version that matched vLLM, because the current main branch broke.

Every one of these is installed **disabled** and starts only when a job needs it. With this many models wanting the same 32 GB, that rule is what keeps the box usable.

---

## Short-form video, run like an experiment

All of the above feeds a short-form video pipeline that I run for a side project:

- **Remotion** (React-based video) and **FFmpeg** build videos from a script, voice-over, screen recordings and AI b-roll.
- A **caption tool** transcribes with WhisperX, **cuts dead air**, and burns in captions. There's a review step so misheard words get fixed first, and when there's a script, the captions are spelled from it.
- Videos go to **7 platforms** (TikTok, YouTube Shorts, Instagram, Facebook, X, Threads, Pinterest) through an upload API.
- Stats come out of **TikTok Studio** with a Playwright script, so retention curves become data rather than screenshots.

**The study.** I pulled retention curves for **160 TikToks** and looked for what predicts reach. Findings:
- TikTok produced **82% of all interactions** across the 7 platforms.
- Views track **completion rate** and **10-second hold** much more than the first second.
- Videos **under 20 seconds** finished about 6x more often than videos over 60 seconds.
- **Opening on the viewer's problem** beat opening on the product or brand (56% vs 43% still watching at 3 seconds).
- Reposted or recut clips never broke out. Paid boosting mostly bought bot traffic.

**Round 1: a balanced test.** That became a playbook, and then a **24-video test** where three factors were balanced against each other (**voice:** me vs. my AI clone; **topic** type; **ending:** a question vs. a payoff line). Two videos a day, decision rules written down before looking at any numbers. Results:
- **20 of 24 videos passed 200 views**, against 12 of 90 before the playbook.
- **My AI voice clone beat my real voice:** median **386 vs 256 views** and **6.6% vs 4.0% completion**.
- Ending on a question **did not** increase comments.
- Story and "real moment" topics beat explainers.

**Round 2** is running now. It's a **format** test, with the same stories told four ways: a first-person story, a POV moment with no narration, a third-person narrated story, and a quick skit.

What I like about this project is that every part of it, from b-roll, voice, music and captions to the analysis, runs on hardware in my house, and each decision comes from a test rather than a hunch.

---

## What I'd tell someone starting out

1. **VRAM is the budget for everything.** Pick tools by how they share it. vLLM is for dedicated throughput. Ollama is for a shared box. A RAM-offloading MoE engine like Strata is for running far above your weight class.
2. **System RAM matters more than people think.** 96 GB is what makes a 125B model and CPU-offloaded music and video models practical on one card.
3. **Default everything to off.** Start services on demand, and write the handoff scripts.
4. **Put it in code.** Ansible plus systemd plus Docker meant I could try (and drop) two dozen services without the box rotting.
5. **Close the loop.** The models are the easy part. The interesting work is in pipelines that do something end to end: transcribe, write, fact-check, publish, measure.
6. **Measure what you make.** A balanced test with rules set in advance taught me more in two weeks than months of posting by gut feel.

A year in, this one box is a coding partner, a writing assistant, an autonomous blogger, a photo studio, a video studio, a voice actor, a composer and an analytics lab, all without sending a token to the cloud.

*This post was published by Hermes Agent, running on the machine it describes.*