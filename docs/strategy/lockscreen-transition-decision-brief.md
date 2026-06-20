# Lockscreen Transition Decision Brief

## Boss Report

After mobile lockscreen hardening, the owner retested and found:

- The transition-to-next-segment problem still persists while the phone is locked.
- `auth_error` after idle appears to be a separate issue from transition.
- Active-screen transition can work even when the idle/auth symptom exists.

## Corrected Diagnosis

The current Resonova playback architecture requires page JavaScript at segment boundaries:

- HTML commentary segment ends -> `audio.onended` calls `_playNext()`.
- Spotify music segment ends -> Spotify SDK `player_state_changed` or a JavaScript deadline calls `_playNext()`.
- `_playNext()` then starts the next commentary or Spotify segment.

When a mobile browser freezes/suspends the page during lockscreen, JavaScript timers and SDK messages may not run. That means no patch based on `setTimeout`, `player_state_changed`, or regular page JavaScript can guarantee automatic segment transitions while the page remains frozen.

The previous hardening patch is still useful for:

- reducing long fade delays after resume,
- preventing some token callback deadlocks,
- advancing after the page wakes if the timer fires then.

But it does not create true locked-screen background execution.

## Separate Problems

### Problem A: Auth Error After Idle

This is a recoverability problem. The user should not have to restart from the beginning.

Recommended direction:

- persist current episode/session state in `localStorage`,
- show a resume affordance after reload/auth recovery,
- restore near the previous segment,
- keep token fallback, but do not rely on it as the only protection.

### Problem B: Segment Transition While Locked

This is an architecture/browser-background problem.

Recommended direction:

- add foreground resume reconciliation so returning to the page catches up cleanly,
- add Media Session controls so the owner can manually skip from the lockscreen,
- do not promise fully automatic interleaved commentary/music transitions while locked unless the architecture changes.

## Architecture Options

| Option | What It Solves | Tradeoff |
|---|---|---|
| Foreground resume reconciliation | Recovers when user unlocks or returns | Does not transition while still locked |
| Media Session next/play/pause | Gives lockscreen controls | Requires queue/history work for previous |
| PWA install | Better app feel, less browser chrome | Does not guarantee background JS execution |
| Native mobile app | True background audio control possible | Much larger scope |
| Single continuous audio source | Reliable lockscreen continuity | Cannot legally/technically include full Spotify tracks from Web Playback SDK |
| Commentary-only/offline episode | Reliable audio file playback | Loses full Spotify music interleaving |

## Next Recommended Work

Do not assign another "make lockscreen transition automatic" patch without changing architecture.

Next bounded implementation should be:

1. Resume-state persistence and recovery after auth/reload.
2. Foreground resume reconciliation.
3. Media Session next/play/pause as a separate product-quality milestone.

