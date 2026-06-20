# Internal Auditor / Product Reviewer — Trial Report

Audience: Boss + Chef
Created: 2026-06-21
Status: trial deliverable (inspect-only; no code changed, no commits, no files patched)
Scope source: `docs/handoffs/Internal Auditor Product Reviewer Trial Brief.md`

---

## 1. Summary

Resonova is a coherent, genuinely working local MVP: Spotify playlist → AI two-host script → multi-speaker TTS → browser playback that interleaves commentary (HTML `<audio>`) with music (Spotify Web Playback SDK). The recovery, observability, offline, saved-cast, and media-session work over June 19–20 is real and has materially raised quality. The desktop happy path is solid.

It is **not yet ready for broader customer testing**, and the reason is narrow and specific, not a general quality collapse. One release-blocking product defect remains in the core playback loop ("blind playback"), and one repo-hygiene defect (whole-tree CRLF churn) currently defeats the chef's own git-diff gate. Everything else is either already addressed, polish, or correctly parked.

My judgment: **good engineering, honest handoffs, one unresolved core risk + one process risk standing between this and a wider phone trial.** It is ready for *continued single-owner phone testing with the new Diag timeline*, which is exactly what the next step should be — not yet ready for non-owner customers.

---

## 2. Severity-Ranked Findings

Ordered by user/release risk.

| # | Sev | Finding | Evidence | Impact | Recommended next step |
|---|-----|---------|----------|--------|----------------------|
| F1 | **High** | **"Blind playback" still trusts HTTP 200 and masks real stalls.** When `/me/player/play` is accepted but `_waitForSpotifyPlaybackStart()` doesn't confirm within 3s (5s on retry), the code arms a `duration_ms`-based deadline and presents a possibly-silent track as "playing," advancing the queue at the track's nominal end. | `player.js:844` (`_waitForSpotifyPlaybackStart`), `1150–1171` (blind branch), `1189–1197` (`_setBlindSpotifyDeadline`). Verified present in current build. | User hears silence for a whole track while UI shows playback; the exact "music begins, then halts near the start" symptom the owner reported. | **Release blocker.** Implement stall-aware verification (External Audit "Item 2") — require position to *advance across two samples*, not just match URI once. Do **not** keep blind force-advance as the primary mechanism. |
| F2 | **High** | **Entire working tree is CRLF↔LF churn — every tracked file shows as modified.** `git diff --stat` reports 44 files, 11,975 insertions / 11,975 deletions (exactly equal); `git diff --ignore-all-space` on source returns empty. | `git status` (44 modified), `git diff --stat`, `git diff --ignore-all-space resonova/api/gemini.py` → empty. | The operating model's review gate depends on `git diff` (operating-model.md "Required gate behavior"). A diff this noisy makes real change review impossible and risks a giant meaningless commit that buries a future real bug. | **Process blocker before next commit.** Normalize line endings (add `.gitattributes` with `* text=auto eol=lf`, renormalize once) so future diffs are reviewable. This is a chef/boss action — flagged here as a finding, not patched. |
| F3 | **Med** | **Spotify health is scattered booleans, not one state machine.** `_isSpotifyHealthy()` is derived ad hoc from ~5 flags checked at ~7 entry points. | `player.js` `_isSpotifyHealthy` (~`:75–82`), flags set across recovery/play/previous paths (per External Intermittent Audit F3, code-confirmed). | "Fixed one case, broke another" maintenance risk; flags can desync. Coherent *enough* today. | Park unless recovery churn continues. If it does, consolidate behind one status getter (Audit "Item 4"). Not a blocker. |
| F4 | **Med** | **No automated tests on the highest-risk surface.** The only test file covers variety + episode CRUD. Zero tests touch `player.js`, `spotify.py`, recovery, or server endpoints. | `tests/test_variety_episodes.py` is the sole test; grep shows no `TestClient`/endpoint/player tests. | The 1,900-line player (the most fragile, most-edited file) has no regression net; every playback fix is validated only by `node --check` + manual phone testing. | Add a thin server-endpoint smoke test (`TestClient` over `/api/episodes`, PATCH/DELETE, auth status) and a JS unit harness for queue/health logic. Medium priority; do after F1/F2. |
| F5 | **Med** | **Fixed timeouts race mobile latency.** Device-ready 3s→5s, Connect-visibility 5s, playback-start 3s/5s are hard-coded. | `player.js` recovery timeouts (Audit F4, code-confirmed). | On slow/H+ mobile data, recovery can report failure even when it would have succeeded — intermittent false `recoveryFailed`. | Gather Diag-timeline data first (now possible), then tune or make adaptive. Do **not** tune blind. |
| F6 | **Low** | **Connect-device round-trip before every play.** `_sendSpotifyPlayCommand()` calls `_waitForSpotifyConnectDevice()` (a `/me/player/devices` call, up to ~5s) even on a healthy device. | `player.js` `_sendSpotifyPlayCommand` (Audit F6). | Adds startup latency to every music segment in the common healthy case. | Gate to post-recovery / first-play only. Polish. |
| F7 | **Low** | **ffmpeg setup is macOS-only in README, but the owner runs Windows.** README lists only `brew install ffmpeg` / `brew install uv`. | `README.md:38,40`; owner environment is Windows. | A fresh Windows setup (or a future agent/contributor) hits a missing-ffmpeg wall with no guidance; pydub PCM→MP3 fails. | Add Windows ffmpeg/uv instructions. Docs-only; low risk because the current machine already has it. |
| F8 | **Low** | **No favicon handling.** No favicon route or link tag. | grep: no `favicon` in `server.py` / `index.html`. | Cosmetic 404 on every page load; clutters logs the Diag timeline now competes with. | Park (cosmetic). |

