# Deep-Research Generation Mode — Idea Brief

Audience: Boss + Agents
Status: Captured 2026-06-22, boss-raised. Not approved, not built — design candidate.

## The idea (boss)

Add an optional **deep-research mode** for the research + script-writing parts of cast generation.
When enabled, the background does heavier, agentic "harness engineering" — an orchestrated,
manager-style multi-step process — to research and write, instead of the current few-shot calls.
It takes longer to prepare, but produces a richer cast, and is the natural place to run **more
real-time personalization sub-processes** during generation.

## What generation does today (for contrast)

`server.py:_run_generation` is a short, mostly-linear pipeline: build playlist context → optional
Last.fm enrich → grounded research enrich → one Gemini script generation. Fast, cheap, shallow.

Deep-research mode = replace that middle with an **agentic loop**: plan research questions →
gather from multiple sources → personalization sub-steps (taste-aware angle selection) → draft →
self-critique → finalize.

## Chef assessment

Worth pursuing as a **post-v0.1, opt-in mode** — but design it before building.

- **Value:** real. It's the natural host for the personalization the companion work needs (a
  sub-step that tailors research angles to the listener's taste), and it lets quality scale with
  patience for casts the user cares about.
- **Architecture caution:** "call our company's manager to execute" most likely means an *in-app
  agentic orchestration modeled on the manager pattern* (server-side subagents/tools), **not**
  literally shelling out to the dev-time manager CLI (RUG/copilot) at runtime — that path is
  fragile, auth-bound, slow, and not built for production request flow. Confirm intent; recommend
  an in-app agent loop (or a real agent framework) over invoking the CLI manager per cast.
- **Cost/budget (the big one):** an agentic multi-step pipeline makes many more LLM/tool calls —
  potentially 5–20× the cost of a normal cast. Given the current budget pressure, this MUST be
  opt-in, budget-bounded (max steps / max spend per deep cast), and ideally owner-only at first.
  Mitigation worth evaluating: **prefix-cache stability** — keep the prompt prefix stable across the
  loop's steps so the provider's cache absorbs most tokens. This is the technique behind the boss's
  `reasonix` repo (`github.com/esengine/deepseek-reasonix`); on DeepSeek's cache pricing it can cut
  long-running cost dramatically, which could make a deep mode actually affordable.
- **Latency/UX:** "takes longer" needs a real *deep-research-in-progress* state with streamed
  progress, not a silent long spinner. The existing SSE job pipeline can carry step updates.
- **Quality risk:** more steps = more places to hallucinate or bleed. The locked rules still
  apply — no cross-cast memory bleed, descriptor-not-inventory, hosts never narrate the listener.

## Recommendation

1. Keep the current fast path as the default; deep-research is an additive opt-in mode.
2. Do a **design pass first** (architecture spec: in-app agent loop vs framework; step budget;
   personalization sub-steps; progress UX) — route to a manager/specialist, not a blind build.
3. Gate the build on budget and on the companion-stance (B) work landing, since deep mode is where
   the per-signal personalization roadmap (§4 of the companion brief) would live.

## Open decisions for boss

- Scope: research-only, or research **and** script writing?
- Owner-only experiment first, or aim at customers?
- Acceptable latency and a per-deep-cast budget ceiling?
- In-app agent loop (recommended) vs literally invoking the manager CLI per cast?
