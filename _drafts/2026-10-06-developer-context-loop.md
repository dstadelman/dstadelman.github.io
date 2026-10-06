---
layout: "post"
title: "Developer Context Loop"
date: 2026-10-06
---

Product specification for an internal system that turns coding-agent chat logs into governed, searchable context, then writes that learning back as a skill the next session can load.

**Status:** Draft, aligned to the 4-minute demo and the published project  
**Audience:** Platform engineering, data engineering, developer experience, security  
**Demo:** Alex Noonan ([@AlexNoonan6](https://x.com/AlexNoonan6)), dbt Labs, 5 Oct 2026  
**Post:** https://x.com/AlexNoonan6/status/2107122714070929894  
**Reference implementation:** https://github.com/C00ldudeNoonan/dbt-chat-context-eng (`main` at `378890872`)  
**Package:** [`dbt-labs/dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering) 0.1.0, locked in that repo  
**Warehouse:** Snowflake Cortex. dbt 2.0 or newer (the standalone `dbt` binary).

The reference repo is one person's working loop. This document specifies that loop as a product for developers in a large organization. Where the repo and the talk differ from what an organization needs, the gap is called out as a product requirement, not described as if the repo already does it.

---

## 1. What it does

It saves the useful parts of engineering chat sessions, and lets a later session look them up.

A developer runs a coding agent and gets a trail of messages: what they tried, the error, and what finally worked. Those logs stay on the laptop. This product reads the logs they opted in, strips obvious secrets on the machine, and loads the messages into a database.

A pipeline then breaks each conversation into short passages, labels each passage with a topic such as coding, data, or planning, and stores a numeric vector for each passage so similar text can be found. It also writes a short record per conversation: the problem, whether it was solved, what worked, and a quote taken from the transcript.

Later, an engineer or their agent asks something like "why did this incremental model duplicate rows?" The question is turned into a vector, the closest passages come back with a link to the original conversation, and the agent reads those passages and answers. It does not receive the whole history.

If a result is worth keeping, the agent writes a `SKILL.md` file from it. A person reviews that file in git. The next session can load the skill directly, or search again.

During development it only processes a small sample of conversations, and it records every model call so the spend is visible. The first version is one person's own sessions. A shared version is one team's sessions, not a search box over the whole company.

## 2. Value proposition

Coding agents are already being asked to change large, old, business-critical systems. The knowledge of how those systems actually break still lives in old chats and in people who may leave. This product turns that history into cited, searchable context the next engineer and the next agent can use, without pasting transcripts or sensitive data into a prompt.

An agent on that work fails in a predictable way. It does not know that this batch job duplicates rows when the incremental filter is wrong, that this incident was a config drift, or that this migration was tried last quarter and rolled back. That text exists. It is in Claude and Codex sessions, ticket notes, and runbooks. It is not modeled, so every new session starts cold and every departing engineer takes the lesson with them.

For a director, the pitch is four outcomes:

- **Agents stop repeating known failures.** The first search is "what did we try last time on this job, and what fixed it?"
- **Onboarding gets shorter.** A new engineer retrieves the last incident instead of waiting for the one person who remembers it.
- **Model spend stays inside a cap.** Development runs on a sample. Embeddings refresh only when the text or the model changes. Every model call is logged.
- **Security can sign it.** Redaction happens before upload. Team partitions keep one group from reading another's sessions. There is no third-party transcript API. Restricted rows never become an org-wide skill. That is the difference between this and dumping chats into a vector database.

The people it helps first are platform and application teams who already have coding agents and a trail of production incidents. Pick one team whose logs are mostly build failures, SQL, and deploy notes, not customer records. Two weeks of opted-in sessions, one eval question set, one merged skill.

What can be shown before anyone bets headcount on it: a search that opens the right session, a topic filter that drops "thanks, that worked," a run that refuses an over-budget batch, and one skill a later session loads without anyone pasting the lesson into the prompt.

What not to claim: a company-wide knowledge base, a replacement for the wiki, or automatic learning from every engineer's chats. The first shared version is one team's memory, governed like a data product. It is data engineering pointed at the agent, not a new AI platform.

## 3. Local first, then the organization

The first version is a personal loop on one machine, using that person's own chat logs. Nobody else can see it.

Point the ingest script at Claude Code or Codex sessions, preview the rows, and load a small sample. Chunking, embedding, and topic labels run locally with the models in section 4. The results sit in a local database such as DuckDB. Search that history, check whether the right conversation comes back, and have the agent write a `SKILL.md` from a hit. If the answer is useful the next week, the demo worked.

Scaling that to a large organization is the same pipeline with a shared warehouse, a partition per team, redaction that security will sign, and a human review before any skill is shared. That shared shape is not required to find out whether the search is any good. Prove it on one person's logs first.

A local demo can be entirely open source. Use dbt OSS, DuckDB or Postgres with pgvector, and the models below. The published demo uses Snowflake Cortex and can be driven from Wizard Desktop. Those two are not open source. They are optional once the local models and a local database are in place. The MIT ingest script, the dbt models, the prompts, and the Apache `dbt_context_engineering` package stay either way.

## 4. Open-source models

These are free weights loaded in local Python. No API key and no warehouse AI call. `sentence-transformers` (Apache 2.0) loads the embedding models. `transformers` loads the zero-shot classifier.

### Embedding

Use one embedding model for the corpus and for the question. Normalize the vectors and rank by cosine similarity.

| Model | License | Size | When to use it |
| --- | --- | --- | --- |
| `sentence-transformers/all-MiniLM-L6-v2` | Apache 2.0 | 23M parameters, 384 dimensions, about 256 word pieces | First bake-off. Small enough for a laptop. A 256-token chunk can get cut off. |
| `BAAI/bge-small-en-v1.5` | MIT | 33M parameters, 384 dimensions | The better small search model. Prefix a query with `Represent this sentence for searching relevant passages:`. |
| `nomic-ai/nomic-embed-text-v1.5` | Apache 2.0 | 137M parameters, 768 dimensions, 8192 tokens | Long sessions on a modest machine. Prefix documents and queries the way the model card says. Dimensions can be truncated. |
| `BAAI/bge-m3` | MIT | 568M parameters, 1024 dimensions, 8192 tokens | Messy session logs, when the small models miss the right conversation. |
| `Snowflake/snowflake-arctic-embed-l-v2.0` | Apache 2.0 | 568M parameters, 1024 dimensions, 8192 tokens | The same family the Cortex demo calls. Download the weights and run them locally. |

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vectors = model.encode(chunks, normalize_embeddings=True)
```

Swap the model name to any row in the table. Start with MiniLM. Move to `bge-m3` or Arctic L v2 only if the eval says the small vectors miss the expected conversation. A corpus whose text is uniform can stay on `bge-small-en-v1.5` or MiniLM.

### Classification

The six topics do not need a chat model. Score each chunk against the six label descriptions with the same embedding model, and take the closest label. One license, one download.

```python
labels = {
    "coding_and_debugging": "writing, reviewing, or fixing application code, scripts, tooling, or errors",
    "data_and_analytics": "SQL, dbt, data modeling, pipelines, warehouses, metrics, or analysis",
    "writing_and_communication": "drafting or editing emails, docs, posts, messaging, or copy",
    "planning_and_strategy": "plans, briefs, campaigns, roadmaps, decisions, or prioritization",
    "learning_and_explanation": "asking how a concept works, with no specific artifact being built",
    "chit_chat_or_other": "greetings, acknowledgements, personal topics, or anything else",
}
```

A separate zero-shot classifier is available if label prototypes are too coarse. `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` loads in `transformers`. The model card says MIT. One dataset it was trained on, ANLI, is CC BY-NC, so do not treat commercial use as settled. The embedding-against-labels method avoids that.

```python
from transformers import pipeline

classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
)
classifier(chunk_text, list(labels), multi_label=False)
```

### Summaries

Problem, outcome, solution, and the evidence quote can be extracted by an Apache-2.0 chat model served locally with vLLM or Ollama, instead of Claude Sonnet through Cortex. Two that meet that bar:

| Model | License | Role |
| --- | --- | --- |
| `Qwen/Qwen2.5-Instruct` | Apache 2.0 | Local extract and summary. Use a size the machine can hold. The grounded test still checks that the evidence quote appears in the source text. |
| `allenai/OLMo` | Apache 2.0 | The same job, from the Allen Institute for AI. Pick a current OLMo instruct checkpoint and keep the same JSON contract. |

Llama and Gemma are free to download and are not OSI-approved licenses. They are out of this list on purpose. The demo's Cortex default, Claude Sonnet 4.5, is a commercial API and is not required once a local instruct model fills the same schema.

---

## 5. Transcript

Spoken track of the full demo, about four minutes. Chapter titles are the video's. A few caption spellings are corrected in the reading text: "colloccating" is colocating, "clawed and codeex" is Claude and Codex, "skill MD" is `SKILL.md`, "rebeds" is re-embeds, and "DBT" is dbt. DAG means directed acyclic graph.

### Analytics engineering → context engineering

**0:00.** Are you ready to level up from analytics engineering into context engineering? When we're talking about context, ultimately what we're talking about is text data.

### Just-in-time vs. just-in-case context

**0:06.** I like to separate into two categories. So just in time context, which are like your skills, your MCP and other context that persists over time across sessions, and just in case context, and that's surfaced through your tools that can be connected to the internet or access internal knowledge stores or other large amounts of non-tabular data.

### Warehouse AI functions and classic search techniques

**0:26.** Many modern warehouses support AI functions and search techniques that allow you to process this data, increase access, and decrease costs from interacting with it. Additionally, we can borrow many techniques from classic machine learning like keyword search, ranking methods, and text tokenization and processing. And these techniques have been in production environments for years. So they're battle tested.

### The pipeline shape: extract, transform, chunk, embed, search

**0:48.** And the process involved in contextualizing unstructured data is deceptively simple with a repetitive shape across different sources. So you have extraction, transformation, chunking, embedding, and then finally search, which is that familiar DAG pattern we are used to.

### The dbt context engineering package

**1:04.** We built a package that makes these pipelines feel the same as any dbt project. Steps broken out into DAGs using SQL syntax, your existing profiles and environments, and colocating with your tabular transformations. So agents interacting with your dbt project now have a greater scope and understanding of your organization.

### Demo: chat transcripts → Snowflake

**1:23.** So what we're going to do here is I have a bunch of Claude and Codex transcripts on my computer. I want to feed them into Snowflake so I can leverage them later and I also want to be able to create a skill to improve and learn from all the chat interactions we had with Claude and Codex. So we're going to do some context engineering to help some of our context that we use in those sessions. It'll be a full working loop demo going from end to end on the entire context engineering process and additionally the code will be on GitHub if you want to check it out for yourself.

### Wizard Desktop setup

**1:55.** So here I am in Wizard Desktop. It's currently in beta and if you want to join the waitlist check out the link in the description. So I'm going to go and the first thing I'm going to do is initialize a new dbt project in the folder that we're in. And then I have a script here that uploads my chat transcripts into Snowflake. And we can investigate and see what these transcripts look like in this table to see what we're working with.

### Summarizing sessions with AI

**2:16.** Then we're going to use some AI to do some transformations to summarize the work that was done, any problems we ran into, and any successes or solutions that we had. And we can also chunk the originals into smaller portions so we can better embed and insert these text fragments.

### Parallel pipelines: testing chunk sizes

**2:31.** I want to be able to experiment and iterate these. So let's make a few parallel pipelines where we test different chunk sizes to see what a difference it makes when we search them.

### How embeddings and search work

**2:39.** And the next step is embedding the chunked data. So an embedding model turns each chunk into a list of numbers that captures its meaning. So similar text will land closely together and also by the relationships. And when I ask a question that also gets embedded in the same way and we grab the closest chunks and only then does the LLM read them and write the answer. Now the text we're working with is session logs. So they're kind of all over the place. So I'm going to try a larger model so I can get more dimensionality embedded in here. And switching is just one variable and dbt re-embeds everything under the same spending cap. And if this was a more structured output that is the same everywhere, I would want to use a smaller embedding model.

### Eval searches

**3:20.** Finally, we have some eval searches here that we can build and then test them out with our unstructured data.

### Writing a SKILL.md from the results

**3:26.** And now that we have our results, I'm going to have Wizard write a `SKILL.md` from the search that we found.

### Principles: sample, iterate, use your existing tools

**3:31.** Now, this video didn't go into a ton of depth, but some general principles to remember when you're doing context engineering. Keep cost low during development by sampling and not running the entire corpus. And don't worry about getting it perfect first. Evaluate and iterate is the name of the game. Also, leverage your existing tooling and processes when you can. So here we used our existing dbt connections, dbt ergonomics, Snowflake and we also used git.

### Try the package

**3:57.** So check out the context engineering package today and we are currently building and refining it. So we welcome any issues or pull requests and make sure you like and subscribe so you don't miss any updates from dbt. Thank you.

### What the short cut showed on screen

The 52-second cut of the same talk uses three columns where the narration uses two. Just in time is "fetched when the task needs it" (skills, MCP tools, web search). Persistent is "carried across sessions" (memories, `AGENTS.md` / rules, project conventions). Just in case is "prepared ahead, searched later" (chat transcripts, tickets and notes, docs and contracts). All three feed a limited context window, and what goes in has to earn its place. The orange box is just in case. That is the path this product builds. The skill it writes is just-in-time context for the next session.

The same cut draws one shape for chat logs, tickets, and docs: Extract (`stg_models`) → Chunk (`chunk()`) → Classify (`classify()`, optional) → Embed (`embed()`) → Search (`vector_search()`). Extract and chunk are plain SQL. Embed and search are AI calls that are gated, capped, and logged. Each step is a dbt model in the DAG. Analytics engineering ends at BI. Context engineering ends at agents. Under both: SQL and Jinja, lineage, profiles, tests, and CI.

The loop diagram is Agent sessions → dbt pipeline (chunk, embed, summarize) → Search and summaries (what broke, what fixed it) → Skills (lessons, with citations) → the next session. The session box is labeled "Claude code, Wizard." In the full talk, Wizard Desktop is the app he is working in, and the transcripts are Claude and Codex. The repo also reads Cursor, Claude.ai, and ChatGPT.

---

## 6. Problem

Context for a coding agent is text. Some of it is small and should travel with the session: skills, MCP tools, rules, memories. Some of it is large and non-tabular: old chats, tickets, docs, contracts. That second kind does not fit in the window. It has to be prepared ahead and retrieved when a task needs it.

Those chat logs already exist on developer machines. They record what was tried, what broke, and what worked. Left as local files, the next session cannot search them, and the organization cannot turn a repeated fix into a skill.

Warehouses already expose AI functions and search next to the tabular models. The missing practice is the same one analytics engineering already uses: a DAG, SQL, profiles, environments, tests, and a spend cap, colocated with the models the team already trusts.

## 7. Product outcome

A developer, working in the agent desktop they already use, can:

1. Land opted-in chat transcripts in Snowflake with a script they can preview before upload.
2. Build extract, chunk, classify, embed, and search as dbt models in the same project as their tabular work.
3. Summarize each conversation into the problem, the outcome, and the solution, with a quote that actually appears in the transcript.
4. Compare chunk sizes and embedding models on a fixed set of eval questions before spending on the whole corpus.
5. Ask the agent to write a `SKILL.md` from a search result, and review that file in git before any later session loads it.

An agent that then opens the project can search the corpus and load the skill. It does not receive the raw transcripts in the prompt.

Success for the first team is a cited answer to "what did we try last time, and what worked?", a skill merged through review, and a run log that shows the spend.

## 8. Users

| User | Job |
| --- | --- |
| Application developer | Preview and upload their own chats. Search them from the agent. Review the skill the agent drafts. |
| Coding agent, in Wizard Desktop or another desktop that can run dbt and edit the repo | Run the project, read search results, write `SKILL.md`. |
| Analytics or context engineer | Add a source, change a chunk size, add a taxonomy version, and compare eval scores. |
| Developer experience | Decide which skills become team or org standard. |
| Security | See what left the laptop, who can query it, and how long it is kept. |
| FinOps | Read `ai_run_log` and stop a run that would exceed the cap. |

## 9. Two kinds of context

| Kind | What it is | How it reaches the agent | This product |
| --- | --- | --- | --- |
| Just in time | Skills, MCP tools, and context that persists across sessions (rules, memories, project conventions) | Loaded or called when the task needs it | Consumes the `SKILL.md` this loop writes. Does not replace MCP or rule files. |
| Just in case | Large non-tabular text: chat transcripts first, then tickets, notes, docs, and contracts | Surfaced by a tool that searches an internal store, or the public web | Builds the store, the search, and the evals. |

The context window stays small. Retrieved passages and approved skills earn their tokens. Raw session logs do not.

## 10. Reference implementation

`dbt-chat-context-eng` is the end-to-end demo. The organization product keeps this shape and adds the controls in later sections.

```
ingest_chat_logs.py ──► RAW.CHAT_MESSAGES ──► stg ──► int_chat_units ──► chunk_chat_logs
   (local, redacts)        (full snapshot)              (paragraphs)        (chunk)
                                                                              │
                                                          chat_chunks_meta ──► chat_chunks_hashed
                                                                              │
                         search_chat_logs ◄── chat_chunks_embedded_classified ◄── chat_chunks_embed
                         (vector_search)                                      └── chat_chunks_classify

chat_chunks_embed ──► search_eval ──► search_eval_summary
stg ──► chat_conversation_text ──► conversation_summaries
```

Everything up through `chat_chunks_hashed` is warehouse compute. Everything under `models/context/ai/` calls Cortex and is disabled unless the run passes `ai_functions_enabled: true`.

### Ingest

`ingest/ingest_chat_logs.py` reads a mix of local logs, normalizes to one row per message, redacts on the machine, writes `chat_messages.jsonl` for review, and optionally loads a full snapshot.

| Source | How it is read | `chat_source` |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/**/*.jsonl` by default | `claude_code` |
| Codex | Session-blog file `YYYY/MM/<date>_codex_<project>.jsonl` | `codex` |
| Cursor | Session-blog file dated `_cursor_` | `cursor` |
| Claude.ai export | `conversations.json` | `claude_ai` |
| ChatGPT export | `conversations.json`, active branch only | `chatgpt` |

The parser keeps user and assistant text. It drops tool calls, tool results, sidechains, meta events, harness-injected text (task notifications, command output, system reminders, `AGENTS.md` injections), and Codex sessions that are the automated approval reviewer. Resumed Claude Code sessions are deduped on source plus message id. `--since YYYY-MM-DD` drops older messages. `--dry-run` uploads nothing. `--load` overwrites `CHAT_MESSAGES` through a named Snowflake connection, or `SNOWFLAKE_*` env vars with browser SSO as the default authenticator. The ingest virtualenv installs the Snowflake connector only, so it does not shadow the `dbt` binary.

Redaction runs before upload and replaces private keys, common vendor tokens, JWTs, `password`/`secret`/`api_key` assignments, and email addresses. It is regex-based. The preview file is the review step. `--no-redact` exists and is not acceptable for an organization load.

### dbt project

Profile name `chat_context`. `require-dbt-version: >=2.0.0`. Package `dbt-labs/dbt_context_engineering` 0.1.0. `on-run-start` creates the package run-log table.

Staging models are views. Context models are tables. A message key is `source || ':' || message_id`. A conversation key is `source || ':' || conversation_id`.

`int_chat_units` keeps the N most recent conversations (`demo_conversation_limit`, default 20; `null` means all). It splits messages on blank lines, then hard-splits any paragraph longer than `max_unit_chars` (default 800) so a pasted log cannot exceed the embedding window. `chunk()` packs those units inside one conversation, never splits a unit, and prefixes the role so the embedding sees who spoke. `chunk_target_tokens` defaults to 256. `chunk_overlap_tokens` defaults to 0.

`chat_chunks_hashed` stores a content hash. Embed is incremental on `chunk_id`: a changed hash re-embeds that chunk, a changed `embedding_fn_fingerprint` re-embeds the corpus, and `dbt build --full-refresh` re-embeds nothing unless `allow_full_reembed` is true. `guard_batch` aborts before any Cortex call when the delta exceeds `max_batch_rows` (10,000) or `max_est_tokens` (5,000,000). Each AI run logs a started event and a completed event.

### Classify, search, summarize, eval

Topic labels use a versioned prompt and JSON schema, `chat_topic` v1. The allowed topics are `coding_and_debugging`, `data_and_analytics`, `writing_and_communication`, `planning_and_strategy`, `learning_and_explanation`, and `chit_chat_or_other`. A new taxonomy is a v2 macro, not an edit to v1. Classify is not incremental: every enabled build relabels the in-scope chunks, which is why the conversation limit stays small.

`search_chat_logs` embeds `search_query` once and returns the top 10 twice: raw cosine similarity, then the same query filtered to `search_topic` before ranking. Short replies such as "Thanks, that worked!" score well against almost any query. The filtered run is the demonstration that similar is not relevant.

`conversation_summaries` calls `extract()` once per conversation, through `AI_COMPLETE`, with `model_extract` defaulting to `claude-sonnet-4-5`. Input is capped (`summary_input_chars` 6,000, `max_output_tokens` 400). The contract is:

| Field | Required | Meaning |
| --- | --- | --- |
| `problem` | yes | What the person was trying to do or fix, one sentence |
| `outcome` | yes | `solved`, `unsolved`, or `unclear` |
| `solution` | yes | What worked, or the last thing tried, one sentence |
| `evidence` | no | One short quote copied exactly from the conversation. Omit when no line supports the outcome |

The `grounded` test checks that a non-null evidence quote appears in `source_text`. Null evidence is allowed. Smaller chat models tend to leave evidence empty, which gives the test nothing to check, so the demo model stays large enough to quote.

`search_eval` embeds each row of `seeds/eval_questions.csv`, ranks chunks, and marks a hit when the expected conversation is in the top 5. Questions must be paraphrases. Reusing the conversation's own keywords makes every chunk size look perfect. `search_eval_summary` is one row per schema: questions found, questions total, chunks embedded, average chunk tokens, estimated embedding tokens, and estimated cost. Parallel schemas with `chunk_target_tokens` of 128, 256, and 512 are the bake-off. Wizard Desktop's pairing note is plan mode for a taxonomy v2, and parallel chats for those three sizes.

Default embedding model is `snowflake-arctic-embed-l-v2.0-8k` with `embedding_max_tokens` 4,000, chosen because session logs are messy and a larger model carries more dimensions. A structured corpus that looks the same everywhere uses a smaller model. Changing `embedding_model` changes the fingerprint and re-embeds under the same guard. Putting the conversation title into the embedded text is `metadata_in_text` (default false) and also changes the hash.

Tests that ship with the repo: unique and not-null keys, chunks fit the embedding window, topic labels match the schema, every AI run completed, embedded chunks still exist upstream, summary outcomes are in the enum, and evidence is grounded.

The repo does not generate `SKILL.md`. That step is the agent, in the demo Wizard, reading the search and writing the file. Git is the review.

## 11. System for a large organization

The demo is one developer, one `RAW.CHAT_MESSAGES` table, one Snowflake role, and a 20-conversation sample. The product keeps the DAG and adds a boundary around whose text it is.

```
developer machine                         Snowflake                                      agent desktop
─────────────────                         ─────────                                      ─────────────
Claude Code, Codex, Cursor,               RAW.CHAT_MESSAGES, partitioned by team_id
Claude.ai and ChatGPT exports             and actor_id
        │                                 staging → units → chunks → hash
        │  ingest, dry-run, redact        embed and classify, gated
        └──────────────────────────────►  summaries, eval, search
                                          ai_run_log
                                                                               search tool
                                          SKILL.md draft ◄── agent reads search results
                                                 │
                                                 └── git review ──► skill path later sessions load
```

One dbt project holds the analytics DAG and this context DAG. They share profiles, environments, lineage, and CI. They can run as separate jobs so an embedding backlog does not delay the metrics build.

| Environment | Corpus | AI calls |
| --- | --- | --- |
| dev | The engineer's own opted-in chats, limited by `demo_conversation_limit` | Off until the zero-AI models have been inspected. Then on, under the guard. |
| ci | Fixture conversations and a frozen eval seed | Disabled. Tests of shape, keys, and chunk bounds run. Grounding and eval run in a scheduled canary, not on every pull request. |
| prod | Team corpus the retention policy allows | On, with the team cap. Full corpus only after a sample run has been reviewed. |

## 12. Functional requirements

### Ingest

- **FR-1.** The collector supports the five source formats in the reference repo. Claude Code and Codex are the sources the talk demonstrates. Cursor, Claude.ai, and ChatGPT ship in the same contract because the repo already parses them.
- **FR-2.** Default mode is dry-run. It writes a local JSONL of exactly the rows that would upload, plus counts by source, a character and token estimate, and a redaction tally. Load is a separate flag.
- **FR-3.** Redaction runs on the laptop before any network call. The organization pattern list starts from the repo's patterns and is extended by security. A load with redaction disabled is rejected by the published job.
- **FR-4.** Tool payloads, harness-injected turns, and automated reviewer sessions are not uploaded. They are large, noisy, and often contain whole files.
- **FR-5.** Each row carries `chat_source`, conversation id, message id, turn index, role, created time, project, title when the source has one, text, and ingested time. Keys are prefixed with the source so tools cannot collide.
- **FR-6.** A developer can limit the load with `--since`. Re-running the load is safe. The reference loader overwrites the snapshot. Downstream content hashes decide what is re-embedded.
- **FR-7.** For the organization, the snapshot is partitioned by team and actor. One developer's load does not replace another team's table. The demo's single overwrite table is the personal-project behavior, not the shared-account behavior.
- **FR-8.** Upload uses the Snowflake connection the developer already has (`connections.toml` or SSO). The collector does not send transcript bodies to a third-party API. Embedding and summarization happen in Cortex.

### Pipeline

- **FR-9.** The shape is extract, transform, chunk, embed, search. Classify sits on the chunk, and search can filter on its label before ranking. Each step is a dbt model.
- **FR-10.** Extract, unit split, chunk, metadata, and hashing call no warehouse AI function. CI fails a pull request that puts a Cortex call in those models.
- **FR-11.** Units are paragraphs, hard-split at `max_unit_chars`. `chunk()` does not split a unit and does not cross conversations. Role is visible in the chunk text.
- **FR-12.** AI models are disabled unless the invocation sets `ai_functions_enabled: true`. A select of an AI model does not bypass the gate.
- **FR-13.** `guard_batch` runs before any classify, embed, or extract call and stops the run when the batch exceeds the row cap or the token cap. The caps live in the dbt project.
- **FR-14.** Embed is incremental on content hash and embedding fingerprint. A model swap re-embeds the in-scope corpus under the same guard. A full refresh does not re-embed unless `allow_full_reembed` is true.
- **FR-15.** Classify uses a versioned prompt and a closed schema. Changing the taxonomy adds a version. Old labels stay reproducible.
- **FR-16.** Search embeds the question with the same model as the corpus, returns the closest chunks with citation columns (`conversation_title`, `chat_source`, `citation_url`, topic, text), and can prefilter by topic. The product also returns a raw run and a filtered run so a developer can see what the filter removed.
- **FR-17.** The LLM that writes an answer reads the retrieved chunks, not the corpus. That call is a separate, logged step from the embedding.
- **FR-18.** Summaries use the problem, outcome, solution, and optional evidence contract. Evidence, when present, is a verbatim substring of the source text.
- **FR-19.** Development runs sample. `demo_conversation_limit` defaults to a small N. Processing the full corpus is an explicit change, reviewed like any other var change that increases spend.
- **FR-20.** Chunk size, overlap, metadata-in-text, and embedding model are vars. A developer can build 128, 256, and 512 in parallel schemas and read `search_eval_summary` to compare hits, chunk counts, and estimated tokens.
- **FR-21.** Eval questions are paraphrases stored in a seed. Each names the conversation key that should be found. Hit-at-5 is the score the demo uses. Keyword reuse in the question is a bad eval and fails review.
- **FR-22.** Session logs use the larger embedding model by default. A corpus whose text is uniform and structured uses a smaller model, with `embedding_max_tokens` kept inside that model's window.
- **FR-23.** Keyword search, ranking, and tokenization are in the product because the talk treats them as battle-tested complements to warehouse AI. The reference repo ships vector search plus a topic prefilter, not a keyword index. The organization design adds keyword search as a filter or a hybrid rank in front of the vector search, using the same citation columns. It does not replace the vector path.

### Skills

- **FR-24.** The agent writes `SKILL.md` from a named search result. The file states when to apply the lesson, the lesson itself, and the citations (conversation key and chunk id).
- **FR-25.** The warehouse does not write into the skill directory. The file enters through git. A team skill needs a reviewer. An org-standard skill needs the code owners of the shared skill path.
- **FR-26.** A skill with no citation, or a citation that does not resolve to a retained chunk, is not approved.
- **FR-27.** Later sessions load the approved skill as just-in-time context. They can also call search. They are not given the raw transcript.

### Classic analytics colocation

- **FR-28.** The project uses the team's existing Snowflake connection, role, warehouse, and dbt environments. There is no second deploy tool.
- **FR-29.** Tickets and documents enter through their own staging models and then the same unit, chunk, hash, embed, classify, and search models. Chat is the first source. The others wait until chat search has an eval baseline.

## 13. Data contracts

### Landed message

`chat_source`, `conversation_id`, `conversation_title`, `project`, `message_id`, `turn_index`, `role`, `created_at`, `message_text`, `ingested_at`. Organization columns added on top of the demo: `team_id`, `actor_id`, `sensitivity` (`internal` or `restricted`).

### Staged message

`chat_source`, `conversation_key`, `message_key`, `turn_index`, `role`, `created_at`, `conversation_title`, `project`, `message_text`, `ingested_at`. One row per source plus message id, latest ingest wins.

### Unit and chunk

Unit: `unit_id`, `message_key`, `conversation_key`, `unit_order`, `role`, `unit_text`.

Chunk: `chunk_id`, `conversation_key`, `chunk_text`, `content_hash`, source unit ids, citation url, title, project, source, start time, token estimate. A chunk belongs to one conversation.

### Embedding and topic

`chunk_id`, `embedding`, `embedding_dimension`, `model_version`, `embedding_fn_fingerprint`, `embedded_at`. Topic: `chunk_id`, `topic`, prompt version.

### Summary

`conversation_key`, `problem`, `outcome`, `solution`, `evidence`, `source_text`, `prompt_version`.

### Eval

Seed: `question`, `expected_conversation_key`. Result: `hit_at_5`, `best_rank`, `top_5_conversations`, `chunk_target_tokens`, `embedding_model`.

### Skill

`title`, `applies_when`, `lesson`, `citations`, `status` (`draft`, `approved`, `rejected`), `scope` (`team`, `org`).

## 14. Search behavior

1. Embed the question with the corpus model.
2. Optionally restrict to one topic, or, once keyword search exists, to chunks that match the keyword filter.
3. Rank by cosine similarity and return citations with the text.
4. Hand only those chunks to the answering model.

Short, formulaic chunks rank as slightly similar to almost everything. Topic filter is required for the session-log corpus before anyone trusts the top 10. The raw top 10 stays available so the filter can be judged.

Query text is stored with the same retention rules as the chats it searches. The run log stores the function name, model, estimated tokens, estimated cost, and whether the run completed.

## 15. The loop

1. The developer works in Claude Code, Codex, Cursor, or the chat products. Logs stay local.
2. They dry-run the ingest, read the JSONL, then load.
3. They build the zero-AI models and look at `chunk_chat_logs`.
4. They enable AI on a sample. Embed, classify, and summarize run under the guard.
5. They run the eval and, if they are comparing chunk sizes, the parallel schemas.
6. They search. The agent writes `SKILL.md` from a result they name. They open a pull request.
7. The next session loads the skill and can search again. That session's log can be ingested later, which is how a bad skill shows up as another unsolved conversation.

## 16. Security and tenancy

Session logs contain code, customer references, and secrets pasted by mistake.

- Redaction is local and mandatory for any shared warehouse. The developer reviews the preview because regex redaction misses things.
- The search role can read its team partition. Cross-team search is off until a team publishes a corpus or a skill.
- `actor_id` on the shared table is the warehouse identity used for delete and export requests. The demo does not pseudonymize. The organization job does, with the mapping held outside the search role.
- Restricted rows are excluded from org-wide skills and from any published corpus.
- Raw snapshots expire on the retention window legal sets. A skill keeps its lesson. A citation past retention resolves as expired rather than as the original text.
- Ingest, search, summary, and skill approval are audited.

## 17. Cost

Sampling is the development default. The guard is the production default. Both are in the talk and in the repo.

- AI models do not build until someone opts in for that run.
- Embed incremental work only. Classify relabels the in-scope set on each build, so the in-scope set stays the sample until classify has a cache of its own.
- A model change and a chunk-size change are expected to re-embed. They still pass `guard_batch`.
- `ai_run_log` is the FinOps source: function, model, estimated tokens, estimated cost, started, completed.
- A test asserts every started AI run completed.
- CI does not call Cortex. A canary on fixture data checks that the provider model behind a version name still returns the expected embedding dimension.

## 18. Quality

| Test | Fails when |
| --- | --- |
| Message keys | Duplicate source plus message id survives staging |
| No AI in the SQL stages | A Cortex function appears above `models/context/ai/` |
| Chunk window | A chunk's token estimate exceeds `embedding_max_tokens` |
| Topic schema | A label is outside the versioned enum |
| Run log | A started AI run has no completed event |
| Grounding | Evidence is non-null and is not a substring of `source_text` |
| Outcome enum | Outcome is outside `solved`, `unsolved`, `unclear` |
| Eval | A reviewed question set drops below the team's hit-at-5 bar after a chunk or model change |
| Skill | A candidate has no citation |
| Budget | An AI model is enabled with no `guard_batch` |

The eval bar is set from the sample bake-off, not from a universal number. Changing chunk size or model without rerunning `search_eval` fails review.

## 19. Developer experience

The path matches the demo, then adds the organization gate.

1. Copy `profiles.example.yml` into the existing dbt profiles. Install the package. `dbt deps`.
2. Dry-run ingest. Open `chat_messages.jsonl`. Load.
3. `dbt build` with AI disabled. Read the chunks.
4. Enable AI on the sample. Check `ai_run_log`.
5. Run a search with and without `search_topic`.
6. Fill `eval_questions.csv` with paraphrases. Compare chunk sizes if search looks wrong.
7. Ask the agent for a `SKILL.md` from one search. Open the pull request.

A new chat source is one parser that emits the landed-message contract, plus a page that says where the files live and what it skips.

Wizard Desktop is the demo environment: beta, with a waitlist at the time of the video. The product does not require Wizard. It requires an agent that can run dbt in the project, read the search model, and write a markdown file. Parallel agent chats are how the chunk-size bake-off is run in the demo. In the organization, those are separate dbt schemas or separate job vars, so the comparison survives after the chat ends.

## 20. Non-functional requirements

- A dry-run of a single developer's logs finishes without a warehouse connection.
- After a load, a sample build is searchable on the next dbt job. The first shared schedule is hourly during the workday, AI models included only when the var is on.
- Search over a team corpus of one million chunks returns in under three seconds at the 90th percentile using the warehouse vector function. A managed index waits until that misses.
- One source failing does not block another. dbt selection by tag is the retry unit.
- The analytics job and the context job are separable.

## 21. Delivery

| Slice | What ships | Demo checkpoint |
| --- | --- | --- |
| 1. Personal loop | The reference repo, unchanged in shape: ingest, zero-AI build, gated AI, search, summary, eval, run log | A developer reproduces the video on their own Claude and Codex logs, on a sample of 20 conversations |
| 2. Bake-off | Documented parallel schemas for chunk size and embedding model, eval seed filled with real paraphrases | `search_eval_summary` shows which size finds the expected conversations |
| 3. Skill | Agent prompt and pull-request path from a search result to `SKILL.md` | Wizard, or the team's agent, writes a cited skill and a reviewer merges it |
| 4. Shared warehouse | Team and actor columns, no cross-user overwrite, mandatory redaction, retention, audit | A second developer can load without destroying the first developer's snapshot |
| 5. More text | Ticket staging, then docs, through the same chunk and search models. Keyword filter in front of vector search | One search spans chats and tickets inside a team, with the topic or keyword filter on |

## 22. Acceptance for the first team

- Two developers have dry-run, reviewed, and loaded Claude Code or Codex logs. Redaction counts were inspected.
- The zero-AI build succeeds with AI left disabled.
- An enabled sample run embeds only the limited conversations, logs the cost, and refuses a batch cut down below the row count with `max_batch_rows`.
- A search returns a chunk whose citation identifies the conversation, and the topic-filtered run drops the boilerplate hits.
- Eval hit-at-5 is recorded for at least two chunk sizes.
- One `SKILL.md` is merged, and a later session loads it without anyone pasting the lesson into the prompt.
- Security has signed the flow: local redaction, team role, Cortex only, retention window.

## 23. Decisions still open

1. The legal retention window for raw coding transcripts that can contain customer data.
2. Whether Cursor, Claude.ai, and ChatGPT are in the first organization rollout or stay available and off by default. The repo parses them. The talk demonstrates Claude and Codex.
3. Which Cortex models are allowed in this account and region. The repo defaults are `snowflake-arctic-embed-l-v2.0-8k` and `claude-sonnet-4-5`, and it names cross-region inference when those are unavailable. `llama3.1-70b` is called out as too weak for the evidence quote.
4. The skill directory each supported agent already loads, so `SKILL.md` lands on a real path.
5. Whether tickets and contracts are already in the warehouse.
6. Who code-owns the org skill path.