---

## 3. Evidence

**Verified facts (read directly from current source / git this pass):**

- Product shape and flow: `README.md`, `Resonova MVP Audit Handoff.md`, `resonova/` layout (`server.py`, `episodes.py`, `variety.py`, `api/`, `web/player.js` 1,900+ lines).
- Served build is `player.js?v=20260620-weak-network-fix` (`index.html:379`) — i.e. the weak-network hotfix is the live build.
- Offline resilience **landed**: online/offline listeners and `navigator.onLine` guards present in `player.js` (10 matches); `pageshow/pagehide` present (4); Skip-Music present (9). Confirms `Offline Bad Network Resilience Implementation Handoff.md` is in the live code.
- Observability **landed**: `_obsRecord`/`_obsTimeline`/`deviceGeneration` present (38 matches). Confirms the observability handoff.
- F1 verified open: `_waitForSpotifyPlaybackStart` (`player.js:844`) returns true on a single `currentUri === uri && !state.paused` check — it does **not** verify position advancing; blind-deadline branch live at `1150–1197`.
- F2 verified: `git diff --stat` = 11,975/11,975 equal; `git diff --ignore-all-space resonova/api/gemini.py` empty → pure EOL churn. Recent playback commits *are* committed (`76f75f0`, `417abea`, `effba24`, `916ca16`…); the dirty tree is churn, not pending feature work.
- Test coverage verified: `tests/` contains only `test_variety_episodes.py`.

**Assumptions / not verified (honest gaps):**

- The intermittent mobile stall was **not reproduced** — desktop cannot reproduce mobile background/network conditions. F1/F5 rest on code analysis + owner reports, consistent with the external auditor's own limitation note.
- TTS audio quality and real Spotify Premium in-browser playback not re-measured (no live Spotify session this pass).
- Commit-by-commit diff review not performed for feature correctness — the EOL churn (F2) makes per-commit content diffs unreliable right now anyway.
- F3/F5/F6 line attributions cross-checked against the External Intermittent Audit Report and confirmed by feature-presence grep, not by full re-reading every branch.

---

## 4. Repro / Inspection Steps

Anyone (boss, chef, future QA agent) can repeat these:

**Confirm F1 (blind playback):**
1. `grep -n "_setBlindSpotifyDeadline\|_waitForSpotifyPlaybackStart" resonova/web/player.js`.
2. Read `_waitForSpotifyPlaybackStart` (~`:844`): confirm it only checks URI match + not-paused once, with no position-advance loop.
3. On a real phone with Diag on, play to a Spotify segment, lock/idle, return. Watch for `play:cmd:ok` followed by `play:start:blind` in the timeline — that is the defect firing.

**Confirm F2 (EOL churn):**
1. `git diff --stat` → note equal insertions/deletions across all files.
2. `git diff --ignore-all-space resonova/api/gemini.py` → empty output proves churn is line-endings only.

**Confirm F4 (test gap):** `ls tests/` → single file; `grep -rn "TestClient\|player" tests/` → no endpoint/player coverage.

**Capture a real failure (the key next test):** Diag on → reach Spotify segment → lock phone long enough to trigger the stall → return → tap **Copy Timeline** → paste. The branch is now readable: `offline+online` = network; `pagehide persisted=true / pageshow persisted=true` = bfcache; `visibilitychange hidden → device:discard → recovery:start` = stale device; `play:cmd:ok → play:start:blind` = accepted-but-silent (F1).

---

## 5. Release-Blocking Risks

Must be resolved before exposing Resonova to non-owner customers:

