/**
 * Resonova player — interleaves Spotify Web Playback SDK with HTML audio commentary.
 *
 * Queue format: [{type: "audio"|"spotify", url?: string, uri?: string}]
 * Playback proceeds sequentially through the queue; each item triggers the next
 * via an end-of-playback event (audio.onended for HTML audio, state change for Spotify).
 */

const STEP_MAP = {
  fetch: 'step-fetch',
  context: 'step-fetch',
  research: 'step-research',
  script: 'step-script',
  tts: 'step-tts',
};

class ResonovaPlayer {
  constructor() {
    this.queue = [];
    this.playedItems = [];
    this.playbackTimeline = [];
    this.currentIndex = -1;
    this.totalItems = 0;
    this.completedItems = 0;
    this.deviceId = null;
    this._cachedToken = null;
    this.spotifyPlayer = null;
    this._segmentDeadline = null;
    this.audioEl = document.getElementById('resonova-audio');
    this.currentItem = null;
    this._episodeId = null;
    this._segmentType = '';
    // Prevents double-firing of playNext on track end
    this._trackEndFired = false;
    // True once the server has finished synthesizing all tracks
    this._generationComplete = true;
    this._diagEl = null; // diagnostic overlay, lazily created
    this._diagVisible = localStorage.getItem('resonova:diag') === '1';
    this._resumeChecked = false;
    this._lifecycle = {
      sdkLoaded: false,
      playerConstructed: false,
      connectCalled: false,
      connectResult: null,
      ready: false,
      deviceId: null,
      notReady: false,
      initError: null,
      authError: null,
      accountError: false,
      playbackError: null,
      autoplayFailed: false,
      isSecureContext: window.isSecureContext,
      protocol: location.protocol,
      userAgent: navigator.userAgent,
    };

    this._spotifyUnhealthy = false;
    this._spotifyRecovering = false;
    this._spotifyRecoveryPromise = null;
    this._spotifyRecoveryFailed = false;
    this._spotifyRecoveryFailureCount = 0;
    this._spotifyReloadRecommended = false;

    this._isPaused = false;
    this._nowPlayingTitle = '';
    this._nowPlayingArtist = '';
    this._pendingEpisodeFocusId = null;
    this._episodesNeedRefresh = false;
    this._lastConnectedRefresh = 0; // timestamp of last _loadEpisodes call from _showState
    this._metaPrefetch = new Set(); // in-flight Spotify metadata prefetch guard (keyed by URI)
    this._missingTailRecoveryPromise = null;
    this._pendingUnlockItem = null; // Spotify segment deferred after hidden-page Spotify Connect failure
    this._activeGenerationId = null;
    this._activeGenerationName = '';
    this._activeGenerationTagline = '';
    this._activeGenerationSource = '';
    this._generationSaveCheck = null;
    this._sseWatchdog = null;
    this._lastSSEEventTime = 0;
    this._episodes = [];

    // ── Replay tracking (saved-cast replays only) ──────────────────────────
    this._replaySessionId = null;
    this._replayMeaningfulSent = false;
    this._replaySavedEpisodeId = null;
    this._replayTotalSegments = 0;

    // ── Observability ring buffer (max 50 entries) ─────────────────────────
    this._obsTimeline = [];
    this._deviceGeneration = 0;
    this._deviceAcquiredAt = null;

    // Record initial network state
    this._obsRecord('online:init', navigator.onLine ? 'online' : 'offline');

    window.addEventListener('online', () => {
      this._obsRecord('online', '');
      this._clearNetworkStatus();
    });
    window.addEventListener('offline', () => {
      this._obsRecord('offline', '');
      this._updateNetworkStatus('offline');
    });

    window.addEventListener('pageshow', (e) => {
      this._obsRecord('pageshow', e.persisted ? 'persisted=true' : 'persisted=false');
    });
    window.addEventListener('pagehide', (e) => {
      this._obsRecord('pagehide', e.persisted ? 'persisted=true' : 'persisted=false');
    });

    // Foreground reconciliation: check Spotify state when page becomes visible
    document.addEventListener('visibilitychange', () => {
      this._obsRecord('visibilitychange', document.visibilityState);
      if (document.visibilityState !== 'visible') return;

      // Req 2: Auto-resume a Spotify segment that was deferred while the page was hidden.
      // This fires when the user unlocks their phone or returns to the tab.
      const pending = this._pendingUnlockItem;
      if (pending) {
        this._pendingUnlockItem = null;
        this._obsRecord('play:spotify:unlock-resume', pending.uri.slice(-24));
        this._setNowPlaying('Spotify waiting for phone unlock', 'Reconnecting…');
        this._recoverSpotifySession().then(success => {
          if (success) {
            this._playSpotifyTrack(pending);
          } else {
            // Recovery failed — keep Skip Music visible as the user's exit path
            this._obsRecord('play:spotify:unlock-recovery-fail', '');
            this._setNowPlaying('Spotify waiting for phone unlock', 'Unlock your phone to resume or use Skip Music');
            this._spotifyRecoveryFailed = true;
            this._updateSkipMusicButton();
          }
        });
        return;
      }

      if (!this.currentItem) return;
      this._reconcileAfterBackground();
    });
  }

  _obsRecord(event, detail = '') {
    this._obsTimeline.push({ t: Date.now(), event, detail: String(detail).slice(0, 120) });
    if (this._obsTimeline.length > 50) this._obsTimeline.shift();
    if (this._diagVisible) this._renderDiagnostics(null);
  }

  _isSpotifyHealthy() {
    return !!this.spotifyPlayer &&
      !!this.deviceId &&
      !this._lifecycle.authError &&
      !this._lifecycle.playbackError &&
      !this._lifecycle.notReady &&
      !this._spotifyUnhealthy;
  }

  _markSpotifyUnhealthy(reason, message) {
    this._spotifyUnhealthy = true;
    this._spotifyRecoveryFailed = false;
    if (reason === 'auth' || reason === 'authentication_error') {
      const baseMsg = message || 'authentication_error';
      this._lifecycle.authError = !navigator.onLine ? `${baseMsg} (offline)` : baseMsg;
    }
    if (reason === 'playback' || reason === 'playback_error') {
      this._lifecycle.playbackError = message || 'playback_error';
    }
    if (reason === 'not_ready') {
      this.deviceId = null;
      this._lifecycle.ready = false;
      this._lifecycle.deviceId = null;
      this._lifecycle.notReady = message || true;
    }
    this._renderDiagnostics(null);
    this._updateRecoveryControl();
    this._updateNowPlayingMiniPanel();
  }

  _clearSpotifyUnhealthy() {
    this._spotifyUnhealthy = false;
    this._spotifyRecoveryFailed = false;
    this._lifecycle.authError = null;
    this._lifecycle.playbackError = null;
    this._lifecycle.notReady = false;
    this._renderDiagnostics(null);
    this._updateRecoveryControl();
    this._updateNowPlayingMiniPanel();
  }

  _recommendSpotifyReload(reason = '') {
    this._spotifyReloadRecommended = true;
    this._spotifyRecoveryFailed = true;
    this._setNowPlaying('Spotify session stale', 'Reload player to reconnect Spotify');
    this._obsRecord('recovery:reload-recommended', reason.slice(0, 80));
    this._updateRecoveryControl();
  }

  _waitForSpotifyDevice(timeoutMs) {
    if (this.deviceId) return Promise.resolve(this.deviceId);
    return new Promise(resolve => {
      const started = Date.now();
      const id = setInterval(() => {
        if (this.deviceId) {
          clearInterval(id);
          resolve(this.deviceId);
        } else if (Date.now() - started >= timeoutMs) {
          clearInterval(id);
          resolve(null);
        }
      }, 100);
    });
  }

  async _recoverSpotifySession() {
    if (this._spotifyRecovering) return this._spotifyRecoveryPromise;

    this._spotifyRecovering = true;
    this._spotifyRecoveryFailed = false;
    this._updateRecoveryControl();

    this._spotifyRecoveryPromise = (async () => {
      try {
        this._obsRecord('recovery:start', '');
        const { token } = await this._apiFetch('/auth/token');
        if (!token) throw new Error('No Spotify token');
        this._cachedToken = token;

        // First try to reconnect existing player.
        if (this.spotifyPlayer) {
          try { await this.spotifyPlayer.connect(); } catch (_) { }
        }

        let deviceId = await this._waitForSpotifyDevice(3000);

        // If reconnect did not produce a device, rebuild once.
        if (!deviceId) {
          try { this.spotifyPlayer?.disconnect(); } catch (_) { }
          this.spotifyPlayer = null;
          this.deviceId = null;
          this._lifecycle.ready = false;
          this._lifecycle.deviceId = null;
          await this._initSpotifyPlayer();
          deviceId = await this._waitForSpotifyDevice(5000);
        }

        if (!deviceId) throw new Error('Spotify device did not become ready');
        const connectReady = await this._waitForSpotifyConnectDevice(token, deviceId, 12000);
        if (!connectReady) throw new Error('Spotify device is ready in SDK but not visible to Spotify Connect');

        await this._transferPlayback(deviceId, token);

        this._spotifyUnhealthy = false;
        this._spotifyRecoveryFailed = false;
        this._spotifyRecoveryFailureCount = 0;
        this._spotifyReloadRecommended = false;
        this._lifecycle.authError = null;
        this._lifecycle.playbackError = null;
        this._lifecycle.notReady = false;
        this._lifecycle.ready = true;
        this._lifecycle.deviceId = deviceId;
        this._obsRecord('recovery:success', '');
        this._renderDiagnostics(null);
        return true;
      } catch (err) {
        console.warn('[Resonova] Spotify recovery failed:', err);
        this._spotifyRecoveryFailed = true;
        this._spotifyRecoveryFailureCount += 1;
        const message = err?.message || '';
        const connectInvisible = message.includes('not visible to Spotify Connect');
        if (connectInvisible || this._spotifyRecoveryFailureCount >= 2) {
          this._recommendSpotifyReload(
            connectInvisible ? 'connect-device-invisible' : String(this._spotifyRecoveryFailureCount)
          );
        }
        this._obsRecord('recovery:fail', message.slice(0, 80));
        this._renderDiagnostics(null);
        return false;
      } finally {
        this._spotifyRecovering = false;
        this._spotifyRecoveryPromise = null;
        this._updateRecoveryControl();
      }
    })();

    return this._spotifyRecoveryPromise;
  }

