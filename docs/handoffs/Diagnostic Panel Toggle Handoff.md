# Diagnostic Panel Toggle Handoff

## Purpose
The Spotify diagnostic panel is useful for mobile testing but should not always display during normal listening. This handoff adds a developer toggle: the panel is hidden by default, with a small unobtrusive "Diag" button in the ON AIR header rail to show/hide it. Toggle state persists across page reloads via localStorage.

## Strategy-Layer Gate Correction

Owner validation found two issues with the first RUG implementation:

- On desktop, the diagnostic panel could still block the Skip button if `localStorage` had diagnostics enabled.
- On mobile, the fixed top-right "Diag" button was not discoverable, likely because it collided with browser/system chrome.

Correction applied by the gate layer:

- Moved the button from a fixed top-right position into the existing ON AIR header rail.
- When diagnostics are disabled, the diagnostic DOM element is removed instead of only hidden.
- Kept the same `localStorage` key and the same diagnostic fields.

## Files Changed

| File | Change | Lines | Summary |
|---|---|---|---|
| `resonova/web/player.js` | +4 changes | ~29 lines added | Constructor: `_diagVisible` from localStorage. New `_createDiagToggle()` method. `_showState()` integrates toggle button into the ON AIR badge. `_renderDiagnostics()` guarded behind toggle. |
| `resonova/web/styles.css` | +1 block | ~29 lines appended | `.diag-toggle` + `.diag-toggle.on` CSS rules for the ON AIR header rail |
| `resonova/web/index.html` | NOT modified | - | - |

## How It Works

### Default State
- Diagnostic panel is **hidden**. No diagnostic overlay visible.
- Small semi-transparent "Diag" button beside the ON AIR badge in the header.

### Toggle Behavior
- **Click "Diag" button**: diag panel appears (all fields + Refresh button work as before), button turns accent-colored
- **Click again**: diag panel hides, button returns to subtle state
- **Page reload**: toggle state read from `localStorage` key `resonova:diag` ('1' = visible, absent/other = hidden)

### localStorage Key
- Key: `resonova:diag`
- Values: `'1'` (visible) or `'0'` (hidden)
- Read in constructor on every page load

## Technical Details

### player.js Changes
1. **Constructor (line 31)**: `this._diagVisible = localStorage.getItem('resonova:diag') === '1';`
2. **`_createDiagToggle()` (lines 51-66)**: Creates `<button id="diag-toggle">`, click handler toggles `_diagVisible`, writes localStorage, toggles `.on` CSS class, calls `_renderDiagnostics(null)`
3. **`_showState()` (lines 693-697)**: When entering playing state, appends toggle button to `#on-air-badge` (guarded against duplicates)
4. **`_renderDiagnostics()` guard (lines 485-490)**: Top guard: if `!_diagVisible`, remove `_diagEl`, clear the reference, and return

### styles.css Addition
```css
.diag-toggle {
  display: inline-flex;
  margin-left: 0.35rem;
  /* semi-transparent, mono font, small border */
  opacity: 0.5;
}
.diag-toggle.on {
  color: var(--accent);
  border-color: var(--accent-mid);
  opacity: 0.9;
}
```

## Validation Results
- `node --check resonova/web/player.js` - PASS
- `git diff -- resonova/web/index.html` - zero output
- All 12 acceptance criteria PASS
- No playback logic changed
- No diagnostic fields removed
- No new dependencies

## Testing Steps

### Desktop
1. Start server: `python -m uvicorn resonova.server:app --host 127.0.0.1 --port 8765`
2. Open `http://127.0.0.1:8765` in browser
3. Authenticate with Spotify, generate an episode
4. Verify: playing screen shows NO diagnostic panel (hidden by default)
5. Verify: small "Diag" button visible beside the ON AIR badge
6. Click "Diag": diagnostic panel appears with all fields + Refresh button
7. Verify: "Diag" button now shows accent color
8. Click "Diag" again: panel hides
9. Reload page, authenticate, start episode: panel should remain in last state (hidden or visible)

### Mobile
1. Navigate to `https://buttking.tail15ea24.ts.net:8765`
2. Same steps as desktop
3. Verify toggle works with touch

### localStorage Verification
```javascript
// In browser console:
localStorage.getItem('resonova:diag')  // '1' when visible, '0' when hidden

// Force show:
localStorage.setItem('resonova:diag', '1')
// Reload page

// Force hide:
localStorage.removeItem('resonova:diag')
// Reload page
```

## Rollback

To remove the toggle (revert diagnostic panel to always-visible):
```bash
git checkout HEAD -- resonova/web/player.js resonova/web/styles.css
```

The toggle is fully self-contained. Removing these two file changes restores the previous always-visible diagnostic panel.

## Design Decisions
- **Hidden by default**: diagnostic panel is developer tooling, not user-facing UI
- **localStorage over sessionStorage**: toggle state survives browser restarts, so the owner doesn't need to re-enable it every session
- **Button appended to `#on-air-badge`**: keeps the control inside existing header chrome and avoids mobile browser/system UI collisions
- **No fixed positioning for button**: avoids blocking playback controls and makes placement predictable on desktop and mobile
- **Toggle calls `_renderDiagnostics(null)`**: ensures panel content is up-to-date when shown, even if no SDK event has fired since last hide
