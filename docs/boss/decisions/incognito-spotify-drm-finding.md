# Finding: Chrome Incognito Blocks Spotify Web Playback SDK

Date: 2026-06-25  
Type: Incident finding / platform limitation  
Severity: Medium (affects incognito users only; normal browsing unaffected)

---

## The Mystery

Phone B (Android 10, Chrome, Redmi K-series) was experiencing Spotify playback failure on
Resonova. The diagnostic panel showed:

```
EME          widevine-fail
Player built yes
connect()    success
ready        no
init_error   Failed to initialize player
```

`connect()` returned success but `ready` never fired. The Spotify Web Playback SDK was
connecting but never registering the device.

This was puzzling because:
- The exact same Spotify account worked fine on Phone A (Android, Chrome)
- PC worked
- The cast had worked on Phone B previously

Multiple code investigations were carried out over one session:
- Removed a false-positive "Browser Blocked" state that incorrectly treated widevine-fail
  as a permanent capability failure
- Removed `enableMediaSession: true` from Spotify Player constructor (caused real
  initialization_error on some Android browsers)
- Restored auto-connect inside `_initSpotifyPlayer` (tired-chef had deferred it to
  gesture-only, breaking the initialization sequence)
- Restored direct `connect()` call in recovery (a guard was silently no-oping the reconnect
  attempt)
- Each fix improved the situation but `ready` still refused to fire on Phone B

The EME `widevine-fail` was visible throughout, but on Phone A it also showed up and
yet playback worked. This created a red herring — we almost concluded Phone B was a
permanently unsupported device.

## The Reveal

The boss discovered Phone B had always been running in **Chrome incognito mode**.  
Switching Phone B to normal Chrome → worked immediately, same as Phone A.

## Root Cause

**Chrome on Android disables Widevine EME in incognito mode.**

This is a deliberate Chrome privacy policy: DRM/Widevine requires persistent identifiers
that could fingerprint users across sessions. Incognito blocks this to protect privacy.

Cascade:
1. Incognito Chrome → `requestMediaKeySystemAccess('com.widevine.alpha', ...)` throws
2. EME probe records `widevine-fail`
3. Spotify Web Playback SDK calls EME internally during `connect()`
4. EME blocked → SDK fires `initialization_error: Failed to initialize player`
5. `ready` never fires → no device ID → Spotify playback impossible

This is a Chrome platform policy, not a Resonova code bug. It cannot be fixed in code.

## Why It "Worked Before"

The old `initialization_error` handler (pre tired-chef changes) only logged the error and
showed the small SDK banner. Audio commentary segments (`.mp3` via `<audio>`) played
independently of Spotify SDK state. The user experienced: commentary plays, music tracks
silently fail or skip. Perceived as "working" because the main content (AI commentary)
was audible.

The tired-chef structural changes added aggressive recovery logic that BLOCKED the cast
on Spotify failure rather than letting commentary continue. This made the breakage
obvious for the first time.

## Fix Applied

**Option A: Contextual warning message.**

When `initialization_error` fires AND `eme:widevine-fail` is detected, the SDK warning
banner now reads:

> *"Spotify is unavailable — protected content is blocked in this browser session.  
> If you're in a private or incognito window, switch to a regular browser window."*

Previously it showed the generic: *"Spotify Premium is required for the Web Playback SDK."*

File changed: `resonova/web/player.js` — `initialization_error` listener.

## Platform Behavior Reference

| Browser / Mode | Widevine EME | Spotify SDK |
|---|---|---|
| Chrome (normal) Android | ✅ supported | ✅ works |
| Chrome (incognito) Android | ❌ blocked by policy | ❌ init_error |
| Chrome Desktop | ✅ supported | ✅ works |
| Firefox Android | ✅ (Widevine L3) | ✅ works |
| Samsung Internet | ✅ | ✅ works |
| In-app WebView (some) | ❌ | ❌ init_error |

## Diagnostic Signature

If a user reports Spotify not working, look for this combination in the diag panel:

```
EME       widevine-fail
connect() success
ready     no
init_error Failed to initialize player
auth_error -
acct_error no
```

`connect(): success` + `ready: no` + `widevine-fail` + no auth/account error =
**almost certainly incognito or DRM-blocked browser session**.

The new warning message now surfaces this directly to the user.

## Related Files

- `resonova/web/player.js` — `_probeEncryptedMediaSupport()`, `initialization_error` listener
- `docs/boss/decisions/mobile-playback-hardening-brief.md` — related mobile reliability work