  _updateRecoveryControl() {
    const btn = document.getElementById('recover-spotify-btn');
    if (!btn) return;

    // Wire listener once
    if (!btn._wired) {
      btn.addEventListener('click', () => {
        this.recoverSpotify();
      });
      btn._wired = true;
    }

    const isVisible = this._spotifyUnhealthy || this._spotifyRecoveryFailed || this._spotifyReloadRecommended;
    btn.style.display = isVisible ? '' : 'none';

    if (this._spotifyRecovering) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 3a7 7 0 0 0-7 7h2a5 5 0 1 1 5 5v2a7 7 0 0 0 0-14z" fill="currentColor"/>
          <path d="M1.5 10l2.5-3 2.5 3h-5z" fill="currentColor"/>
        </svg>
        Recovering...
      `;
    } else if (this._spotifyReloadRecommended) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 3a7 7 0 0 0-7 7h2a5 5 0 1 1 5 5v2a7 7 0 0 0 0-14z" fill="currentColor"/>
          <path d="M1.5 10l2.5-3 2.5 3h-5z" fill="currentColor"/>
        </svg>
        Reload Player
      `;
    } else {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 3a7 7 0 0 0-7 7h2a5 5 0 1 1 5 5v2a7 7 0 0 0 0-14z" fill="currentColor"/>
          <path d="M1.5 10l2.5-3 2.5 3h-5z" fill="currentColor"/>
        </svg>
        Recover Spotify
      `;
    }
    this._updateSkipMusicButton();
  }

  async recoverSpotify() {
    if (this._spotifyReloadRecommended) {
      this._obsRecord('recovery:reload-click', '');
      location.reload();
      return;
    }
    if (!navigator.onLine) {
      this._obsRecord('recovery:blocked', 'offline');
      this._setNowPlaying('Spotify unavailable offline', 'Use Next to continue commentary');
      this._updateSkipMusicButton();
      return;
    }
    const success = await this._recoverSpotifySession();
    if (success && this.currentItem && this.currentItem.type === 'spotify') {
      await this._playSpotifyTrack(this.currentItem);
    }
  }

  // ──────────────────────────────────────────────
  // Play / Pause / Resume
  // ──────────────────────────────────────────────

  pause() {
    if (!this.currentItem || this._isPaused) return;
    if (this.currentItem.type === 'audio') {
      this.audioEl.pause();
    } else if (this.currentItem.type === 'spotify') {
      if (this._segmentDeadline) {
        clearTimeout(this._segmentDeadline);
        this._segmentDeadline = null;
      }
      try { this.spotifyPlayer?.pause(); } catch (_) {}
    }
    this._isPaused = true;
    document.getElementById('waveform')?.classList.add('paused');
    this._updatePlayPauseButton();
    this._setMediaSessionPlaybackState('paused');
    this._updateNowPlayingMiniPanel();
  }

  resume() {
    if (!this.currentItem || !this._isPaused) return;
    if (this.currentItem.type === 'audio') {
      this.audioEl.play()
        .then(() => {
          this._isPaused = false;
          document.getElementById('waveform')?.classList.remove('paused');
          this._updatePlayPauseButton();
          this._setMediaSessionPlaybackState('playing');
          this._updateNowPlayingMiniPanel();
        })
        .catch(err => {
          console.error('[Resonova] Audio resume failed:', err);
        });
      return;
    } else if (this.currentItem.type === 'spotify') {
      if (!this._isSpotifyHealthy()) {
        this._recoverSpotifySession().then(success => {
          if (success) {
            try { this.spotifyPlayer?.resume(); } catch (_) {}
            this._isPaused = false;
            document.getElementById('waveform')?.classList.remove('paused');
            this._updatePlayPauseButton();
            this._setMediaSessionPlaybackState('playing');
            this._updateNowPlayingMiniPanel();
          }
        });
        return;
      }
      try { this.spotifyPlayer?.resume(); } catch (_) {}
    }
    this._isPaused = false;
    document.getElementById('waveform')?.classList.remove('paused');
    this._updatePlayPauseButton();
    this._setMediaSessionPlaybackState('playing');
    this._updateNowPlayingMiniPanel();
  }

  togglePlayPause() {
    if (this._isPaused) {
      this.resume();
    } else {
      this.pause();
    }
  }

  _updatePlayPauseButton() {
    const btn = document.getElementById('play-pause-btn');
    if (!btn) return;
    btn.disabled = !this.currentItem;
    if (this._isPaused) {
      btn.setAttribute('aria-label', 'Resume');
      btn.title = 'Resume';
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M5 4l10 6-10 6V4z" fill="currentColor"/>
        </svg>
        Resume
      `;
    } else {
      btn.setAttribute('aria-label', 'Pause');
      btn.title = 'Pause';
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="5" y="4" width="3.5" height="12" rx="1" fill="currentColor"/>
          <rect x="11.5" y="4" width="3.5" height="12" rx="1" fill="currentColor"/>
        </svg>
        Pause
      `;
    }
  }

  // ──────────────────────────────────────────────
  // Media Session API
  // ──────────────────────────────────────────────

  _initMediaSessionHandlers() {
    if (!('mediaSession' in navigator)) return;
    const safe = (action, handler) => {
      try { navigator.mediaSession.setActionHandler(action, handler); } catch (_) {}
    };
    safe('play', () => this.resume());
    safe('pause', () => this.pause());
    safe('nexttrack', () => this.skip());
    safe('previoustrack', () => this.previous());
  }

  _updateMediaSession(title, artist) {
    if (!('mediaSession' in navigator)) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: title || 'Resonova',
        artist: artist || '',
        album: 'Resonova',
      });
    } catch (_) {}
  }

  _setMediaSessionPlaybackState(state) {
    if (!('mediaSession' in navigator)) return;
    try {
      navigator.mediaSession.playbackState = state;
    } catch (_) {}
  }

  _createDiagToggle() {
    const btn = document.createElement('button');
    btn.id = 'diag-toggle';
    btn.className = 'diag-toggle';
    btn.textContent = 'Diag';
    btn.title = 'Toggle Spotify diagnostic panel';
    btn.addEventListener('click', () => {
      this._diagVisible = !this._diagVisible;
      localStorage.setItem('resonova:diag', this._diagVisible ? '1' : '0');
      btn.classList.toggle('on', this._diagVisible);
      this._renderDiagnostics(null);
    });
    if (this._diagVisible) btn.classList.add('on');
    return btn;
  }

  _saveResumeState() {
    const hasIncompleteProgress = this.totalItems > 0 && this.completedItems < this.totalItems;
    if (!this._episodeId || (!this.queue.length && !this.currentItem && !hasIncompleteProgress)) {
      // Nothing meaningful to resume
      localStorage.removeItem('resonova:resume');
      return;
    }
    const state = {
      episodeId: this._episodeId,
      queue: this.queue.slice(),
      playedItems: this.playedItems.slice(),
      playbackTimeline: this.playbackTimeline.slice(),
      currentIndex: this.currentIndex,
      currentItem: this.currentItem ? { ...this.currentItem } : null,
      completedItems: this.completedItems,
      totalItems: this.totalItems,
      segmentType: this._segmentType,
      ts: Date.now(),
    };
    try {
      localStorage.setItem('resonova:resume', JSON.stringify(state));
    } catch { /* quota exceeded, ignore */ }
  }

  _clearResumeState() {
    localStorage.removeItem('resonova:resume');
  }

  _checkResumeState() {
    try {
      const raw = localStorage.getItem('resonova:resume');
      if (!raw) return null;
      const state = JSON.parse(raw);
      // Expire after 30 minutes
      if (Date.now() - state.ts > 30 * 60 * 1000) {
        localStorage.removeItem('resonova:resume');
        return null;
      }
      return state;
    } catch {
      localStorage.removeItem('resonova:resume');
      return null;
    }
  }

  _showResumePrompt(state) {
    // Create a resume card in the connected state
    const container = document.getElementById('state-connected');
    if (!container) return;

    // Remove any existing resume card
    const existing = document.getElementById('resume-card');
    if (existing) existing.remove();

    const card = document.createElement('div');
    card.id = 'resume-card';
    card.innerHTML = `
        <div style="margin:1rem 0;padding:0.75rem 1rem;background:var(--panel);border:1px solid var(--accent-mid);border-radius:4px;display:flex;align-items:center;justify-content:space-between;gap:1rem;">
            <div style="font-size:0.75rem;color:var(--cream-mid);">
                <span style="color:var(--accent);font-weight:600;">Unfinished episode</span>
                <span style="color:var(--cream-faint);margin-left:0.5rem;">Segment ${state.completedItems}/${state.totalItems}</span>
            </div>
            <button id="resume-btn" style="padding:0.35rem 0.75rem;background:var(--accent);color:#fff;border:none;border-radius:3px;font-family:var(--font-mono);font-size:0.65rem;cursor:pointer;white-space:nowrap;">Resume</button>
            <button id="resume-dismiss" style="padding:0.35rem 0.5rem;background:transparent;border:1px solid var(--panel-border);border-radius:3px;color:var(--cream-faint);font-size:0.65rem;cursor:pointer;">✕</button>
        </div>`;

    // Keep unfinished playback in the episode/library area so it appears
    // beside saved casts instead of as a separate page-level alert.
    const episodesSection = document.getElementById('section-episodes');
    const episodeList = document.getElementById('past-episodes');
    if (episodesSection && episodeList) {
      episodesSection.classList.add('loaded');
      episodesSection.insertBefore(card, episodeList);
    } else {
      container.insertBefore(card, container.firstChild);
    }

    // Bind events
    card.querySelector('#resume-btn').addEventListener('click', () => {
      card.remove();
      this._resumePlayback(state);
    });
    card.querySelector('#resume-dismiss').addEventListener('click', () => {
      card.remove();
      this._clearResumeState();
    });
  }

  async _resumePlayback(state) {
    this._episodeId = state.episodeId;

    const timeline = Array.isArray(state.playbackTimeline)
      ? [...state.playbackTimeline]
      : [
        ...(Array.isArray(state.playedItems) ? state.playedItems : []),
        ...(state.currentItem ? [state.currentItem] : []),
        ...state.queue,
      ];
    const startIndex = Math.max(0, state.currentItem
      ? (state.currentIndex ?? (state.playedItems?.length || 0))
      : (state.completedItems ?? state.currentIndex ?? (state.playedItems?.length || 0)));
    let resolvedTimeline = timeline;
    let queue = timeline.slice(startIndex);

    if (!queue.length && state.completedItems < state.totalItems) {
      const saved = await this._loadSavedEpisode(state.episodeId);
      if (saved?.queue?.length > state.completedItems) {
        resolvedTimeline = saved.queue;
        queue = saved.queue.slice(state.completedItems);
      }
    }

    if (!queue.length && state.completedItems < state.totalItems) {
      this._showState('playing');
      this.completedItems = state.completedItems;
      this.totalItems = state.totalItems;
      this.playedItems = Array.isArray(state.playedItems) ? [...state.playedItems] : [];
      this.playbackTimeline = resolvedTimeline;
      this.currentIndex = Math.max(0, state.completedItems - 1);
      this.currentItem = null;
      this.queue = [];
      this._setNowPlaying('Episode paused', 'Saved cast is still being finalized.');
      document.getElementById('next-up').textContent = 'Return to Library or try Resume again shortly.';
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
      return;
    }

    this._startPlayback(queue, { timeline: resolvedTimeline });
    this.playedItems = Array.isArray(state.playedItems) ? [...state.playedItems] : [];

    // Mark completedItems as already passed (minus current item)
    this.completedItems = Math.max(0, state.completedItems - 1);
    this.totalItems = state.totalItems || queue.length;
    this._segmentType = state.segmentType || '';
    this._updateProgress();
    this._updateSkipButton();
    this._saveResumeState();
  }

  async _loadSavedEpisode(episodeId) {
    if (!episodeId) return null;
    try {
      const ep = await this._apiFetch(`/api/episodes/${episodeId}`);
      try {
        localStorage.setItem(`resonova:episode:${episodeId}`, JSON.stringify({ ts: Date.now(), ep }));
      } catch { /* quota exceeded */ }
      return ep;
    } catch {
      try {
        const raw = localStorage.getItem(`resonova:episode:${episodeId}`);
        return raw ? JSON.parse(raw).ep || null : null;
      } catch {
        return null;
      }
    }
  }

  async _recoverMissingEpisodeTail() {
    if (this._missingTailRecoveryPromise) return this._missingTailRecoveryPromise;
    this._missingTailRecoveryPromise = (async () => {
      this._obsRecord('queue:missing-tail', `${this.completedItems}/${this.totalItems}`);
      const ep = await this._loadSavedEpisode(this._episodeId);
      if (!ep?.queue?.length || ep.queue.length <= this.completedItems) return false;

      this.playbackTimeline = ep.queue;
      this.queue = ep.queue.slice(this.completedItems);
      this.totalItems = Math.max(this.totalItems, ep.queue.length);
      this.currentIndex = Math.max(0, this.completedItems - 1);
      this.currentItem = null;
      this._setNowPlaying('Continuing episode', 'Recovered remaining saved segments.');
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
      return this.queue.length > 0;
    })();

    try {
      return await this._missingTailRecoveryPromise;
    } finally {
      this._missingTailRecoveryPromise = null;
    }
  }

  _parkIncompleteEpisode() {
    this._obsRecord('queue:incomplete-parked', `${this.completedItems}/${this.totalItems}`);
    this._setNowPlaying('Episode interrupted', 'Resume is available in Library.');
    this._setSegmentType('');
    document.getElementById('next-up').textContent = 'Return to Library to resume this cast.';
    document.getElementById('on-air-badge').classList.remove('active');
    document.getElementById('waveform').classList.add('paused');
    this._isPaused = true;
    this._updatePlayPauseButton();
    this._saveResumeState();
    const state = this._checkResumeState();
    if (state) this._showResumePrompt(state);
  }

  async _reconcileAfterBackground() {
    if (this.currentItem?.type === 'spotify' && !this._isSpotifyHealthy()) {
      console.log('[Resonova] Spotify is unhealthy on foreground return, triggering recovery...');
      const success = await this._recoverSpotifySession();
      if (success) {
        console.log('[Resonova] Spotify recovery succeeded on foreground return, retrying playback...');
        await this._playSpotifyTrack(this.currentItem);
      } else {
        console.warn('[Resonova] Spotify recovery failed on foreground return.');
      }
      return;
    }

    // If auth_error exists but we have a resume state, don't consider it fatal
    if (this._lifecycle.authError && this._episodeId) {
      console.log('[Resonova] Auth error after background — resume state exists, not fatal');
      this._saveResumeState();
    }

    // If current item is Spotify, query current state
    if (this.currentItem?.type !== 'spotify' || !this.spotifyPlayer) return;

    try {
      const state = await this.spotifyPlayer.getCurrentState();
      if (!state) return;

      // If track appears ended (paused at start with history), advance
      if (state.paused && state.position < 2000 && state.track_window?.previous_tracks?.length > 0) {
        if (!this._trackEndFired) {
          console.log('[Resonova] Track appears ended after background — advancing');
          this._trackEndFired = true;
          this._fadeSpotifyVolume(_SPOTIFY_VOLUME, 0, _CROSSFADE_MS).then(() => this._playNext());
        }
      }

      // Refresh diagnostics with latest state
      this._renderDiagnostics(state);
    } catch {
      // getCurrentState can fail if SDK is disconnected — not fatal
    }
  }

  // ──────────────────────────────────────────────
  // Initialisation
  // ──────────────────────────────────────────────

  async init() {
    if (!navigator.onLine) {
      this._updateNetworkStatus('offline');
    }
    let authData;
    try {
      authData = await this._apiFetch('/auth/token');
    } catch (err) {
      if (err.kind === 'offline' || err.kind === 'network') {
        history.replaceState({ resonovaState: 'connected' }, '', location.pathname + location.search);
        this._showState('connected');
        this._loadEpisodes();
        this._initHistoryNav();
        this._initMediaSessionHandlers();
        return;
      }
      throw err;
    }
    const { authenticated } = authData;
    if (!authenticated) {
      this._showState('landing');
      history.replaceState({ resonovaState: 'landing' }, '', location.pathname + location.search);
      return;
    }
    history.replaceState({ resonovaState: 'connected' }, '', location.pathname + location.search);
    this._showState('connected');
    this._loadSpotifySDK();
    this._loadLibrary();
    this._initLastFM();
    this._initMemory();
    this._initFeedback();
    this._initHistoryNav();
    this._initMediaSessionHandlers();

    // Check for unfinished episode
    if (!this._resumeChecked) {
      this._resumeChecked = true;
      const resumeState = this._checkResumeState();
      if (resumeState) {
        // Delay slightly so DOM is ready
        setTimeout(() => this._showResumePrompt(resumeState), 200);
      }
    }
  }

  // ── Browser history navigation ──────────────────────────────────────────

  _pushHistoryState(name) {
    history.pushState({ resonovaState: name }, '', location.pathname + location.search);
  }

  _initHistoryNav() {
    window.addEventListener('popstate', (e) => {
      const s = e.state?.resonovaState;
      // Generating and playing are transient; any back navigation returns to library.
      if (s === 'landing') {
        this._showState('landing');
      } else {
        this._showState('connected');
      }
    });
  }

  // ── Last.fm widget ──────────────────────────────────────────────────────

  async _initLastFM() {
    try {
      const status = await this._apiFetch('/auth/lastfm/status');
      if (!status.available) return; // API keys not in env — keep widget hidden
      document.getElementById('lastfm-widget').style.display = '';
      this._renderLastFMStatus(status);
    } catch (e) {
      console.warn('Last.fm status check failed:', e);
    }

    document.getElementById('lastfm-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('lastfm-username').value.trim();
      if (!username) return;
      const btn = document.getElementById('lastfm-connect-btn');
      btn.disabled = true;
      btn.textContent = 'Connecting…';
      try {
        const result = await this._apiFetch('/auth/lastfm/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username }),
        });
        this._renderLastFMStatus({ connected: true, ...result });
      } catch (err) {
        btn.textContent = 'Not found';
        setTimeout(() => { btn.disabled = false; btn.textContent = 'Connect'; }, 2000);
      }
    });

    document.getElementById('lastfm-disconnect-btn').addEventListener('click', async () => {
      await fetch('/auth/lastfm/disconnect', { method: 'POST' });
      this._renderLastFMStatus({ connected: false });
    });
  }

  _renderLastFMStatus(status) {
    const connected = document.getElementById('lastfm-connected');
    const disconnected = document.getElementById('lastfm-disconnected');
    if (status.connected) {
      const scrobbles = status.scrobbles ? ` · ${status.scrobbles.toLocaleString()} scrobbles` : '';
      document.getElementById('lastfm-pill-label').textContent = `@${status.username}${scrobbles}`;
      connected.style.display = 'inline-flex';
      disconnected.style.display = 'none';
    } else {
      connected.style.display = 'none';
      disconnected.style.display = 'flex';
    }
  }

  _renderLastFMStatus(status) {
    const connected = document.getElementById('lastfm-connected');
    const disconnected = document.getElementById('lastfm-disconnected');
    if (status.connected) {
      const scrobbles = status.scrobbles ? ` · ${status.scrobbles.toLocaleString()} scrobbles` : '';
      document.getElementById('lastfm-pill-label').textContent = `@${status.username}${scrobbles}`;
      connected.style.display = 'inline-flex';
      disconnected.style.display = 'none';
    } else {
      connected.style.display = 'none';
      disconnected.style.display = 'flex';
    }
  }

  // ── Memory widget ────────────────────────────────────────────────────────

  async _initMemory() {
    try {
      const profile = await this._apiFetch('/api/profile');
      document.getElementById('memory-widget').style.display = '';
      this._updateMemoryPillLabel(profile);

      document.getElementById('memory-inspect-btn').addEventListener('click', async () => {
        const panel = document.getElementById('memory-panel');
        if (panel.style.display === 'none') {
          try {
            const fresh = await this._apiFetch('/api/profile');
            this._renderMemoryPanel(fresh);
            panel.style.display = '';
            document.getElementById('memory-inspect-btn').textContent = 'close';
            document.getElementById('memory-clear-btn').style.display = '';
          } catch (e) {
            console.warn('Memory load failed:', e);
          }
        } else {
          panel.style.display = 'none';
          document.getElementById('memory-inspect-btn').textContent = 'inspect';
          document.getElementById('memory-clear-btn').style.display = 'none';
        }
      });

      document.getElementById('memory-refresh-btn').addEventListener('click', async () => {
        const btn = document.getElementById('memory-refresh-btn');
        btn.textContent = '…';
        btn.disabled = true;
        try {
          const updated = await this._apiFetch('/api/profile/refresh', { method: 'POST' });
          this._updateMemoryPillLabel(updated);
          const panel = document.getElementById('memory-panel');
          if (panel.style.display !== 'none') {
            this._renderMemoryPanel(updated);
          }
        } catch (e) {
          console.warn('Profile refresh failed:', e);
        } finally {
          btn.textContent = 'refresh';
          btn.disabled = false;
        }
      });

      document.getElementById('memory-close-btn').addEventListener('click', () => {
        document.getElementById('memory-panel').style.display = 'none';
        document.getElementById('memory-inspect-btn').textContent = 'inspect';
        document.getElementById('memory-clear-btn').style.display = 'none';
      });

      const clearHandler = async () => {
        if (!confirm('Clear all memory? Resonova will start learning your taste again from scratch. Your saved casts are not affected.')) return;
        try {
          const empty = await this._apiFetch('/api/profile', { method: 'DELETE' });
          this._updateMemoryPillLabel(empty);
          this._renderMemoryPanel(empty);
        } catch (e) {
          console.warn('Memory clear failed:', e);
        }
      };
      document.getElementById('memory-clear-btn').addEventListener('click', clearHandler);
      document.getElementById('memory-clear-action-btn').addEventListener('click', clearHandler);

      // Pin/delete delegation — attached ONCE here (not per-render) so a misclick
      // can't consume the listener and silently disable the buttons.
      document.getElementById('memory-memories-rows').addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const id = btn.dataset.id;
        let body = {};
        if (btn.dataset.action === 'pin') {
          body = { pin_memory_id: id, pin_value: btn.dataset.pinned !== '1' };
        } else if (btn.dataset.action === 'delete') {
          body = { delete_memory_id: id };
        }
        try {
          const updated = await this._apiFetch('/api/profile', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
          this._updateMemoryPillLabel(updated);
          this._renderMemoryPanel(updated);
        } catch (e2) {
          console.warn('Memory action failed:', e2);
        }
      });
    } catch (e) {
      console.warn('Memory init failed:', e);
    }
  }

  _escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  _updateMemoryPillLabel(profile) {
    const taste = profile.taste_profile || {};
    const memories = profile.memories || [];
    const artistCount = (taste.top_artists || []).length;
    const memCount = memories.length;
    let label = 'Memory';
    if (artistCount || memCount) {
      const parts = [];
      if (artistCount) parts.push(`${artistCount} artist${artistCount !== 1 ? 's' : ''}`);
      if (memCount) parts.push(`${memCount} note${memCount !== 1 ? 's' : ''}`);
      label = parts.join(' · ');
    } else {
      label = 'Memory — empty';
    }
    document.getElementById('memory-pill-label').textContent = label;
  }

  _renderMemoryPanel(profile) {
    const taste = profile.taste_profile || {};
    const prefs = profile.commentary_preferences || {};
    const memories = profile.memories || [];

    const hasAny = (
      (taste.top_artists || []).length ||
      (taste.recurring_styles || []).length ||
      (taste.favorite_eras || []).length ||
      (taste.saved_library_artists || []).length ||
      (taste.followed_artists || []).length ||
      (prefs.tone || []).length ||
      (prefs.avoid || []).length ||
      (prefs.loved_patterns || []).length ||
      memories.length
    );

    document.getElementById('memory-empty-hint').style.display = hasAny ? 'none' : '';

    // ── Memory enabled toggle ─────────────────────────────────────────────
    const toggle = document.getElementById('memory-enabled-toggle');
    if (toggle) {
      toggle.checked = profile.memory_enabled !== false;
      toggle.onchange = async () => {
        try {
          const updated = await this._apiFetch('/api/profile', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ memory_enabled: toggle.checked }),
          });
          this._updateMemoryPillLabel(updated);
        } catch (e) {
          console.warn('Memory toggle failed:', e);
          toggle.checked = !toggle.checked; // revert
        }
      };
    }

    // ── Taste profile rows ─────────────────────────────────────────────────
    const tasteSection = document.getElementById('memory-taste-section');
    const tasteRows = document.getElementById('memory-taste-rows');
    tasteRows.innerHTML = '';
    const tasteFields = [
      ['top artists', taste.top_artists],
      ['recurring styles', taste.recurring_styles],
      ['favourite eras', taste.favorite_eras],
      ['recent listening', taste.recent_shifts],
      ['library regulars', taste.saved_library_artists],
      ['followed artists', taste.followed_artists],
      ['playlist patterns', taste.playlist_patterns],
    ];
    let hasTaste = false;
    for (const [label, values] of tasteFields) {
      if (!values || !values.length) continue;
      hasTaste = true;
      const row = document.createElement('div');
      row.className = 'memory-row';
      row.innerHTML = `<span class="memory-row-label">${label}</span><span class="memory-row-value">${values.map((v) => this._escapeHtml(v)).join(', ')}</span>`;
      tasteRows.appendChild(row);
    }
    tasteSection.style.display = hasTaste ? '' : 'none';

    // ── Commentary preferences rows ────────────────────────────────────────
    const prefsSection = document.getElementById('memory-prefs-section');
    const prefsRows = document.getElementById('memory-prefs-rows');
    prefsRows.innerHTML = '';
    const prefsFields = [
      ['tone', prefs.tone],
      ['depth', prefs.depth ? [prefs.depth] : null],
      ['avoid', prefs.avoid],
      ['lean into', prefs.loved_patterns],
    ];
    let hasPrefs = false;
    for (const [label, values] of prefsFields) {
      if (!values || !values.length) continue;
      hasPrefs = true;
      const row = document.createElement('div');
      row.className = 'memory-row';
      row.innerHTML = `<span class="memory-row-label">${label}</span><span class="memory-row-value">${values.map((v) => this._escapeHtml(v)).join(', ')}</span>`;
      prefsRows.appendChild(row);
    }
    prefsSection.style.display = hasPrefs ? '' : 'none';

    // ── Memories list (with pin/delete) ────────────────────────────────────
    const memoriesSection = document.getElementById('memory-memories-section');
    const memoriesRows = document.getElementById('memory-memories-rows');
    memoriesRows.innerHTML = '';
    if (memories.length) {
      const sorted = [...memories].sort((a, b) => {
        const pin = (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0);
        if (pin !== 0) return pin;
        const cRank = { high: 0, medium: 1, low: 2 };
        return (cRank[a.confidence] ?? 2) - (cRank[b.confidence] ?? 2);
      });
      for (const m of sorted) {
        const item = document.createElement('div');
        item.className = 'memory-memory-item';
        const pinBadge = m.pinned ? '<span class="memory-badge pinned">pinned</span>' : '';
        const confBadge = m.confidence ? `<span class="memory-badge ${m.confidence}">${m.confidence}</span>` : '';
        const srcBadge = m.source ? `<span class="memory-badge">${this._escapeHtml(m.source)}</span>` : '';
        item.innerHTML = `
          <span style="flex:1">${this._escapeHtml(m.text)}</span>
          ${pinBadge}${confBadge}${srcBadge}
          <button class="memory-action-btn" data-action="pin" data-id="${m.id}" data-pinned="${m.pinned ? '1' : '0'}" title="${m.pinned ? 'Unpin' : 'Pin'}">${m.pinned ? '★' : '☆'}</button>
          <button class="memory-action-btn" data-action="delete" data-id="${m.id}" title="Delete">✕</button>
        `;
        memoriesRows.appendChild(item);
      }
      // Pin/delete clicks are handled by the delegated listener attached once in _initMemory.
    }
    memoriesSection.style.display = memories.length ? '' : 'none';
  }

  // ── Feedback channel ─────────────────────────────────────────────────────

  _initFeedback() {
    this._feedbackVerdict = null;
    this._feedbackTags = new Set();

    const panel = document.getElementById('feedback-panel');
    const upBtn = document.getElementById('feedback-up-btn');
    const downBtn = document.getElementById('feedback-down-btn');
    const tagsEl = document.getElementById('feedback-tags');
    const submitRow = document.getElementById('feedback-submit-row');
    const submitBtn = document.getElementById('feedback-submit-btn');
    const sentMsg = document.getElementById('feedback-sent-msg');

    if (!panel) return;

    const setVerdict = (v) => {
      this._feedbackVerdict = v;
      upBtn.classList.toggle('feedback-thumb-active', v === 'up');
      downBtn.classList.toggle('feedback-thumb-active', v === 'down');
      tagsEl.style.display = '';
      submitRow.style.display = '';
    };

    upBtn.addEventListener('click', () => setVerdict('up'));
    downBtn.addEventListener('click', () => setVerdict('down'));

    tagsEl.querySelectorAll('.feedback-tag').forEach(btn => {
      btn.addEventListener('click', () => {
        const tag = btn.dataset.tag;
        if (this._feedbackTags.has(tag)) {
          this._feedbackTags.delete(tag);
          btn.classList.remove('feedback-tag-active');
        } else {
          this._feedbackTags.add(tag);
          btn.classList.add('feedback-tag-active');
        }
      });
    });

    submitBtn.addEventListener('click', async () => {
      if (!this._feedbackVerdict || !this._episodeId) return;
      submitBtn.disabled = true;
      try {
        await this._apiFetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            episode_id: this._episodeId,
            verdict: this._feedbackVerdict,
            tags: [...this._feedbackTags],
          }),
        });
        sentMsg.style.display = '';
        submitBtn.style.display = 'none';
        // Reset state
        this._feedbackVerdict = null;
        this._feedbackTags = new Set();
        upBtn.classList.remove('feedback-thumb-active');
        downBtn.classList.remove('feedback-thumb-active');
        tagsEl.querySelectorAll('.feedback-tag').forEach(b => b.classList.remove('feedback-tag-active'));
      } catch (e) {
        console.warn('Feedback submit failed:', e);
        submitBtn.disabled = false;
      }
    });
  }

  _showFeedbackPanel(episodeId) {
    const panel = document.getElementById('feedback-panel');
    if (!panel) return;
    this._episodeId = episodeId;
    // Reset sent state
    const sentMsg = document.getElementById('feedback-sent-msg');
    const submitBtn = document.getElementById('feedback-submit-btn');
    if (sentMsg) sentMsg.style.display = 'none';
    if (submitBtn) { submitBtn.style.display = ''; submitBtn.disabled = false; }
    panel.style.display = '';
  }

  _loadSpotifySDK() {
    window.onSpotifyWebPlaybackSDKReady = () => this._initSpotifyPlayer();
    const script = document.createElement('script');
    script.src = 'https://sdk.scdn.co/spotify-player.js';
    document.head.appendChild(script);
  }

  async _initSpotifyPlayer() {
    // Always fetch a fresh token — it may have been refreshed server-side
    this._lifecycle.sdkLoaded = true;
    const { token } = await this._apiFetch('/auth/token');
    if (!token) return;
    this._cachedToken = token;

    this.spotifyPlayer = new window.Spotify.Player({
      name: 'Resonova',
      getOAuthToken: async (cb) => {
        try {
          const { token: fresh } = await this._apiFetch('/auth/token');
          if (fresh) this._cachedToken = fresh;
          cb(fresh || this._cachedToken);
        } catch {
          // If fetch fails (mobile suspended/backgrounded), use cached token
          // so cb() is always called and SDK never gets stuck
          if (this._cachedToken) cb(this._cachedToken);
        }
      },
      volume: _SPOTIFY_VOLUME,
    });
    this._lifecycle.playerConstructed = true;

    this.spotifyPlayer.addListener('ready', ({ device_id }) => {
      this.deviceId = device_id;
      this._lifecycle.ready = true;
      this._lifecycle.deviceId = device_id;
      this._deviceGeneration++;
      this._deviceAcquiredAt = Date.now();
      this._obsRecord('device:ready', `gen=${this._deviceGeneration} id=...${device_id.slice(-6)}`);
      this._clearSpotifyUnhealthy();
      // Do not transfer playback on passive page load. A phone refreshing the
      // library must not steal Spotify playback from an active PC session.
    });

    this.spotifyPlayer.addListener('not_ready', () => {
      this._markSpotifyUnhealthy('not_ready', 'Device was marked not ready');
    });

    this.spotifyPlayer.addListener('initialization_error', ({ message }) => {
      console.error('Spotify init error:', message);
      this._lifecycle.initError = message;
      this._renderDiagnostics(null);
      document.getElementById('sdk-warning').classList.add('visible');
    });

    this.spotifyPlayer.addListener('authentication_error', ({ message }) => {
      this._markSpotifyUnhealthy('authentication_error', message);
    });

    this.spotifyPlayer.addListener('account_error', (e) => {
      this._lifecycle.accountError = e?.message || true;
      this._renderDiagnostics(null);
      document.getElementById('sdk-warning').classList.add('visible');
    });

    this.spotifyPlayer.addListener('playback_error', ({ message }) => {
      this._markSpotifyUnhealthy('playback_error', message);
    });

    this.spotifyPlayer.addListener('autoplay_failed', () => {
      this._lifecycle.autoplayFailed = true;
      this._renderDiagnostics(null);
    });

    this.spotifyPlayer.addListener('player_state_changed', (state) => {
      this._handleSpotifyStateChange(state);
    });

    const connectPromise = this.spotifyPlayer.connect();
    this._lifecycle.connectCalled = true;
    this._renderDiagnostics(null);
    connectPromise.then(
      (ok) => {
        this._lifecycle.connectResult = ok ? 'success' : 'false';
        this._renderDiagnostics(null);
      },
      (err) => {
        this._lifecycle.connectResult = 'error: ' + (err?.message || err);
        this._renderDiagnostics(null);
      }
    );
    connectPromise.catch(() => { });
  }

  async _transferPlayback(deviceId, token) {
    const res = await this._fetchWithTimeout('https://api.spotify.com/v1/me/player', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ device_ids: [deviceId], play: false }),
    }, 8000);
    if (!res.ok) {
      let detail = '';
      try { detail = await res.text(); } catch (_) { }
      throw new Error(`Transfer playback failed: ${res.status}${detail ? `: ${detail.slice(0, 180)}` : ''}`);
    }
  }

  async _waitForSpotifyConnectDevice(token, deviceId, timeoutMs = 5000) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      try {
        const res = await this._fetchWithTimeout('https://api.spotify.com/v1/me/player/devices', {
          headers: { 'Authorization': `Bearer ${token}` },
        }, 1500);
        if (res.ok) {
          const data = await res.json();
          const visible = (data.devices || []).some(device => device.id === deviceId);
          if (visible) return true;
        }
      } catch (_) { }
      await new Promise(resolve => setTimeout(resolve, 350));
    }
    return false;
  }

  async _sendSpotifyPlayCommand(token, uri) {
    this._obsRecord('play:cmd:start', uri.slice(-24));
    const visible = await this._waitForSpotifyConnectDevice(token, this.deviceId, 5000);
    if (!visible) {
      const err = new Error('Spotify device is not visible in Connect devices');
      err.status = 404;
      this._obsRecord('play:cmd:fail', `404:device-not-visible`);
      throw err;
    }
    const res = await this._fetchWithTimeout(`https://api.spotify.com/v1/me/player/play?device_id=${this.deviceId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ uris: [uri] }),
    }, 8000);
    if (!res.ok) {
      let detail = '';
      try { detail = await res.text(); } catch (_) { }
      this._obsRecord('play:cmd:fail', `${res.status}:${detail.slice(0, 60)}`);
      const err = new Error(
        `Device playback endpoint returned ${res.status}${detail ? `: ${detail.slice(0, 180)}` : ''}`
      );
      err.status = res.status;
      throw err;
    }
    this._obsRecord('play:cmd:ok', `${res.status}`);
  }

  async _waitForSpotifyPlaybackStart(uri, timeoutMs = 3000) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      try {
        const state = await this.spotifyPlayer?.getCurrentState();
        if (state) {
          this._renderDiagnostics(state);
          const currentUri = state.track_window?.current_track?.uri;
          if (currentUri === uri && !state.paused) {
            // Confirm audio position actually advances (guard against blind "playing")
            const firstPos = state.position || 0;
            await new Promise(resolve => setTimeout(resolve, 750));
            const reState = await this.spotifyPlayer?.getCurrentState();
            if (reState) {
              this._renderDiagnostics(reState);
              const rePos = reState.position || 0;
              if (rePos - firstPos > 250) return true;
              // Position not advancing — continue loop to timeout
              this._obsRecord('play:start:stalled', `pos:${firstPos}->${rePos}`);
              continue;
            }
            return true; // no re-state available; trust the initial match
          }
        }
      } catch (_) { }
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    return false;
  }

  _discardSpotifyDevice(reason) {
    this._obsRecord('device:discard', (reason || '').slice(0, 80));
    console.warn('[Resonova] Discarding Spotify device:', reason);
    try { this.spotifyPlayer?.disconnect(); } catch (_) { }
    this.spotifyPlayer = null;
    this.deviceId = null;
    this._lifecycle.ready = false;
    this._lifecycle.deviceId = null;
  }

  // ──────────────────────────────────────────────
  // Generation flow
  // ──────────────────────────────────────────────

  async generate(rawInput) {
    const parsed = this._parseInput(rawInput);
    if (!parsed) {
      this._showError('Paste a Spotify playlist link, URI, or a list of track URLs.');
      return;
    }
    // Single-generation lock: navigate to the running cast instead of stacking a new one.
    if (this._activeGenerationId && !this._generationComplete) {
      this._pushHistoryState('generating');
      this._showState('generating');
      return;
    }
    // Regeneration guard: confirm before generating a fresh episode for a playlist
    // that already has saved episodes.
    if (parsed.playlist_uri) {
      const existingCount = (this._episodes || [])
        .filter(ep => ep.playlist_uri === parsed.playlist_uri && ep.status === 'complete')
        .length;
      if (existingCount > 0) {
        const label = existingCount === 1 ? 'cast' : 'casts';
        const proceed = await this._confirmRegeneration(
          `You already have ${existingCount} ${label} for this playlist. Generate a new episode?`
        );
        if (!proceed) return;
      }
    }
    // Incognito: one-off cast that reads and writes no memory.
    const _incognitoEl = document.getElementById('generate-incognito');
    parsed.incognito = !!(_incognitoEl && _incognitoEl.checked);

    const _languageSelect = document.getElementById('commentary-language');
    const _languageCustom = document.getElementById('commentary-language-custom');
    const selectedLanguage = (_languageSelect?.value || '').trim();
    const commentaryLanguage = selectedLanguage === 'custom'
      ? (_languageCustom?.value || '').trim()
      : selectedLanguage;
    if (commentaryLanguage) {
      parsed.commentary_language = commentaryLanguage.slice(0, 40);
    }

    // Cast lenses: analysis depth and host vibe
    const _depthSelect = document.getElementById('cast-depth');
    const depthVal = _depthSelect?.value || '';
    if (depthVal) {
      parsed.cast_depth = depthVal;
    }

    const _vibeSelect = document.getElementById('cast-vibe');
    const vibeVal = _vibeSelect?.value || '';
    if (vibeVal) {
      parsed.cast_vibe = vibeVal;
    }

    // Persist last-selected lenses so they survive page refresh
    try {
      localStorage.setItem('resonova:cast-depth', depthVal);
      localStorage.setItem('resonova:cast-vibe', vibeVal);
    } catch (_) {}

    // Client-side quota cooldown guard — blocks immediate retries without a server round-trip
    try {
      const raw = localStorage.getItem('resonova:tts-cooldown');
      if (raw) {
        const cd = JSON.parse(raw);
        if (cd.until && Date.now() < cd.until) {
          const remaining = Math.ceil((cd.until - Date.now()) / 1000);
          this._showQuotaError({
            code: 'tts_quota_exhausted',
            model: cd.model || '',
            retry_after_seconds: remaining,
            message: cd.message || 'Gemini TTS quota is still cooling down.',
          });
          return;
        }
        localStorage.removeItem('resonova:tts-cooldown');
      }
    } catch (_) { }

    this._pushHistoryState('generating');
    this._showState('generating');

    let jobId;
    try {
      const res = await this._apiFetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      jobId = res.job_id;
      this._episodeId = jobId;
      this._activeGenerationId = jobId;
      this._activeGenerationName = 'Generating cast';
      this._activeGenerationSource = parsed.playlist_uri ? 'New playlist' : 'Custom tracks';
      this._pendingEpisodeFocusId = jobId;
      this._episodesNeedRefresh = true;
    } catch (err) {
      this._showState('connected');
      // Server-side cooldown: 429 with structured quota detail
      if (err.status === 429 && err.body && err.body.detail && err.body.detail.code === 'tts_quota_exhausted') {
        this._showQuotaError(err.body.detail);
      } else {
        this._showError('Failed to start generation: ' + err.message);
      }
      return;
    }

    this._streamProgress(jobId);
  }

  _confirmRegeneration(text) {
    return new Promise(resolve => {
      const overlay = document.getElementById('regeneration-confirm');
      const textEl = document.getElementById('regeneration-confirm-text');
      const cancelBtn = document.getElementById('regeneration-cancel-btn');
      const proceedBtn = document.getElementById('regeneration-proceed-btn');
      if (!overlay || !textEl || !cancelBtn || !proceedBtn) {
        resolve(true); // fallback: allow generation if elements missing
        return;
      }
      textEl.textContent = text;
      overlay.style.display = 'flex';
      const cleanup = () => {
        overlay.style.display = 'none';
        cancelBtn.removeEventListener('click', onCancel);
        proceedBtn.removeEventListener('click', onProceed);
      };
      const onCancel = () => { cleanup(); resolve(false); };
      const onProceed = () => { cleanup(); resolve(true); };
      cancelBtn.addEventListener('click', onCancel);
      proceedBtn.addEventListener('click', onProceed);
    });
  }

  _streamProgress(jobId) {
    // Close any previous stream before opening a new one (stale-SSE guard)
    if (this._activeStream) {
      this._activeStream.close();
      this._activeStream = null;
    }
    const es = new EventSource(`/jobs/${jobId}/stream`);
    this._activeStream = es;

    this._generationComplete = false;

    // SSE silence watchdog: if no event arrives for 30s behind a proxy/tunnel
    // that buffers SSE, fall back to polling /jobs/{id}/status.
    this._clearSSEWatchdog();
    this._lastSSEEventTime = Date.now();
    this._sseWatchdog = setInterval(async () => {
      if (this._generationComplete) { this._clearSSEWatchdog(); return; }
      if (jobId !== this._activeGenerationId) { this._clearSSEWatchdog(); return; }
      const silentMs = Date.now() - this._lastSSEEventTime;
      if (silentMs < 30000) return;
      // SSE has been silent too long — poll job status as fallback
      try {
        const statusRes = await this._apiFetch(`/jobs/${jobId}/status`);
        if (statusRes.status === 'done') {
          this._handleGenerationDone(jobId, es);
        } else if (statusRes.status === 'error') {
          this._handleGenerationError({ message: statusRes.error || 'Generation failed.' }, es);
        }
      } catch (_) { /* polling failed, will retry next interval */ }
    }, 5000);

    const _touchSSE = () => { this._lastSSEEventTime = Date.now(); };

    es.addEventListener('progress', (e) => {
      _touchSSE();
      const { step, message } = JSON.parse(e.data);
      this._updateProgressStep(step, message);
    });

    // Intro is ready — start playback immediately with just the intro audio
    es.addEventListener('intro_ready', (e) => {
      _touchSSE();
      // Stale-event guard: ignore if this stream is no longer the active generation
      if (jobId !== this._activeGenerationId) return;
      const { url, episode_name, tagline } = JSON.parse(e.data);
      if (episode_name) this._activeGenerationName = episode_name;
      if (tagline) this._activeGenerationTagline = tagline;
      this._markAllStepsDone();
      this._startPlayback([{ type: 'audio', url }]);
    });

    // Each track's commentary arrives as it finishes — append to live queue
    es.addEventListener('track_ready', (e) => {
      _touchSSE();
      const { commentary_url, track_uri, total, track_name, artist, duration_ms } = JSON.parse(e.data);
      const commentaryItem = { type: 'audio', url: commentary_url };
      const spotifyItem = { type: 'spotify', uri: track_uri };
      if (track_name) spotifyItem.name = track_name;
      if (artist) spotifyItem.artist = artist;
      if (duration_ms) spotifyItem.duration_ms = duration_ms;
      this.queue.push(commentaryItem);
      this.queue.push(spotifyItem);
      this.playbackTimeline.push(commentaryItem);
      this.playbackTimeline.push(spotifyItem);
      // intro (1) + N tracks × 2 items each
      this.totalItems = 1 + total * 2;
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
      this._refreshCurrentGenerationInLibrary();
    });

    // Outro arrives after the last track — append to the live queue
    es.addEventListener('outro_ready', (e) => {
      _touchSSE();
      const { url } = JSON.parse(e.data);
      const outroItem = { type: 'audio', url };
      this.queue.push(outroItem);
      this.playbackTimeline.push(outroItem);
      this.totalItems += 1;
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
      this._refreshCurrentGenerationInLibrary();
      this._scheduleGenerationSaveCheck(jobId);
    });

    es.addEventListener('done', (e) => {
      _touchSSE();
      let doneData = {};
      try { doneData = JSON.parse(e.data || '{}'); } catch (_) { }
      this._handleGenerationDone(doneData.episode_id || null, es);
    });

    es.addEventListener('error', (e) => {
      _touchSSE();
      let errData = {};
      try { errData = JSON.parse(e.data || '{}'); } catch (_) { }
      this._handleGenerationError(errData, es);
    });
  }

  // ──────────────────────────────────────────────
  // Playback queue
  // ──────────────────────────────────────────────

  _startPlayback(queue, options = {}) {
    if (options.replayEpisodeId) {
      this._beginReplayTracking(options.replayEpisodeId, queue.length);
    } else {
      this._clearReplayTracking();
    }
    this.queue = [...queue];
    this.playedItems = [];
    this.playbackTimeline = options.timeline ? [...options.timeline] : [...queue];
    this.currentIndex = -1;
    this.totalItems = queue.length;
    this.completedItems = 0;
    this._isPaused = false;
    this._pushHistoryState('playing');
    this._showState('playing');
    document.getElementById('on-air-badge').classList.add('active');
    this._renderDiagnostics(null);
    this._updateSkipButton();
    this._updatePlayPauseButton();
    this._playNext();
    this._saveResumeState();
  }

  _playNext() {
    if (this.currentItem) {
      this.playedItems.push(this.currentItem);
      this.currentItem = null;
    }

    if (this.queue.length === 0) {
      if (!this._generationComplete) {
        // More tracks are still being synthesized — poll until they arrive
        setTimeout(() => this._playNext(), 300);
        return;
      }
      if (this.totalItems > 0 && this.completedItems < this.totalItems) {
        this._recoverMissingEpisodeTail().then((recovered) => {
          if (recovered) {
            this._playNext();
          } else {
            this._parkIncompleteEpisode();
          }
        });
        return;
      }
      this._onPlaybackComplete();
      return;
    }

    const item = this.queue.shift();
    this.currentItem = item;
    let timelineIndex = this.playbackTimeline.indexOf(item);
    if (timelineIndex === -1) {
      this.playbackTimeline.push(item);
      timelineIndex = this.playbackTimeline.length - 1;
    }
    this.currentIndex = timelineIndex;
    this._trackEndFired = false;
    // Clear any pending segment deadline (item is changing)
    if (this._segmentDeadline) {
      clearTimeout(this._segmentDeadline);
      this._segmentDeadline = null;
    }
    this.completedItems++;
    this._updateProgress();
    this._updateSkipButton();
    this._renderDiagnostics(null);
    this._saveResumeState();
    this._maybeReportMeaningfulReplay();

    if (item.type === 'audio') {
      this._playAudio(item);
    } else if (item.type === 'spotify') {
      this._playSpotifyTrack(item);
    }
  }

  _playAudio(item) {
    this._isPaused = false;
    this._updatePlayPauseButton();
    this._setSegmentType('commentary');
    this._setNowPlaying('AI Commentary', 'Podcast Intro');
    this._updateSkipMusicButton();

    // Look ahead to find what Spotify track comes next (for context)
    const nextSpotify = this.queue.find(q => q.type === 'spotify');
    const cachedNext = nextSpotify?.uri ? this._cacheGet(nextSpotify.uri) : null;
    if (cachedNext && nextSpotify) {
      nextSpotify.name = nextSpotify.name || cachedNext.name;
      nextSpotify.artist = nextSpotify.artist || cachedNext.artist;
      nextSpotify.duration_ms = nextSpotify.duration_ms || cachedNext.duration_ms;
    }
    if (nextSpotify?.name) {
      document.getElementById('next-up').innerHTML =
        `Up next: <strong>${this._esc(nextSpotify.name)}</strong>`;
    } else {
      document.getElementById('next-up').textContent = '';
      // Name not yet known — prefetch metadata asynchronously during commentary
      if (nextSpotify?.uri) this._prefetchNextTrackMeta(nextSpotify);
    }

    document.getElementById('waveform').classList.remove('spotify-mode');
    document.getElementById('waveform').classList.remove('paused');
    document.getElementById('progress-fill').classList.remove('spotify-mode');

    this.audioEl.volume = 1;
    this.audioEl.src = item.url;
    this._crossfadeTriggered = false;

    // Fade out commentary ~2s before end so it flows smoothly into the next segment
    this.audioEl.ontimeupdate = () => {
      if (!this._crossfadeTriggered && this.audioEl.duration > 0) {
        const remaining = (this.audioEl.duration - this.audioEl.currentTime) * 1000;
        if (remaining < _CROSSFADE_MS && remaining > 0) {
          this._crossfadeTriggered = true;
          this._fadeAudioVolume(1, 0, remaining);
        }
      }
    };

    this.audioEl.onended = () => {
      this.audioEl.ontimeupdate = null;
      this._playNext();
    };

    this.audioEl.play()
      .then(() => this._setMediaSessionPlaybackState('playing'))
      .catch(err => {
        console.error('Audio play failed:', err);
        this._playNext();
      });
  }

  /**
   * Asynchronously prefetch Spotify track metadata during commentary so the
   * "Up next" display can update without waiting for the Spotify segment to start.
   * Uses _metaPrefetch as an in-flight guard to prevent duplicate fetch storms.
   */
  async _prefetchNextTrackMeta(spotifyItem) {
    if (!spotifyItem?.uri || this._metaPrefetch.has(spotifyItem.uri)) return;
    this._metaPrefetch.add(spotifyItem.uri);
    try {
      const { token } = await this._apiFetch('/auth/token');
      const trackId = spotifyItem.uri.split(':')[2];
      if (!trackId) return;
      const res = await this._fetchWithTimeout(
        `https://api.spotify.com/v1/tracks/${trackId}`,
        { headers: { Authorization: `Bearer ${token}` } },
        8000,
      );
      if (!res.ok) return;
      const data = await res.json();
      const artist = data.artists.map(a => a.name).join(', ');
      spotifyItem.name = data.name;
      spotifyItem.artist = artist;
      spotifyItem.duration_ms = data.duration_ms;
      this._cacheSet(spotifyItem.uri, { name: data.name, artist, duration_ms: data.duration_ms });
      // Update only if this track is still the next Spotify segment.
      const stillNext = this.queue.find(q => q.type === 'spotify')?.uri === spotifyItem.uri;
      if (this._segmentType === 'commentary' && stillNext) {
        const el = document.getElementById('next-up');
        if (el) el.innerHTML = `Up next: <strong>${this._esc(data.name)}</strong>`;
      }
    } catch (_) {
      // Silently ignore — commentary playback is unaffected
    } finally {
      this._metaPrefetch.delete(spotifyItem.uri);
    }
  }

  async _playSpotifyTrack(item) {
    this._isPaused = false;
    this._updatePlayPauseButton();
    this._setSegmentType('spotify');

    this._setNowPlaying(item.name || 'Spotify music', item.artist || 'Connecting to Spotify...');
    document.getElementById('next-up').textContent = '';

    document.getElementById('waveform').classList.add('spotify-mode');
    document.getElementById('waveform').classList.remove('paused');
    document.getElementById('progress-fill').classList.add('spotify-mode');

    if (!this._isSpotifyHealthy()) {
      if (!navigator.onLine) {
        this._obsRecord('play:spotify:offline', '');
        this._setNowPlaying('Spotify unavailable offline', 'Use Next to continue commentary');
        document.getElementById('waveform').classList.remove('spotify-mode');
        document.getElementById('progress-fill').classList.remove('spotify-mode');
        this._updateSkipMusicButton();
        return;
      }
      console.warn('Spotify unhealthy. Triggering automatic single recovery...');
      const recovered = await this._recoverSpotifySession();
      if (!recovered) {
        console.error('Spotify recovery failed. Halting playback.');
        this._setNowPlaying('(Spotify connection lost. Click Recover below.)', '');
        document.getElementById('waveform').classList.remove('spotify-mode');
        document.getElementById('progress-fill').classList.remove('spotify-mode');
        return;
      }
    }

    const { token } = await this._apiFetch('/auth/token');

    // Fetch track info — check cache first
    const cached = this._cacheGet(item.uri);
    if (cached) {
      this._setNowPlaying(cached.name, cached.artist);
      item.name = cached.name;
      item.artist = cached.artist;
      item.duration_ms = cached.duration_ms;
      document.getElementById('next-up').textContent = '';
    } else {
      try {
        const trackId = item.uri.split(':')[2];
        const trackRes = await this._fetchWithTimeout(`https://api.spotify.com/v1/tracks/${trackId}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }, 8000);
        if (trackRes.ok) {
          const trackData = await trackRes.json();
          const artist = trackData.artists.map(a => a.name).join(', ');
          this._setNowPlaying(trackData.name, artist);
          item.name = trackData.name;
          item.artist = artist;
          item.duration_ms = trackData.duration_ms;
          this._cacheSet(item.uri, {
            name: trackData.name,
            artist,
            duration_ms: trackData.duration_ms,
          });
          document.getElementById('next-up').textContent = '';
        }
      } catch (err) {
        this._obsRecord('track:metadata:fail', err?.name === 'AbortError' ? 'timeout' : 'network');
      }
    }

    try {
      // Restore full volume whenever we start a Spotify track
      await this.spotifyPlayer.setVolume(_SPOTIFY_VOLUME);
      try {
        await this._sendSpotifyPlayCommand(token, item.uri);
        const started = await this._waitForSpotifyPlaybackStart(item.uri);
        if (!started) {
          console.warn('[Resonova] Spotify play command succeeded but SDK state is blank; continuing in blind playback mode.');
          this._obsRecord('play:start:blind', '');
          this._setBlindSpotifyDeadline(item);
        } else {
          this._obsRecord('play:start:confirmed', '');
        }
      } catch (err) {
        if (err.status !== 404) throw err;
        if (document.visibilityState !== 'visible') {
          this._obsRecord('play:spotify:connect-missing-hidden', item.uri.slice(-24));
          this._spotifyUnhealthy = true;
          this._spotifyRecoveryFailed = true;
          this._lifecycle.playbackError = 'Spotify device unavailable while page hidden';
          this._setNowPlaying('Spotify waiting for phone unlock', 'Return to resume or use Skip Music');
          this._updateRecoveryControl();
          this._updateSkipMusicButton();
          this._saveResumeState();
          return;
        }
        console.warn('[Resonova] Spotify device returned 404; rebuilding SDK session once and retrying.', err);
        this._markSpotifyUnhealthy('not_ready', err.message || 'Spotify device did not start playback');
        this._discardSpotifyDevice(err.message || 'playback did not start');
        const recovered = await this._recoverSpotifySession();
        if (!recovered) throw new Error('Spotify device could not be registered with Spotify Connect after recovery');
        const { token: freshToken } = await this._apiFetch('/auth/token');
        await this._sendSpotifyPlayCommand(freshToken, item.uri);
        const retryStarted = await this._waitForSpotifyPlaybackStart(item.uri, 5000);
        if (!retryStarted) {
          console.warn('[Resonova] Spotify retry command succeeded but SDK state is still blank; continuing in blind playback mode.');
          this._obsRecord('play:start:blind', 'retry');
          this._setBlindSpotifyDeadline(item);
        } else {
          this._obsRecord('play:start:confirmed', 'retry');
        }
      }
      this._setMediaSessionPlaybackState('playing');
    } catch (err) {
      this._obsRecord('play:start:failed', (err?.message || '').slice(0, 80));
      console.error('Spotify play failed:', err);
      this._markSpotifyUnhealthy('playback_error', err.message || 'Direct play command failed');
      this._spotifyRecoveryFailed = true;
      if (err.status >= 500) {
        this._recommendSpotifyReload(`playback-${err.status}`);
      }
      this._updateRecoveryControl();
      if (!this._spotifyReloadRecommended) {
        this._setNowPlaying('(Spotify playback failed. Click Recover below.)', '');
      }
      document.getElementById('waveform').classList.remove('spotify-mode');
      document.getElementById('progress-fill').classList.remove('spotify-mode');
    }
  }

  _setBlindSpotifyDeadline(item) {
    if (this._segmentDeadline || !item?.duration_ms) return;
    const sentinel = item;
    const deadlineMs = 5000; // short re-check window instead of full track duration
    this._obsRecord('deadline:blind:armed', `${deadlineMs}ms`);
    this._segmentDeadline = setTimeout(async () => {
      if (this.currentItem !== sentinel || this._trackEndFired) {
        this._segmentDeadline = null;
        return;
      }
      // Re-sample position to see if audio is actually playing now
      try {
        const state = await this.spotifyPlayer?.getCurrentState();
        if (state) {
          const currentPos = state.position || 0;
          if (currentPos > 500) {
            // Position advanced — audio caught up; do not force-advance
            this._obsRecord('deadline:blind:cancelled', `pos:${currentPos}ms`);
            this._segmentDeadline = null;
            return;
          }
        }
      } catch (_) { }
      // Position still at/near zero — force-advance
      console.log('[Resonova] Blind Spotify deadline fired; forcing advance');
      this._obsRecord('deadline:blind:fired', '');
      this._trackEndFired = true;
      await this._fadeSpotifyVolume(_SPOTIFY_VOLUME, 0, _CROSSFADE_MS);
      this._playNext();
      this._segmentDeadline = null;
    }, deadlineMs);
  }

  _handleSpotifyStateChange(state) {
    if (!state) return;
    this._renderDiagnostics(state);
    if (this.currentItem?.type !== 'spotify') return;

    console.log('[Resonova] Spotify state:', JSON.stringify({
      paused: state?.paused,
      position: state?.position,
      duration: state?.duration,
      track: state?.track_window?.current_track?.name,
      prevCount: state?.track_window?.previous_tracks?.length,
      deviceId: this.deviceId,
    }));

    // Set a one-shot deadline: if player_state_changed never fires again
    // (mobile background/lockscreen), force-advance after remaining duration.
    if (state.duration > 0 && !state.paused && !this._segmentDeadline) {
      const remainingMs = Math.max(0, state.duration - (state.position || 0));
      const deadlineMs = Math.max(3000, remainingMs + 3000);
      const sentinel = this.currentItem;
      this._obsRecord('deadline:seg:armed', `${deadlineMs}ms`);
      this._segmentDeadline = setTimeout(() => {
        if (this.currentItem === sentinel && !this._trackEndFired) {
          console.log('[Resonova] Segment deadline fired; forcing advance');
          this._obsRecord('deadline:seg:fired', '');
          this._trackEndFired = true;
          this._fadeSpotifyVolume(_SPOTIFY_VOLUME, 0, _CROSSFADE_MS).then(() => this._playNext());
        }
        this._segmentDeadline = null;
      }, deadlineMs);
    }

    const { paused, position, track_window } = state;

    // Track ended: paused, at the very start, and there's a track in history
    if (paused && position === 0 && track_window.previous_tracks.length > 0) {
      if (!this._trackEndFired) {
        this._trackEndFired = true;
        // Fade Spotify out while commentary starts (crossfade)
        this._fadeSpotifyVolume(_SPOTIFY_VOLUME, 0, _CROSSFADE_MS).then(() => this._playNext());
      }
    }
  }

  _renderDiagnostics(state) {
    if (!this._diagVisible) {
      if (this._diagEl) this._diagEl.remove();
      this._diagEl = null;
      return;
    }
    // Lazy-create the diagnostic DOM element
    if (!this._diagEl) {
      this._diagEl = document.createElement('div');
      this._diagEl.className = 'spotify-diag';
      const playing = document.getElementById('state-playing');
      if (playing) playing.appendChild(this._diagEl);
    }

    const fmtMs = (ms) => {
      if (ms == null) return '--:--';
      const s = Math.floor(ms / 1000);
      const m = Math.floor(s / 60);
      const sec = s % 60;
      return m + ':' + String(sec).padStart(2, '0');
    };

    const fmtAge = (acquiredAt) => {
      if (!acquiredAt) return '-';
      const ageS = Math.floor((Date.now() - acquiredAt) / 1000);
      return ageS < 60 ? `${ageS}s` : `${Math.floor(ageS / 60)}m${ageS % 60}s`;
    };

    const fmtTime = (ts) => {
      const d = new Date(ts);
      return d.toTimeString().slice(0, 8);
    };
    const escapeHtml = (value) => String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

    const d = {
      paused: state ? (state.paused ? 'yes' : 'no') : 'waiting',
      position: state ? fmtMs(state.position) : '--:--',
      duration: state ? fmtMs(state.duration) : '--:--',
      track: (state?.track_window?.current_track?.name || 'waiting for Spotify state').slice(0, 32),
      deviceId: this.deviceId ? 'yes' : 'NO',
      prevCount: state?.track_window?.previous_tracks?.length ?? '-',
      segType: this.currentItem?.type || '-',
      queueRemaining: this.queue.length,
    };
    const lc = this._lifecycle;

    // Build rows with warn class for critical fields
    const row = (label, value, warn) =>
      `<div class="spotify-diag-row"><span class="spotify-diag-label">${label}</span><span class="spotify-diag-value${warn ? ' warn' : ''}">${value}</span></div>`;

    // Events section — most recent 10 entries, newest first
    const recentEvents = this._obsTimeline.slice(-10).reverse();
    const eventsHtml = recentEvents.length
      ? recentEvents.map(e => `<div class="spotify-diag-event"><span class="spotify-diag-etime">${fmtTime(e.t)}</span> <span class="spotify-diag-ename">${escapeHtml(e.event)}</span>${e.detail ? ` <span class="spotify-diag-edetail">${escapeHtml(e.detail)}</span>` : ''}</div>`).join('')
      : '<div class="spotify-diag-event" style="color:var(--cream-faint)">no events yet</div>';

    this._diagEl.innerHTML =
      row('Online', navigator.onLine ? 'yes' : 'NO', !navigator.onLine) +
      row('Device gen', this._deviceGeneration || '0') +
      row('Device age', fmtAge(this._deviceAcquiredAt)) +
      '<div class="spotify-diag-sep"></div>' +
      row('Paused', d.paused) +
      row('Position', d.position) +
      row('Duration', d.duration) +
      row('Track', d.track) +
      row('Device ID', d.deviceId, d.deviceId === 'NO') +
      row('Prev', d.prevCount) +
      row('Seg type', d.segType) +
      row('Queue', d.queueRemaining) +
      '<div class="spotify-diag-sep"></div>' +
      row('SDK loaded', lc.sdkLoaded ? 'yes' : 'no') +
      row('Player built', lc.playerConstructed ? 'yes' : 'no') +
      row('connect()', lc.connectCalled ? (lc.connectResult || '...') : 'not called', !lc.connectCalled || (lc.connectCalled && !lc.connectResult)) +
      row('ready', lc.ready ? 'yes' : 'no', !lc.ready) +
      row('device_id', lc.deviceId || '-', !lc.deviceId) +
      row('not_ready', lc.notReady ? 'yes' : 'no') +
      row('init_error', lc.initError || '-', !!lc.initError) +
      row('auth_error', lc.authError || '-', !!lc.authError) +
      row('acct_error', lc.accountError ? 'yes' : 'no') +
      row('playback_err', lc.playbackError || '-', !!lc.playbackError) +
      row('autoplay_fail', lc.autoplayFailed ? 'yes' : 'no') +
      row('SecureCtx', lc.isSecureContext ? 'true' : 'false', !lc.isSecureContext) +
      row('Protocol', lc.protocol) +
      row('UA', (lc.userAgent || '').slice(0, 48) + (lc.userAgent && lc.userAgent.length > 48 ? '...' : '')) +
      '<div class="spotify-diag-sep"></div>' +
      '<div class="spotify-diag-section-label">Events</div>' +
      eventsHtml +
      '<div style="display:flex;gap:0.4rem;margin-top:0.5rem;">' +
      '<button class="spotify-diag-refresh" id="spotify-diag-refresh" style="flex:1">Refresh State</button>' +
      '<button class="spotify-diag-refresh" id="spotify-diag-copy" style="flex:1">Copy Timeline</button>' +
      '</div>';

    // Bind refresh button (re-bind every render since innerHTML replaces it)
    const btn = this._diagEl.querySelector('#spotify-diag-refresh');
    if (btn) {
      btn.addEventListener('click', () => this._refreshDiagnostics());
    }
    const copyBtn = this._diagEl.querySelector('#spotify-diag-copy');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => this._copyObsTimeline());
    }
  }

  _copyObsTimeline() {
    const lines = this._obsTimeline.map(e => {
      const d = new Date(e.t);
      const ts = d.toISOString();
      return `${ts} ${e.event}${e.detail ? ' ' + e.detail : ''}`;
    });
    const text = lines.join('\n') || '(no events)';
    navigator.clipboard?.writeText(text).catch(() => {
      // Fallback: show in console if clipboard unavailable
      console.log('[Resonova] Obs Timeline:\n' + text);
    });
  }

  async _refreshDiagnostics() {
    try {
      if (!this.spotifyPlayer) return;
      const state = await this.spotifyPlayer.getCurrentState();
      if (state) this._renderDiagnostics(state);
    } catch (e) {
      console.warn('[Resonova] Refresh diagnostics failed:', e);
    }
  }

  _onPlaybackComplete() {
    if (this.totalItems > 0 && this.completedItems < this.totalItems) {
      this._parkIncompleteEpisode();
      return;
    }
    this._maybeReportMeaningfulReplay();
    if (this._segmentDeadline) {
      clearTimeout(this._segmentDeadline);
      this._segmentDeadline = null;
    }
    document.getElementById('on-air-badge').classList.remove('active');
    document.getElementById('waveform').classList.add('paused');
    this._setNowPlaying('Episode Complete', '');
    this._setSegmentType('');
    document.getElementById('next-up').textContent = 'Thanks for listening.';
    this._updateSkipButton();
    this._clearResumeState();
    this._isPaused = false;
    this._updatePlayPauseButton();
    this._setMediaSessionPlaybackState('none');
    this._updateNowPlayingMiniPanel();
    this._updateSkipMusicButton();
    this._clearReplayTracking();
  }

  // ──────────────────────────────────────────────
  // Library loading
  // ──────────────────────────────────────────────

  _playlistOffset = 0;
  _playlistTotal = Infinity;

  async _loadLibrary() {
    this._loadEpisodes();
    this._loadRecent();
    this._loadPlaylists();
  }

  _closeGenerationStream(stream) {
    if (stream) stream.close();
    if (!stream || this._activeStream === stream) {
      this._activeStream = null;
    }
  }

  _handleGenerationDone(episodeId, stream) {
    this._clearSSEWatchdog();
    this._closeGenerationStream(stream);
    this._pendingEpisodeFocusId = episodeId;
    this._episodesNeedRefresh = true;
    this._generationComplete = true;
    this._clearGenerationSaveCheck();
    this._updateProgress();
    this._updateSkipButton();
    this._refreshEpisodesAfterGeneration(episodeId);
    if (episodeId) this._showFeedbackPanel(episodeId);
  }

  _handleGenerationError(errData = {}, stream) {
    this._clearSSEWatchdog();
    this._closeGenerationStream(stream);
    this._clearGenerationSaveCheck();
    this._generationComplete = true;

    const episodeId = this._activeGenerationId || null;
    this._episodesNeedRefresh = true;
    this._pendingEpisodeFocusId = episodeId;
    this._activeGenerationId = null;
    this._activeGenerationName = '';
    this._activeGenerationSource = '';
    this._showState('connected');

    if (errData.code === 'tts_quota_exhausted') {
      this._showQuotaError(errData);
    } else {
      this._showError(errData.message || 'Generation failed.');
    }
  }

  async _refreshEpisodesAfterGeneration(episodeId) {
    const loadedFresh = await this._loadEpisodes({ focusEpisodeId: episodeId });
    if (loadedFresh) {
      this._episodesNeedRefresh = false;
      // Do NOT clear _pendingEpisodeFocusId here — keep it so that when the user
      // enters the connected state the list re-loads and scrolls to the new episode.
    }

    if (!episodeId) return;
    try {
      const ep = await this._apiFetch(`/api/episodes/${episodeId}`);
      localStorage.setItem(`resonova:episode:${episodeId}`, JSON.stringify({ ts: Date.now(), ep }));
    } catch (e) {
      console.warn('Failed to cache completed episode detail:', e);
    }
  }

  _scheduleGenerationSaveCheck(episodeId) {
    this._clearGenerationSaveCheck();
    if (!episodeId) return;

    let attempts = 0;
    this._generationSaveCheck = setInterval(async () => {
      if (this._generationComplete) {
        this._clearGenerationSaveCheck();
        return;
      }

      attempts++;
      try {
        await this._apiFetch(`/api/episodes/${episodeId}`);
        this._generationComplete = true;
        this._pendingEpisodeFocusId = episodeId;
        this._episodesNeedRefresh = true;
        this._updateProgress();
        this._updateSkipButton();
        this._refreshEpisodesAfterGeneration(episodeId);
        this._clearGenerationSaveCheck();
      } catch (_) {
        if (attempts >= 20) this._clearGenerationSaveCheck();
      }
    }, 1000);
  }

  _clearGenerationSaveCheck() {
    if (!this._generationSaveCheck) return;
    clearInterval(this._generationSaveCheck);
    this._generationSaveCheck = null;
  }

  _clearSSEWatchdog() {
    if (!this._sseWatchdog) return;
    clearInterval(this._sseWatchdog);
    this._sseWatchdog = null;
  }

  _refreshCurrentGenerationInLibrary() {
    if (!this._activeGenerationId) return;
    if (!document.getElementById('state-connected')?.classList.contains('active')) return;
    this._loadEpisodes({ focusEpisodeId: this._activeGenerationId });
  }

  async _loadEpisodes(options = {}) {
    const focusEpisodeId = options.focusEpisodeId || null;
    let episodes = null;
    let fromCache = false;
    try {
      const data = await this._apiFetch(`/api/episodes?_=${Date.now()}`, { cache: 'no-store' });
      episodes = data.episodes;
      try {
        localStorage.setItem('resonova:episodes-cache', JSON.stringify({ ts: Date.now(), episodes }));
      } catch { /* quota exceeded */ }
    } catch (e) {
      console.warn('Failed to load past episodes:', e);
      try {
        const raw = localStorage.getItem('resonova:episodes-cache');
        if (raw) {
          const cached = JSON.parse(raw);
          episodes = cached.episodes;
          fromCache = true;
        }
      } catch { /* ignore */ }
      if (!episodes) return false;
    }
    this._episodes = episodes;

    const container = document.getElementById('past-episodes');
    if (!container) return false;

    const activeGeneration = this._currentGenerationEpisode();

    if ((!episodes || !episodes.length) && !activeGeneration) {
      container.innerHTML = '';
      document.getElementById('section-episodes').classList.remove('loaded');
      return !fromCache;
    }

    // Group episodes by playlist_uri; custom track-list casts go under a separate bucket.
    const groups = new Map();
    for (const ep of episodes) {
      const isPlaylist = ep.playlist_uri && ep.playlist_uri.startsWith('spotify:playlist:');
      const key = isPlaylist ? ep.playlist_uri : '__custom__';
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          name: isPlaylist ? (ep.playlist_name || 'Unnamed Playlist') : 'Custom Casts',
          isCustom: !isPlaylist,
          episodes: [],
          latestDate: ep.created_at,
        });
      }
      const g = groups.get(key);
      g.episodes.push(ep);
      if (ep.created_at > g.latestDate) g.latestDate = ep.created_at;
    }

    // Sort groups newest-first; expand only the most recent group by default.
    const sortedGroups = [...groups.values()].sort(
      (a, b) => b.latestDate.localeCompare(a.latestDate)
    );

    const activeGenerationSaved = !!(activeGeneration && episodes.some(ep => ep.id === activeGeneration.id));
    if (activeGenerationSaved) {
      this._activeGenerationId = null;
      this._activeGenerationName = '';
      this._activeGenerationSource = '';
    }

    const focusGroupKey = focusEpisodeId
      ? sortedGroups.find(g => g.episodes.some(ep => ep.id === focusEpisodeId))?.key
      : null;
    const currentHtml = activeGeneration && !activeGenerationSaved
      ? this._currentGenerationGroupHTML(activeGeneration)
      : '';
    container.innerHTML = currentHtml + sortedGroups.map((g, i) => {
      const expanded = focusGroupKey ? g.key === focusGroupKey : i === 0;
      return this._episodeGroupHTML(g, expanded, focusEpisodeId);
    }).join('');

    document.querySelectorAll('.cache-notice').forEach(el => el.remove());
    if (fromCache) {
      const notice = document.createElement('div');
      notice.className = 'cache-notice';
      notice.textContent = 'Offline — showing saved casts from cache';
      container.before(notice);
    }

    document.getElementById('section-episodes').classList.add('loaded');
    if (focusEpisodeId) {
      requestAnimationFrame(() => {
        const card = [...container.querySelectorAll('.episode-card')]
          .find(el => el.dataset.episodeId === focusEpisodeId);
        if (card && document.getElementById('state-connected')?.classList.contains('active')) {
          card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
      });
    }
    return !fromCache;
  }

  _episodeGroupHTML(group, expanded, focusEpisodeId = null) {
    const latestDate = new Date(group.latestDate).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
    });
    const count = group.episodes.length;
    const castLabel = count === 1 ? '1 cast' : `${count} casts`;
    return `
      <div class="ep-group${expanded ? ' expanded' : ''}">
        <div class="ep-group-header" data-group-toggle>
          <span class="ep-group-chevron" aria-hidden="true">${expanded ? '▾' : '▸'}</span>
          <span class="ep-group-name">${this._esc(group.name)}</span>
          <span class="ep-group-meta">${this._esc(castLabel)} · ${this._esc(latestDate)}</span>
        </div>
        <div class="ep-group-body">
          <div class="ep-group-cards">
            ${group.episodes.map(ep => this._episodeCardHTML(ep, ep.id === focusEpisodeId)).join('')}
          </div>
        </div>
      </div>
    `;
  }

  _currentGenerationEpisode() {
    if (!this._activeGenerationId) return null;
    return {
      id: this._activeGenerationId,
      name: this._activeGenerationName || 'Generating cast',
      source: this._activeGenerationSource || 'Current source',
      completedItems: this.completedItems,
      totalItems: this.totalItems,
      status: this._generationComplete ? 'Saving' : 'Generating',
    };
  }

  _currentGenerationGroupHTML(ep) {
    const progress = ep.totalItems > 0
      ? `Segment ${ep.completedItems}/${ep.totalItems}`
      : 'Starting';
    return `
      <div class="ep-group expanded" data-current-generation-id="${this._esc(ep.id)}">
        <div class="ep-group-header">
          <span class="ep-group-chevron" aria-hidden="true">▾</span>
          <span class="ep-group-name">Current Cast</span>
          <span class="ep-group-meta">${this._esc(ep.status)} · ${this._esc(progress)}</span>
        </div>
        <div class="ep-group-body">
          <div class="ep-group-cards">
            <div class="episode-card episode-card-new" data-current-generation-card>
              <div class="episode-card-main">
                <div class="episode-card-name">${this._esc(ep.name)}</div>
                <div class="episode-card-meta">
                  ${this._esc(ep.source)} · ${this._esc(progress)}
                  <span class="ep-new-badge">${this._esc(ep.status)}</span>
                  <span class="ep-new-badge">Open progress</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _episodeCardHTML(ep, isNew = false) {
    const date = new Date(ep.created_at).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
    });
    const time = new Date(ep.created_at).toLocaleTimeString(undefined, {
      hour: '2-digit', minute: '2-digit',
    });

    const isPlaylistEpisode = ep.playlist_uri && ep.playlist_uri.startsWith('spotify:playlist:');

    const runBadge = isPlaylistEpisode && ep.run_number != null
      ? `<span class="ep-run-badge">Run #${ep.run_number}</span>`
      : '';

    const newBadge = isNew
      ? '<span class="ep-new-badge">New</span>'
      : '';

    const quotaBadge = ep.status === 'quota_failed'
      ? '<span class="ep-quota-badge">⚠ Incomplete</span>'
      : '';

    const genFailedBadge = ep.status === 'gen_failed'
      ? '<span class="ep-quota-badge">⚠ Incomplete</span>'
      : '';

    const fingerprintBadge = ep.order_fingerprint
      ? `<span class="ep-fingerprint" title="Order fingerprint">${this._esc(ep.order_fingerprint)}</span>`
      : '';

    const replayBadge = ep.replay_count > 0
      ? `<span class="ep-run-badge">Replayed ${ep.replay_count}x</span>`
      : '';

    const preview = ep.track_order_preview && ep.track_order_preview.length
      ? `<div class="ep-preview">${ep.track_order_preview.map(s => this._esc(s)).join(' · ')}</div>`
      : '';

    const taglineHTML = ep.tagline
      ? `<div class="episode-card-tagline">${this._esc(ep.tagline)}</div>`
      : '';

    const coverGradient = this._coverGradient(ep.order_fingerprint || ep.id);
    const initial = ep.name ? ep.name.trim().charAt(0).toUpperCase() : '';

    return `
      <div class="episode-card${isNew ? ' episode-card-new' : ''}" data-episode-id="${ep.id}">
        <div class="episode-card-cover" style="background: ${coverGradient}">
          <span class="episode-card-cover-initial">${this._esc(initial)}</span>
        </div>
        <div class="episode-card-main">
          <div class="episode-card-name">${this._esc(ep.name)}</div>
          ${taglineHTML}
          <div class="episode-card-meta">
            ${this._esc(ep.playlist_name)} · ${ep.track_count} tracks · ${date} ${time}
            ${newBadge}${runBadge}${replayBadge}${quotaBadge}${genFailedBadge}${fingerprintBadge}
          </div>
          ${preview}
        </div>
        <div class="episode-card-actions" role="group" aria-label="Episode actions">
          <button class="ep-btn ep-btn-play" data-action="play" data-episode-id="${ep.id}" title="Play this episode">▶ Play</button>
          <button class="ep-btn ep-btn-share" data-action="share" data-episode-id="${ep.id}" title="Copy episode blurb">📋 Copy</button>
          <button class="ep-btn ep-btn-rename" data-action="rename" data-episode-id="${ep.id}" title="Rename episode">✏</button>
          <button class="ep-btn ep-btn-delete" data-action="delete" data-episode-id="${ep.id}" title="Delete episode">🗑</button>
        </div>
      </div>
    `;
  }

  async _renameEpisode(episodeId) {
    const card = document.querySelector(`.episode-card[data-episode-id="${episodeId}"]`);
    const currentName = card ? card.querySelector('.episode-card-name')?.textContent : '';
    const newName = prompt('Rename episode:', currentName || '');
    if (newName === null) return; // cancelled
    const trimmed = newName.trim();
    if (!trimmed) { alert('Name cannot be empty.'); return; }
    try {
      await this._apiFetch(`/api/episodes/${episodeId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      await this._loadEpisodes();
    } catch (err) {
      this._showError('Rename failed: ' + err.message);
    }
  }

  _coverGradient(seed) {
    let hash = 0;
    const str = String(seed || '');
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    const h1 = Math.abs(hash) % 360;
    const h2 = (h1 + 60 + (Math.abs(hash >> 8) % 240)) % 360;
    const s1 = 55 + (Math.abs(hash >> 4) % 16);
    const s2 = 55 + (Math.abs(hash >> 12) % 16);
    const l1 = 40 + (Math.abs(hash >> 16) % 16);
    const l2 = 40 + (Math.abs(hash >> 20) % 16);
    return `linear-gradient(135deg, hsl(${h1}, ${s1}%, ${l1}%) 0%, hsl(${h2}, ${s2}%, ${l2}%) 100%)`;
  }

  async _shareEpisode(episodeId) {
    let ep = this._episodes?.find(e => e.id === episodeId);
    if (!ep) {
      ep = await this._loadSavedEpisode(episodeId);
    }
    if (!ep) return;

    const title = ep.name || 'Resonova Cast';
    const tagline = ep.tagline ? ep.tagline.trim() : '';
    const playlistName = ep.playlist_name ? ep.playlist_name.trim() : '';
    const trackCount = ep.track_count;

    let blurb = title;
    if (tagline) {
      blurb += ` — ${tagline}`;
    }
    const parts = [];
    if (playlistName) parts.push(playlistName);
    if (trackCount != null) parts.push(`${trackCount} tracks`);
    if (parts.length > 0) {
      blurb += ` · ${parts.join(' · ')}`;
    }

    try {
      await navigator.clipboard.writeText(blurb);
      this._showToast('Copied to clipboard ✓');
    } catch {
      this._showError('Could not copy to clipboard');
    }
  }

  _showToast(msg) {
    let toast = document.getElementById('resonova-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'resonova-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('visible');
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => toast.classList.remove('visible'), 2500);
  }

  async _deleteEpisode(episodeId) {
    const card = document.querySelector(`.episode-card[data-episode-id="${episodeId}"]`);
    const name = card ? card.querySelector('.episode-card-name')?.textContent : 'this episode';
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await this._apiFetch(`/api/episodes/${episodeId}`, { method: 'DELETE' });
      await this._loadEpisodes();
    } catch (err) {
      this._showError('Delete failed: ' + err.message);
    }
  }

  async _playEpisode(episodeId) {
    this._episodeId = episodeId;
    try {
      const ep = await this._apiFetch(`/api/episodes/${episodeId}`);
      try {
        localStorage.setItem(`resonova:episode:${episodeId}`, JSON.stringify({ ts: Date.now(), ep }));
      } catch { /* quota exceeded */ }
      this._startPlayback(ep.queue, { replayEpisodeId: episodeId });
    } catch (err) {
      try {
        const raw = localStorage.getItem(`resonova:episode:${episodeId}`);
        if (raw) {
          const cached = JSON.parse(raw);
          this._startPlayback(cached.ep.queue, { replayEpisodeId: episodeId });
          return;
        }
      } catch { /* ignore */ }
      this._showError('Could not load episode: ' + err.message);
    }
  }

  async _loadRecent() {
    try {
      const { playlists } = await this._apiFetch('/api/recent');
      if (!playlists.length) return;
      const container = document.getElementById('recent-playlists');
      container.innerHTML = playlists.map(p => this._featuredCardHTML(p)).join('');
      document.getElementById('section-recent').classList.add('loaded');
    } catch (e) { console.warn('Failed to load recent plays:', e); }
  }

  _maybeReportMeaningfulReplay() {
    if (!this._replaySessionId || this._replayMeaningfulSent) return;
    if (!this._replaySavedEpisodeId) return;
    const total = this._replayTotalSegments || this.totalItems;
    if (total <= 0 || this.completedItems / total < 0.5) return;
    this._replayMeaningfulSent = true;
    const episodeId = this._replaySavedEpisodeId;
    const sessionId = this._replaySessionId;
    this._apiFetch(`/api/episodes/${episodeId}/replay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'meaningful',
        session_id: sessionId,
        completed_segments: this.completedItems,
        total_segments: total,
      }),
    }).catch(() => { /* non-blocking */ });
  }

  _beginReplayTracking(episodeId, totalSegments) {
    const sessionId = (window.crypto && typeof window.crypto.randomUUID === 'function')
      ? window.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    this._replaySessionId = sessionId;
    this._replayMeaningfulSent = false;
    this._replaySavedEpisodeId = episodeId;
    this._replayTotalSegments = totalSegments || 0;
    this._apiFetch(`/api/episodes/${episodeId}/replay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'start',
        session_id: sessionId,
        completed_segments: 0,
        total_segments: this._replayTotalSegments,
      }),
    }).catch(() => { /* non-blocking */ });
  }

  _clearReplayTracking() {
    this._replaySessionId = null;
    this._replayMeaningfulSent = false;
    this._replaySavedEpisodeId = null;
    this._replayTotalSegments = 0;
  }

  async _loadPlaylists() {
    try {
      const data = await this._apiFetch(`/api/playlists?limit=50&offset=${this._playlistOffset}`);
      this._playlistTotal = data.total;
      this._playlistOffset += data.items.length;

      const container = document.getElementById('user-playlists');
      container.insertAdjacentHTML('beforeend',
        data.items.map(p => this._playlistCardHTML(p)).join('')
      );
      document.getElementById('section-playlists').classList.add('loaded');

      const btn = document.getElementById('load-more-playlists');
      btn.style.display = this._playlistOffset < this._playlistTotal ? '' : 'none';
    } catch (e) { console.warn('Failed to load playlists:', e); }
  }

  _playlistCardHTML(p) {
    return `
      <div class="playlist-card" data-uri="${p.uri}">
        ${p.image ? `<img class="playlist-card-img" src="${p.image}" alt="" loading="lazy">` : '<div class="playlist-card-img"></div>'}
        <div class="playlist-card-body">
          <div class="playlist-card-name" title="${this._esc(p.name)}">${this._esc(p.name)}</div>
          <div class="playlist-card-meta">${p.track_count} tracks · ${this._esc(p.owner)}</div>
        </div>
      </div>
    `;
  }

  _featuredCardHTML(p) {
    return `
      <div class="featured-card playlist-card" data-uri="${p.uri}">
        ${p.image ? `<img class="featured-card-img" src="${p.image}" alt="">` : '<div class="featured-card-img"></div>'}
        <div class="featured-card-info">
          <div class="featured-card-name">${this._esc(p.name)}</div>
          <div class="featured-card-meta">${p.track_count} tracks · Updated weekly</div>
        </div>
      </div>
    `;
  }

  _esc(str) {
    const el = document.createElement('span');
    el.textContent = str ?? '';
    return el.innerHTML;
  }

  _handlePlaylistClick(uri) {
    const input = document.getElementById('playlist-uri');
    input.value = uri;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    // Quick one-click: generate immediately. This goes through the form submit
    // handler -> generate(), which reads the current language/incognito options,
    // so card clicks already respect whatever is set on the form.
    document.getElementById('generate-form').requestSubmit();
  }

  // ──────────────────────────────────────────────
  // UI helpers
  // ──────────────────────────────────────────────

  _showState(name, options = {}) {
    document.querySelectorAll('.state').forEach(el => el.classList.remove('active'));
    const el = document.getElementById(`state-${name}`);
    if (el) {
      el.classList.add('active');
      if (name === 'playing' && !document.getElementById('diag-toggle')) {
        document.getElementById('on-air-badge')?.appendChild(this._createDiagToggle());
      }
    }
    if (name === 'connected') {
      const now = Date.now();
      const focusId = options.focusEpisodeId || this._pendingEpisodeFocusId || this._episodeId || null;
      // Refresh whenever: (a) flag set by generation, (b) pending focus episode to scroll to,
      // or (c) more than 8 s since last refresh (catches SSE-drop / back-navigation scenarios).
      const shouldRefresh =
        options.forceRefreshEpisodes ||
        this._episodesNeedRefresh ||
        !!focusId ||
        (now - this._lastConnectedRefresh) > 8000;
      if (shouldRefresh) {
        this._lastConnectedRefresh = now;
        this._loadEpisodes({ focusEpisodeId: focusId }).then((loadedFresh) => {
          if (loadedFresh) {
            this._episodesNeedRefresh = false;
            if (focusId && this._pendingEpisodeFocusId === focusId) {
              this._pendingEpisodeFocusId = null;
            }
          }
        });
      }
    }
    this._updateNowPlayingMiniPanel(name);
  }

  _updateNowPlayingMiniPanel(stateName = null) {
    const trail = document.getElementById('now-playing-trail');
    if (!trail) return;

    // Determine effective state: use passed name if available, else read DOM
    const inLibrary = stateName !== null
      ? stateName === 'connected'
      : document.getElementById('state-connected')?.classList.contains('active');

    if (!inLibrary || !this.currentItem) {
      trail.style.display = 'none';
      return;
    }

    // Determine segment type label
    let typeLabel = '';
    let typeClass = '';
    if (this._spotifyRecoveryFailed || this._spotifyUnhealthy) {
      typeLabel = 'Recover needed';
      typeClass = 'npt-type--recover';
    } else if (this._isPaused) {
      typeLabel = 'Paused';
      typeClass = 'npt-type--paused';
    } else if (this._segmentType === 'commentary') {
      typeLabel = 'AI Commentary';
      typeClass = 'npt-type--commentary';
    } else if (this._segmentType === 'spotify') {
      typeLabel = 'Spotify';
      typeClass = 'npt-type--spotify';
    }

    const typeEl = document.getElementById('npt-type');
    const titleEl = document.getElementById('npt-title');
    const artistEl = document.getElementById('npt-artist');
    const progressEl = document.getElementById('npt-progress');

    if (typeEl) { typeEl.textContent = typeLabel; typeEl.className = 'npt-type ' + typeClass; }
    if (titleEl) titleEl.textContent = this._nowPlayingTitle || '';
    if (artistEl) artistEl.textContent = this._nowPlayingArtist || '';
    if (progressEl) {
      progressEl.textContent = this.totalItems > 0
        ? `${this.completedItems} / ${this.totalItems} segments`
        : '';
    }

    trail.style.display = '';
  }

  _showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.classList.add('visible');
    setTimeout(() => el.classList.remove('visible'), 6000);
  }

  _showQuotaError(data) {
    // Remove any existing quota banner so this call is idempotent
    document.getElementById('quota-error-banner')?.remove();

    const retryStr = data.retry_after_seconds ? this._formatDuration(data.retry_after_seconds) : '';

    // Persist cooldown in localStorage so the next generate() call is blocked client-side
    if (data.retry_after_seconds && data.retry_after_seconds > 0) {
      try {
        localStorage.setItem('resonova:tts-cooldown', JSON.stringify({
          until: Date.now() + data.retry_after_seconds * 1000,
          model: data.model || '',
          message: data.message || '',
        }));
      } catch (_) { }
    }

    const banner = document.createElement('div');
    banner.id = 'quota-error-banner';
    banner.className = 'quota-error-banner';
    banner.innerHTML = `
      <div class="quota-error-icon">⏸</div>
      <div class="quota-error-body">
        <div class="quota-error-title">Generation paused — Gemini TTS quota exhausted</div>
        ${data.model ? `<div class="quota-error-model">Model: ${this._esc(data.model)}</div>` : ''}
        ${retryStr ? `<div class="quota-error-retry">Retry after about ${this._esc(retryStr)}</div>` : ''}
        <div class="quota-error-note">Generated segments so far are saved.</div>
      </div>
      <button class="quota-error-dismiss" type="button" aria-label="Dismiss">✕</button>
    `;
    banner.querySelector('.quota-error-dismiss').addEventListener('click', () => banner.remove());

    // Insert before the error-msg element inside state-connected
    const errorEl = document.getElementById('error-msg');
    if (errorEl && errorEl.parentNode) {
      errorEl.parentNode.insertBefore(banner, errorEl);
    }
  }

  _formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins === 0 ? `${hours}h` : `${hours}h ${mins}m`;
  }

  _setNowPlaying(title, artist) {
    this._nowPlayingTitle = title;
    this._nowPlayingArtist = artist;
    document.getElementById('now-playing-title').textContent = title;
    document.getElementById('now-playing-artist').textContent = artist;

    const titleEl = document.getElementById('now-playing-title');
    if (title === 'AI Commentary') {
      titleEl.classList.add('italic');
    } else {
      titleEl.classList.remove('italic');
    }
    this._updateMediaSession(title, artist);
    this._updateNowPlayingMiniPanel();
  }

  _setSegmentType(type) {
    const el = document.getElementById('segment-type');
    el.className = 'segment-type ' + (type || '');
    const labels = { commentary: 'AI Commentary', spotify: 'Now Playing', '': '' };
    el.querySelector('.segment-type-label').textContent = labels[type] ?? '';
    this._segmentType = type;
    this._updateNowPlayingMiniPanel();
  }

  _updateProgress() {
    const pct = this.totalItems > 0
      ? Math.round((this.completedItems / this.totalItems) * 100)
      : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
    const suffix = this._generationComplete ? '' : ' · generating…';
    document.getElementById('progress-label').textContent =
      `${this.completedItems} / ${this.totalItems} segments${suffix}`;
    this._updateNowPlayingMiniPanel();
  }

  _updateSkipButton() {
    // Disable skip when there's nothing queued yet and more is still being synthesized.
    // Skipping into an empty queue while generating would stall playback.
    const blocked = this.queue.length === 0 && !this._generationComplete;
    const btn = document.getElementById('skip-btn');
    btn.disabled = blocked;
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
      const hasPrevious = this._hasPreviousSegment();
      prevBtn.setAttribute('aria-disabled', hasPrevious ? 'false' : 'true');
      prevBtn.title = hasPrevious ? 'Go to previous segment' : 'No previous segment yet';
    }
  }

  _hasPreviousSegment() {
    return !!this.currentItem && (this.currentIndex > 0 || this.playedItems.length > 0);
  }

  _updateProgressStep(step, message) {
    const stepId = STEP_MAP[step] ?? step;

    // Mark all previous steps as done
    const allIds = ['step-fetch', 'step-research', 'step-script', 'step-tts'];
    const idx = allIds.indexOf(stepId);
    allIds.forEach((id, i) => {
      const stepEl = document.getElementById(id);
      if (!stepEl) return;
      if (i < idx) {
        stepEl.classList.remove('active');
        stepEl.classList.add('done');
        stepEl.querySelector('.step-icon').textContent = '✓';
      } else if (i === idx) {
        stepEl.classList.add('active');
        stepEl.classList.remove('done');
        stepEl.querySelector('.step-message').textContent = message ?? '';
      }
    });
  }

  _markAllStepsDone() {
    ['step-fetch', 'step-script', 'step-tts'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove('active');
      el.classList.add('done');
      el.querySelector('.step-icon').textContent = '✓';
    });
  }

  // ──────────────────────────────────────────────
  // Utilities
  // ──────────────────────────────────────────────

  _parseInput(input) {
    input = (input ?? '').trim();

    // Multiple track URLs/URIs (one per line, from cmd-A cmd-C in a playlist)
    const lines = input.split(/\n/).map(l => l.trim()).filter(Boolean);
    if (lines.length > 1) {
      const trackUris = [];
      for (const line of lines) {
        const m = line.match(/spotify\.com\/track\/([a-zA-Z0-9]+)/);
        if (m) { trackUris.push(`spotify:track:${m[1]}`); continue; }
        if (/^spotify:track:[a-zA-Z0-9]+$/.test(line)) { trackUris.push(line); continue; }
        // Not a track line — bail out
        return null;
      }
      if (trackUris.length > 0) return { track_uris: trackUris };
    }

    // Single playlist URL
    const urlMatch = input.match(/spotify\.com\/playlist\/([a-zA-Z0-9]+)/);
    if (urlMatch) return { playlist_uri: `spotify:playlist:${urlMatch[1]}` };
    // Already a URI
    if (/^spotify:playlist:[a-zA-Z0-9]+$/.test(input)) return { playlist_uri: input };
    // Raw ID
    if (/^[a-zA-Z0-9]{22}$/.test(input)) return { playlist_uri: `spotify:playlist:${input}` };
    return null;
  }

  async _apiFetch(url, options = {}) {
    let res;
    try {
      res = await this._fetchWithTimeout(url, options, 12000);
    } catch (netErr) {
      const kind = !navigator.onLine ? 'offline' : 'network';
      if (url.startsWith('/')) this._updateNetworkStatus(kind);
      const err = new Error(kind === 'offline'
        ? `Offline — cannot reach ${url}`
        : `Network error: ${url}`);
      err.kind = kind;
      throw err;
    }
    if (!res.ok) {
      let errBody = null;
      try { errBody = await res.json(); } catch (_) { }
      const detail = errBody && errBody.detail;
      const msg = typeof detail === 'string' ? detail
        : (detail ? JSON.stringify(detail) : `${res.status} ${res.statusText}`);
      const err = new Error(msg);
      err.kind = 'http';
      err.status = res.status;
      err.body = errBody;
      throw err;
    }
    if (url.startsWith('/')) this._clearNetworkStatus();
    return res.json();
  }

  async _fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  // ──────────────────────────────────────────────
  // Skip & crossfade
  // ──────────────────────────────────────────────

  skip() {
    if (!this.currentItem) return;
    if (this.currentItem.type === 'audio') {
      this._crossfadeTriggered = true;
      this.audioEl.ontimeupdate = null;
      this.audioEl.pause();
      this.audioEl.onended = null;
      this._playNext();
    } else if (this.currentItem.type === 'spotify') {
      if (!this._trackEndFired) {
        this._trackEndFired = true;
        this.spotifyPlayer?.pause();
        this._playNext();
      }
    }
  }

  async previous() {
    if (!this._hasPreviousSegment()) return;

    const fallbackItem = this.playedItems[this.playedItems.length - 1];
    let previousIndex = this.currentIndex > 0
      ? this.currentIndex - 1
      : this.playbackTimeline.indexOf(fallbackItem);
    const previousItem = previousIndex >= 0
      ? this.playbackTimeline[previousIndex]
      : fallbackItem;
    if (!previousItem) return;

    if (previousItem.type === 'spotify' && !this._isSpotifyHealthy()) {
      console.warn('[Resonova] Spotify recovery triggered due to unhealthy state before previous navigation.');
      const success = await this._recoverSpotifySession();
      if (!success) {
        console.error('[Resonova] Spotify recovery failed during previous navigation.');
        this._spotifyRecoveryFailed = true;
        this._updateRecoveryControl();
        return;
      }
    }

    if (this._segmentDeadline) {
      clearTimeout(this._segmentDeadline);
      this._segmentDeadline = null;
    }

    if (this.currentItem.type === 'audio') {
      this._crossfadeTriggered = true;
      this.audioEl.ontimeupdate = null;
      this.audioEl.onended = null;
      this.audioEl.pause();
    } else if (this.currentItem.type === 'spotify') {
      this.spotifyPlayer?.pause();
    }

    this.playedItems.pop();
    this.queue = previousIndex >= 0
      ? this.playbackTimeline.slice(previousIndex)
      : [previousItem, this.currentItem, ...this.queue];
    this.currentItem = null;
    this.currentIndex = previousIndex - 1;
    this.completedItems = Math.max(0, previousIndex >= 0 ? previousIndex : this.completedItems - 2);
    this._trackEndFired = false;
    this._playNext();
  }

  // Ramp HTML audio element volume from → to over durationMs
  _fadeAudioVolume(from, to, durationMs) {
    const steps = Math.max(1, Math.round(durationMs / 50));
    const stepMs = durationMs / steps;
    let step = 0;
    const id = setInterval(() => {
      step++;
      this.audioEl.volume = Math.max(0, Math.min(1, from + (to - from) * (step / steps)));
      if (step >= steps) clearInterval(id);
    }, stepMs);
  }

  // Ramp Spotify player volume from → to over durationMs, returns a Promise
  async _fadeSpotifyVolume(from, to, durationMs) {
    if (!this.spotifyPlayer) return;
    // Cap step count so background-throttled setTimeout
    // doesn't balloon the fade to 20+ seconds.
    // Each step is roughly one second at most for short fades.
    const steps = Math.min(20, Math.max(1, Math.ceil(durationMs / 1000)));
    const stepMs = durationMs / steps;
    for (let i = 0; i <= steps; i++) {
      const v = Math.max(0, Math.min(1, from + (to - from) * (i / steps)));
      try { await this.spotifyPlayer.setVolume(v); } catch { /* ignore */ }
      if (i < steps) await new Promise(r => setTimeout(r, stepMs));
    }
  }

  // ──────────────────────────────────────────────
  // LocalStorage cache for Spotify metadata
  // ──────────────────────────────────────────────

  _cacheGet(uri) {
    try {
      const raw = localStorage.getItem(`sc:${uri}`);
      if (!raw) return null;
      const entry = JSON.parse(raw);
      // Expire after 7 days
      if (Date.now() - entry.ts > 7 * 86400000) {
        localStorage.removeItem(`sc:${uri}`);
        return null;
      }
      return entry.data;
    } catch { return null; }
  }

  _cacheSet(uri, data) {
    try {
      localStorage.setItem(`sc:${uri}`, JSON.stringify({ ts: Date.now(), data }));
    } catch { /* quota exceeded — ignore */ }
  }

  // ──────────────────────────────────────────────
  // Network status indicator
  // ──────────────────────────────────────────────

  _updateNetworkStatus(kind) {
    const el = document.getElementById('network-status');
    if (!el) return;
    const msgs = { offline: 'Offline — saved casts only', network: 'Connection unstable' };
    el.textContent = msgs[kind] || 'Connection unstable';
    el.dataset.kind = kind;
    el.style.display = '';
    this._obsRecord('network:status', kind);
  }

  _clearNetworkStatus() {
    const el = document.getElementById('network-status');
    if (!el || el.style.display === 'none') return;
    el.style.display = 'none';
    this._obsRecord('network:clear', '');
  }

  // ──────────────────────────────────────────────
  // Skip Music button visibility
  // ──────────────────────────────────────────────

  _updateSkipMusicButton() {
    const btn = document.getElementById('skip-music-btn');
    if (!btn) return;
    if (!btn._wired) {
      btn.addEventListener('click', () => this.skip());
      btn._wired = true;
    }
    const shouldShow = this.currentItem?.type === 'spotify' &&
      (this._spotifyUnhealthy || this._spotifyRecoveryFailed || !navigator.onLine || !!this._pendingUnlockItem);
    btn.style.display = shouldShow ? '' : 'none';
  }
}

// ──────────────────────────────────────────────
// Bootstrap
// ──────────────────────────────────────────────

// Duration of the volume fade at segment transitions (ms)
const _CROSSFADE_MS = 1800;
// Spotify masters are usually much louder than generated commentary.
const _SPOTIFY_VOLUME = 0.62;

const resonova = new ResonovaPlayer();
window.resonova = resonova;

document.addEventListener('DOMContentLoaded', () => {
  resonova.init();

  // Generate form submission
  document.getElementById('generate-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.textContent = 'Starting...';
    await resonova.generate(document.getElementById('playlist-uri').value);
    btn.disabled = false;
    btn.textContent = 'Generate Cast';
  });

  const languageSelect = document.getElementById('commentary-language');
  const languageCustom = document.getElementById('commentary-language-custom');
  if (languageSelect && languageCustom) {
    languageSelect.addEventListener('change', () => {
      const isCustom = languageSelect.value === 'custom';
      languageCustom.style.display = isCustom ? '' : 'none';
      if (isCustom) languageCustom.focus();
    });
  }

  // Restore last-selected cast lenses from localStorage
  try {
    const savedDepth = localStorage.getItem('resonova:cast-depth');
    const depthSelect = document.getElementById('cast-depth');
    if (savedDepth && depthSelect) depthSelect.value = savedDepth;

    const savedVibe = localStorage.getItem('resonova:cast-vibe');
    const vibeSelect = document.getElementById('cast-vibe');
    if (savedVibe && vibeSelect) vibeSelect.value = savedVibe;
  } catch (_) {}

  // Auto-resize textarea and allow pasting multi-line track lists
  const textarea = document.getElementById('playlist-uri');
  const autoResize = () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
    textarea.style.overflowY = textarea.scrollHeight > 160 ? 'auto' : 'hidden';
  };
  textarea.addEventListener('input', autoResize);
  textarea.addEventListener('paste', () => setTimeout(autoResize, 0));

  // Playlist card clicks (delegated — covers recent, featured, and library)
  document.getElementById('state-connected').addEventListener('click', (e) => {
    // Accordion group header toggle
    const groupHeader = e.target.closest('[data-group-toggle]');
    if (groupHeader) {
      const group = groupHeader.closest('.ep-group');
      if (group) {
        const wasExpanded = group.classList.contains('expanded');
        group.classList.toggle('expanded');
        const chevron = groupHeader.querySelector('.ep-group-chevron');
        if (chevron) chevron.textContent = wasExpanded ? '▸' : '▾';
      }
      return;
    }

    // Episode action buttons (play, rename, delete) — check before general card click
    const actionBtn = e.target.closest('[data-action]');
    if (actionBtn) {
      e.stopPropagation();
      const action = actionBtn.dataset.action;
      const id = actionBtn.dataset.episodeId;
      if (action === 'play') resonova._playEpisode(id);
      else if (action === 'share') resonova._shareEpisode(id);
      else if (action === 'rename') resonova._renameEpisode(id);
      else if (action === 'delete') resonova._deleteEpisode(id);
      return;
    }

    // Clicking anywhere else on an episode card plays it (but not inside action area)
    const episodeCard = e.target.closest('.episode-card');
    if (episodeCard && episodeCard.dataset.episodeId && !e.target.closest('.episode-card-actions')) {
      resonova._playEpisode(episodeCard.dataset.episodeId);
      return;
    }

    const currentGenerationCard = e.target.closest('[data-current-generation-card]');
    if (currentGenerationCard && resonova._activeGenerationId && !resonova._generationComplete) {
      resonova._pushHistoryState('generating');
      resonova._showState('generating');
      return;
    }

    const card = e.target.closest('.playlist-card');
    if (card) {
      resonova._handlePlaylistClick(card.dataset.uri);
    }
  });

  // Back-to-library buttons
  document.getElementById('back-to-library-btn').addEventListener('click', () => {
    resonova._showState('connected', { forceRefreshEpisodes: true });
  });

  document.getElementById('back-from-generating-btn').addEventListener('click', () => {
    // Keep the active SSE stream open so the library card and completion state
    // continue to update while generation runs in the background.
    resonova._showState('connected', { forceRefreshEpisodes: true });
  });

  document.getElementById('return-to-player-btn').addEventListener('click', () => {
    resonova._pushHistoryState('playing');
    resonova._showState('playing');
  });

  // Skip button
  document.getElementById('prev-btn').addEventListener('click', () => {
    resonova.previous();
  });

  document.getElementById('play-pause-btn')?.addEventListener('click', () => {
    resonova.togglePlayPause();
  });

  document.getElementById('skip-btn').addEventListener('click', () => {
    resonova.skip();
  });

  const recoverBtn = document.getElementById('recover-spotify-btn');
  if (recoverBtn) {
    recoverBtn.addEventListener('click', () => {
      resonova.recoverSpotify();
    });
  }

  const skipMusicBtn = document.getElementById('skip-music-btn');
  if (skipMusicBtn) {
    skipMusicBtn._wired = true;
    skipMusicBtn.addEventListener('click', () => {
      resonova.skip();
    });
  }

  // Load more playlists
  document.getElementById('load-more-playlists').addEventListener('click', () => {
    resonova._loadPlaylists();
  });
});