1. **F1 — blind playback.** A customer can hear a full track of silence while the UI says it's playing. This is the single most likely "the app is broken" report from a new user and it is in the core loop. Blocker.
2. **F2 — CRLF working-tree churn.** Not user-facing, but it disables the review gate that protects every future change before a customer build. Resolve before the next feature commit.

Everything else (F3–F8) is non-blocking. The offline/observability/media-session/saved-cast work is already at acceptable quality for a wider owner-driven trial.

---

## 6. Recommended Next Tests

In priority order:

1. **Phone, with new Diag timeline (highest value):** reproduce the intermittent stall and capture one Copy-Timeline log. This converts F1/F5 from hypothesis to data and tells you whether the dominant branch is blind-playback, stale-device, or offline. Do this *before* writing any more recovery code.
2. **Bad-network playback (H+/throttled):** verify the weak-network hotfix actually moves to recovery/fallback instead of showing the wrong segment; confirm the now-playing text no longer lags the segment.
3. **Offline degradation:** airplane-mode mid-Spotify-segment → confirm offline banner, "Spotify unavailable offline", Skip-Music advances to commentary, cached library renders. (Checklist already in the offline handoff.)
4. **Lockscreen / Media Session:** lock during commentary vs during Spotify; confirm controls appear for commentary and note whether they disappear during Spotify (known SDK limitation, not a bug).
5. **Saved cast / replay:** generate same playlist 3× → confirm Run #1/2/3, distinct fingerprints, rename/delete, backward-compat replay of old episodes.
6. **Return-to-player / now-playing trail:** confirm the mini-panel tracks segment changes live from the library screen.

---

## 7. Parked Items (real, but do not implement yet)

- **F3 health state-machine consolidation** — only if recovery churn continues; premature otherwise.
- **F5 adaptive timeouts** — park until phone-timeline data exists; tuning blind is worse than waiting.
- **F6 per-play device round-trip optimization** — polish.
- **F8 favicon** — cosmetic.
- **PWA / service worker for true offline app-shell** — noted as out of scope in the offline handoff; correct to park.
- **Media Session album art (V2)** — needs cached Spotify artwork URLs; park.
- **Episode-detail cache TTL pruning** — accumulates slowly; fine at personal scale.
- **Product-direction features** (persistent taste profile, feedback loops, lenses) — these are roadmap, not quality blockers; out of scope for this review.

---

## 8. Final Recommendation

**Use carefully.**

Rationale tied to role fit: Resonova's quality is good enough to keep iterating with the owner on a phone, but two specific risks (F1 user-facing, F2 process) make a *broader* customer trial premature. "Use carefully" = continue owner-driven phone testing with the new Diag timeline, fix F1 and F2, then re-review for wider exposure. The right next action is **data capture (Section 6, test 1), not more code** — the observability pass exists precisely so the next fix is evidence-led.

This is not "restrict" (the product isn't fragile across the board — most focus areas are already handled) and not "reject" (the core flow works and the recent work is sound). It is one core fix and one hygiene fix away from a wider trial.

---

## 9. Self-Assessment Against Role Spec

Measured against `docs/strategy/ai-agent-role-job-specs.md` → "Internal Auditor / Product Reviewer":

**Satisfies:**
- *Separates product issues from implementation bugs* — F1 is flagged as a product-facing defect (silent track) with an implementation cause; F2 as pure process; roadmap features explicitly excluded.
- *Concrete evidence + reproducible steps* — every finding cites file:line or a git command; Section 4 gives repeatable inspection + repro steps.
- *Release blockers vs polish* — Section 5 names exactly two blockers; F3–F8 and Section 7 are explicitly non-blocking.
- *Mobile/browser/network/Spotify awareness* — covered across F1/F5 and Section 6.
- *States uncertainty honestly* — Section 3 separates verified facts from unverified assumptions; the mobile stall is openly marked not-reproduced.
- *Says what to park* — Section 7.
- *Findings chef can turn into manager briefs* — F1 maps directly to the external auditor's bounded "Item 2"; F2 is a one-shot chef action.
- *Did not patch code, did not commit, did not approve manager work* — inspect-only honored.

**Partial / limits:**
- I could not reproduce the live mobile failure or re-measure TTS/Spotify playback quality — same hardware limitation the external auditor hit. I relied on code + handoffs and flagged it rather than overclaiming.
- I did not do a per-commit content audit; F2 (EOL churn) currently makes that low-value, which is itself part of the finding.

**Note on this report file:** producing this report is the required trial output. I created it as a *new* deliverable document and changed no product code or existing files. If the boss/chef prefer it not live under `docs/handoffs/`, it can be moved or deleted — I did not commit it.
