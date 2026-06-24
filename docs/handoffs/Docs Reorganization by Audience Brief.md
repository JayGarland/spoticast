# Docs Reorganization by Audience — Implementation Brief

Audience: Manager (implementation)
Chef: gates result before commit
Date: 2026-06-24
Status: APPROVED — boss + chef gate passed

---

## Goal

Split `docs/strategy/` into two audience-based folders so the boss only sees
boss-facing files and agents only see agent-facing files. Leave `docs/handoffs/`
untouched. Do not create `docs/archive/` (out of scope).

---

## New Folder Structure

```
docs/
├── boss/               ← CEO-facing docs; you read this, agents don't
│   ├── decisions/      ← all *-brief.md and *-decision-*.md files
│   └── research/       ← move docs/research/* here
│
├── agents/             ← agent onboarding + ops; boss doesn't read this
│   ├── chef-guides/    ← CLI reference guides for Chef
│   └── reviews/        ← agent-reviews/ subfolder
│
├── handoffs/           ← DO NOT TOUCH
└── strategy/           ← will be empty after moves; delete the folder
```

---

## File Mapping

### Move to `docs/boss/`

| From | To |
|---|---|
| `docs/strategy/activity-board.md` | `docs/boss/dashboard.md` |
| `docs/strategy/bounded-personal-music-narrator-pivot.md` | `docs/boss/product-pivot.md` |
| `docs/strategy/v0.1-roadmap.md` | `docs/boss/roadmap.md` |
| `docs/strategy/resonova-market-benchmark.md` | `docs/boss/market-benchmark.md` |

### Move to `docs/boss/decisions/`

All `*-brief.md` and `*-decision-*.md` files in `docs/strategy/`:

- `attention-board-next-moves-brief.md`
- `audio-level-balance-brief.md`
- `companion-direction-and-memory-use-brief.md`
- `deep-research-generation-mode-brief.md`
- `lockscreen-transition-decision-brief.md`
- `mobile-background-playback-reliability-brief.md`
- `mobile-playback-hardening-brief.md`
- `persistent-profile-feedback-brief.md`
- `playlist-order-variety-brief.md`
- `private-phone-access-brief.md`
- `release-access-and-memory-positioning-brief.md`
- `resonova-mvp-audit-brief.md`
- `tts-model-options.md`
- `v0.1-access-shape-decision-brief.md`
- `v0.1-access-shape-decision-record.md`
- `product-destination-decision-record.md`

Keep original filenames inside `decisions/`.

### Move to `docs/boss/research/`

Everything currently in `docs/research/`:
- `Resonova-analysis-market-competition.md`
- `AI Companion Personalization and Trust.md`

### Move to `docs/agents/`

| From | To |
|---|---|
| `docs/strategy/ai-agent-company-operating-model.md` | `docs/agents/operating-model.md` |
| `docs/strategy/ai-agent-role-job-specs.md` | `docs/agents/job-specs.md` |
| `docs/strategy/ai-agent-recruitment-execution-guide.md` | `docs/agents/recruitment-guide.md` |
| `docs/strategy/boss-profile.md` | `docs/agents/boss-profile.md` |
| `docs/strategy/agent-performance-weights-2026-06-19.md` | `docs/agents/performance-weights.md` |

### Move to `docs/agents/chef-guides/`

| From | To |
|---|---|
| `docs/strategy/antigravity-cli-chef-guide.md` | `docs/agents/chef-guides/antigravity-cli.md` |
| `docs/strategy/cursor-cli-chef-guide.md` | `docs/agents/chef-guides/cursor-cli.md` |

### Move to `docs/agents/reviews/`

| From | To |
|---|---|
| `docs/strategy/agent-reviews/` (entire subfolder) | `docs/agents/reviews/` |

---

## Duplicate Operating Model — Resolution Required

There are TWO operating model files:
- `docs/strategy/ai-agent-company-operating-model.md` — 627 lines, canonical (move to `docs/agents/operating-model.md`)
- `docs/strategy/operating-model.md` — 211 lines, older/shorter version

**Action**: Read both. If `operating-model.md` contains any content NOT in the
larger file, merge it in first. Then delete `operating-model.md` (do not move
it — it's superseded). If it's a pure subset, delete it directly.

---

## Cross-Reference Cleanup — MANDATORY

After all moves, update every inbound reference. A grep for the old paths
returns 38 files. Walk through them and update:

- `docs/strategy/operating-model.md` → `docs/agents/operating-model.md`
- `docs/strategy/ai-agent-company-operating-model.md` → `docs/agents/operating-model.md`
- `docs/strategy/ai-agent-role-job-specs.md` → `docs/agents/job-specs.md`
- `docs/strategy/ai-agent-recruitment-execution-guide.md` → `docs/agents/recruitment-guide.md`
- `docs/strategy/boss-profile.md` → `docs/agents/boss-profile.md`
- `docs/strategy/agent-performance-weights*.md` → `docs/agents/performance-weights.md`
- `docs/strategy/activity-board.md` → `docs/boss/dashboard.md`
- `docs/strategy/bounded-personal-music-narrator-pivot.md` → `docs/boss/product-pivot.md`
- `docs/strategy/v0.1-roadmap.md` → `docs/boss/roadmap.md`
- `docs/strategy/resonova-market-benchmark.md` → `docs/boss/market-benchmark.md`
- `docs/strategy/<any-brief>.md` → `docs/boss/decisions/<filename>`
- `docs/research/` → `docs/boss/research/`
- `docs/strategy/antigravity-cli-chef-guide.md` → `docs/agents/chef-guides/antigravity-cli.md`
- `docs/strategy/cursor-cli-chef-guide.md` → `docs/agents/chef-guides/cursor-cli.md`

Also check `AGENTS.md` at repo root.

---

## Verification Before Handing Off

Run these checks and include output in your handoff:

```bash
# No remaining references to old paths (should return empty or only self-references in handoffs)
grep -r "docs/strategy/" docs/ --include="*.md" -l
grep -r "docs/research/" docs/ --include="*.md" -l

# New folders exist and have the right files
ls docs/boss/
ls docs/boss/decisions/
ls docs/agents/
ls docs/agents/chef-guides/

# docs/strategy/ is empty (ready to delete)
ls docs/strategy/
```

`docs/strategy/` should be empty after all moves. Remove it.

---

## Commit

Single commit. Message:

```
Reorganize docs by audience: boss/ and agents/ replace strategy/

Split docs/strategy/ into docs/boss/ (CEO-facing) and docs/agents/
(agent-facing) so each reader opens the right folder directly.
Move docs/research/ into docs/boss/research/. Update all inbound
cross-references. docs/strategy/ removed.
```

---

## Out of Scope

- `docs/handoffs/` — do not touch
- `docs/archive/` — do not create
- Any file content changes beyond cross-reference path updates
