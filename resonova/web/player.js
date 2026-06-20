/**
 * Resonova player — interleaves Spotify Web Playback SDK with HTML audio commentary.
 *
 * Queue format: [{type: "audio"|"spotify", url?: string, uri?: string}]
 * Playback proceeds sequentially through the queue; each item triggers the next
 * via an end-of-playback event (audio.onended for HTML audio, state change for Spotify).
 */

const STEP_MAP = {
  fetch:    'step-fetch',
  context:  'step-fetch',
  research: 'step-research',
  script:   'step-script',
  tts:      'step-tts',
};

class ResonovaPlayer {
  constructor() {
    this.queue               = [];
    this.playedItems         = [];
    this.playbackTimeline    = [];
    this.currentIndex        = -1;
    this.totalItems          = 0;
    this.completedItems      = 0;
    this.deviceId            = null;
    this._cachedToken        = null;
    this.spotifyPlayer       = null;
    this._segmentDeadline    = null;
    this.audioEl             = document.getElementById('resonova-audio');
    this.currentItem         = null;
    this._episodeId           = null;
    this._segmentType         = '';
    // Prevents double-firing of playNext on track end
    this._trackEndFired      = false;
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

    // Foreground reconciliation: check Spotify state when page becomes visible
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState !== 'visible') return;
      if (!this.currentItem) return;
      this._reconcileAfterBackground();
    });
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
      this._lifecycle.authError = message || 'authentication_error';
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
  }

  _clearSpotifyUnhealthy() {
    this._spotifyUnhealthy = false;
    this._spotifyRecoveryFailed = false;
    this._lifecycle.authError = null;
    this._lifecycle.playbackError = null;
    this._lifecycle.notReady = false;
    this._renderDiagnostics(null);
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
        const { token } = await this._apiFetch('/auth/token');
        if (!token) throw new Error('No Spotify token');
        this._cachedToken = token;

        // First try to reconnect existing player.
        if (this.spotifyPlayer) {
          try { await this.spotifyPlayer.connect(); } catch (_) {}
        }

        let deviceId = await this._waitForSpotifyDevice(3000);

        // If reconnect did not produce a device, rebuild once.
        if (!deviceId) {
          try { this.spotifyPlayer?.disconnect(); } catch (_) {}
          this.spotifyPlayer = null;
          this.deviceId = null;
          this._lifecycle.ready = false;
          this._lifecycle.deviceId = null;
          await this._initSpotifyPlayer();
          deviceId = await this._waitForSpotifyDevice(5000);
        }

        if (!deviceId) throw new Error('Spotify device did not become ready');

        await this._transferPlayback(deviceId, token);

        this._spotifyUnhealthy = false;
        this._spotifyRecoveryFailed = false;
        this._lifecycle.authError = null;
        this._lifecycle.playbackError = null;
        this._lifecycle.notReady = false;
        this._lifecycle.ready = true;
        this._lifecycle.deviceId = deviceId;
        this._renderDiagnostics(null);
        return true;
      } catch (err) {
        console.warn('[Resonova] Spotify recovery failed:', err);
        this._spotifyRecoveryFailed = true;
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

    const isVisible = this._spotifyUnhealthy || this._spotifyRecoveryFailed;
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
  }

  async recoverSpotify() {
    const success = await this._recoverSpotifySession();
    if (success && this.currentItem && this.currentItem.type === 'spotify') {
      await this._playSpotifyTrack(this.currentItem);
    }
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
    if (!this._episodeId || (!this.queue.length && !this.currentItem)) {
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

    // Insert after the header text, before the generate form
    const header = container.querySelector('.connected-header');
    if (header) {
      header.after(card);
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
    const startIndex = Math.max(0, state.currentIndex ?? (state.playedItems?.length || 0));
    const queue = timeline.slice(startIndex);

    this._startPlayback(queue, { timeline });
    this.playedItems = Array.isArray(state.playedItems) ? [...state.playedItems] : [];

    // Mark completedItems as already passed (minus current item)
    this.completedItems = Math.max(0, state.completedItems - 1);
    this.totalItems = state.totalItems || queue.length;
    this._segmentType = state.segmentType || '';
    this._updateProgress();
    this._updateSkipButton();
    this._saveResumeState();
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
    const { authenticated } = await this._apiFetch('/auth/token');
    if (!authenticated) {
      this._showState('landing');
      return;
    }
    this._showState('connected');
    this._loadSpotifySDK();
    this._loadLibrary();
    this._initLastFM();

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
      this._clearSpotifyUnhealthy();
      this._transferPlayback(device_id, token);
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
    connectPromise.catch(() => {});
  }

  async _transferPlayback(deviceId, token) {
    try {
      await fetch('https://api.spotify.com/v1/me/player', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ device_ids: [deviceId], play: false }),
      });
    } catch (err) {
      console.warn('Transfer playback failed:', err);
    }
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
    } catch (err) {
      this._showState('connected');
      this._showError('Failed to start generation: ' + err.message);
      return;
    }

    this._streamProgress(jobId);
  }

  _streamProgress(jobId) {
    const es = new EventSource(`/jobs/${jobId}/stream`);

    this._generationComplete = false;

    es.addEventListener('progress', (e) => {
      const { step, message } = JSON.parse(e.data);
      this._updateProgressStep(step, message);
    });

    // Intro is ready — start playback immediately with just the intro audio
    es.addEventListener('intro_ready', (e) => {
      const { url } = JSON.parse(e.data);
      this._markAllStepsDone();
      this._startPlayback([{ type: 'audio', url }]);
    });

    // Each track's commentary arrives as it finishes — append to live queue
    es.addEventListener('track_ready', (e) => {
      const { commentary_url, track_uri, total } = JSON.parse(e.data);
      const commentaryItem = { type: 'audio', url: commentary_url };
      const spotifyItem = { type: 'spotify', uri: track_uri };
      this.queue.push(commentaryItem);
      this.queue.push(spotifyItem);
      this.playbackTimeline.push(commentaryItem);
      this.playbackTimeline.push(spotifyItem);
      // intro (1) + N tracks × 2 items each
      this.totalItems = 1 + total * 2;
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
    });

    // Outro arrives after the last track — append to the live queue
    es.addEventListener('outro_ready', (e) => {
      const { url } = JSON.parse(e.data);
      const outroItem = { type: 'audio', url };
      this.queue.push(outroItem);
      this.playbackTimeline.push(outroItem);
      this.totalItems += 1;
      this._updateProgress();
      this._updateSkipButton();
      this._saveResumeState();
    });

    es.addEventListener('done', (_e) => {
      es.close();
      this._generationComplete = true;
      this._updateProgress();
      this._updateSkipButton();
      // Refresh episode list so the new episode appears immediately
      this._loadEpisodes();
    });

    es.addEventListener('error', (e) => {
      es.close();
      this._generationComplete = true;
      let msg = 'Generation failed.';
      try { msg = JSON.parse(e.data).message; } catch (_) {}
      this._showState('connected');
      this._showError(msg);
    });
  }

  // ──────────────────────────────────────────────
  // Playback queue
  // ──────────────────────────────────────────────

  _startPlayback(queue, options = {}) {
    this.queue          = [...queue];
    this.playedItems    = [];
    this.playbackTimeline = options.timeline ? [...options.timeline] : [...queue];
    this.currentIndex   = -1;
    this.totalItems     = queue.length;
    this.completedItems = 0;
    this._showState('playing');
    document.getElementById('on-air-badge').classList.add('active');
    this._renderDiagnostics(null);
    this._updateSkipButton();
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
      this._onPlaybackComplete();
      return;
    }

    const item = this.queue.shift();
    this.currentItem    = item;
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

    if (item.type === 'audio') {
      this._playAudio(item);
    } else if (item.type === 'spotify') {
      this._playSpotifyTrack(item);
    }
  }

  _playAudio(item) {
    this._setSegmentType('commentary');
    this._setNowPlaying('AI Commentary', 'Podcast Intro');

    // Look ahead to find what Spotify track comes next (for context)
    const nextSpotify = this.queue.find(q => q.type === 'spotify');
    if (nextSpotify?.name) {
      document.getElementById('next-up').innerHTML =
        `Up next: <strong>${nextSpotify.name}</strong>`;
    } else {
      document.getElementById('next-up').textContent = '';
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

    this.audioEl.play().catch(err => {
      console.error('Audio play failed:', err);
      this._playNext();
    });
  }

  async _playSpotifyTrack(item) {
    this._setSegmentType('spotify');

    document.getElementById('waveform').classList.add('spotify-mode');
    document.getElementById('waveform').classList.remove('paused');
    document.getElementById('progress-fill').classList.add('spotify-mode');

    if (!this._isSpotifyHealthy()) {
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
      document.getElementById('next-up').textContent = '';
    } else {
      try {
        const trackId = item.uri.split(':')[2];
        const trackRes = await fetch(`https://api.spotify.com/v1/tracks/${trackId}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (trackRes.ok) {
          const trackData = await trackRes.json();
          const artist = trackData.artists.map(a => a.name).join(', ');
          this._setNowPlaying(trackData.name, artist);
          item.name = trackData.name;
          item.artist = artist;
          this._cacheSet(item.uri, { name: trackData.name, artist });
          document.getElementById('next-up').textContent = '';
        }
      } catch (_) {}
    }

    try {
      // Restore full volume whenever we start a Spotify track
      await this.spotifyPlayer.setVolume(_SPOTIFY_VOLUME);
      const res = await fetch(`https://api.spotify.com/v1/me/player/play?device_id=${this.deviceId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ uris: [item.uri] }),
      });
      if (!res.ok) {
        throw new Error(`Device playback endpoint returned ${res.status}`);
      }
    } catch (err) {
      console.error('Spotify play failed:', err);
      this._markSpotifyUnhealthy('playback_error', err.message || 'Direct play command failed');
      this._spotifyRecoveryFailed = true;
      this._updateRecoveryControl();
      this._setNowPlaying('(Spotify playback failed. Click Recover below.)', '');
      document.getElementById('waveform').classList.remove('spotify-mode');
      document.getElementById('progress-fill').classList.remove('spotify-mode');
    }
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
    if (state.duration > 0 && !this._segmentDeadline) {
      const remainingMs = Math.max(0, state.duration - (state.position || 0));
      const deadlineMs = Math.max(3000, remainingMs + 3000);
      const sentinel = this.currentItem;
      this._segmentDeadline = setTimeout(() => {
        if (this.currentItem === sentinel && !this._trackEndFired) {
          console.log('[Resonova] Segment deadline fired; forcing advance');
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

    const d = {
      paused:    state ? (state.paused ? 'yes' : 'no') : 'waiting',
      position:  state ? fmtMs(state.position) : '--:--',
      duration:  state ? fmtMs(state.duration) : '--:--',
      track:     (state?.track_window?.current_track?.name || 'waiting for Spotify state').slice(0, 32),
      deviceId:  this.deviceId ? 'yes' : 'NO',
      prevCount: state?.track_window?.previous_tracks?.length ?? '-',
      segType:   this.currentItem?.type || '-',
      queueRemaining: this.queue.length,
    };
    const lc = this._lifecycle;

    // Build rows with warn class for critical fields
    const row = (label, value, warn) =>
      `<div class="spotify-diag-row"><span class="spotify-diag-label">${label}</span><span class="spotify-diag-value${warn ? ' warn' : ''}">${value}</span></div>`;

    this._diagEl.innerHTML =
      row('Paused',   d.paused) +
      row('Position', d.position) +
      row('Duration', d.duration) +
      row('Track',    d.track) +
      row('Device ID',d.deviceId, d.deviceId === 'NO') +
      row('Prev',     d.prevCount) +
      row('Seg type', d.segType) +
      row('Queue',    d.queueRemaining) +
      '<div class="spotify-diag-sep"></div>' +
      row('SDK loaded',   lc.sdkLoaded ? 'yes' : 'no') +
      row('Player built', lc.playerConstructed ? 'yes' : 'no') +
      row('connect()',    lc.connectCalled ? (lc.connectResult || '...') : 'not called', !lc.connectCalled || (lc.connectCalled && !lc.connectResult)) +
      row('ready',        lc.ready ? 'yes' : 'no', !lc.ready) +
      row('device_id',    lc.deviceId || '-', !lc.deviceId) +
      row('not_ready',    lc.notReady ? 'yes' : 'no') +
      row('init_error',   lc.initError || '-', !!lc.initError) +
      row('auth_error',   lc.authError || '-', !!lc.authError) +
      row('acct_error',   lc.accountError ? 'yes' : 'no') +
      row('playback_err', lc.playbackError || '-', !!lc.playbackError) +
      row('autoplay_fail',lc.autoplayFailed ? 'yes' : 'no') +
      row('SecureCtx',    lc.isSecureContext ? 'true' : 'false', !lc.isSecureContext) +
      row('Protocol',     lc.protocol) +
      row('UA',           (lc.userAgent || '').slice(0, 48) + (lc.userAgent && lc.userAgent.length > 48 ? '...' : '')) +
      '<button class="spotify-diag-refresh" id="spotify-diag-refresh">Refresh State</button>';

    // Bind refresh button (re-bind every render since innerHTML replaces it)
    const btn = this._diagEl.querySelector('#spotify-diag-refresh');
    if (btn) {
      btn.addEventListener('click', () => this._refreshDiagnostics());
    }
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

  async _loadEpisodes() {
    try {
      const { episodes } = await this._apiFetch('/api/episodes');
      if (!episodes.length) return;
      const container = document.getElementById('past-episodes');
      container.innerHTML = episodes.map(ep => this._episodeCardHTML(ep)).join('');
      document.getElementById('section-episodes').classList.add('loaded');
    } catch (e) { console.warn('Failed to load past episodes:', e); }
  }

  _episodeCardHTML(ep) {
    const date = new Date(ep.created_at).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
    });
    return `
      <div class="episode-card" data-episode-id="${ep.id}">
        <div class="episode-card-name">${this._esc(ep.name)}</div>
        <div class="episode-card-meta">
          ${this._esc(ep.playlist_name)} · ${ep.track_count} tracks · ${date}
        </div>
      </div>
    `;
  }

  async _playEpisode(episodeId) {
    this._episodeId = episodeId;
    try {
      const ep = await this._apiFetch(`/api/episodes/${episodeId}`);
      this._startPlayback(ep.queue);
    } catch (err) {
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
    input.focus();
    // Auto-submit
    document.getElementById('generate-form').requestSubmit();
  }

  // ──────────────────────────────────────────────
  // UI helpers
  // ──────────────────────────────────────────────

  _showState(name) {
    document.querySelectorAll('.state').forEach(el => el.classList.remove('active'));
    const el = document.getElementById(`state-${name}`);
    if (el) {
      el.classList.add('active');
      if (name === 'playing' && !document.getElementById('diag-toggle')) {
        document.getElementById('on-air-badge')?.appendChild(this._createDiagToggle());
      }
    }
  }

  _showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.classList.add('visible');
    setTimeout(() => el.classList.remove('visible'), 6000);
  }

  _setNowPlaying(title, artist) {
    document.getElementById('now-playing-title').textContent  = title;
    document.getElementById('now-playing-artist').textContent = artist;

    const titleEl = document.getElementById('now-playing-title');
    if (title === 'AI Commentary') {
      titleEl.classList.add('italic');
    } else {
      titleEl.classList.remove('italic');
    }
  }

  _setSegmentType(type) {
    const el = document.getElementById('segment-type');
    el.className = 'segment-type ' + (type || '');
    const labels = { commentary: 'AI Commentary', spotify: 'Now Playing', '': '' };
    el.querySelector('.segment-type-label').textContent = labels[type] ?? '';
    this._segmentType = type;
  }

  _updateProgress() {
    const pct = this.totalItems > 0
      ? Math.round((this.completedItems / this.totalItems) * 100)
      : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
    const suffix = this._generationComplete ? '' : ' · generating…';
    document.getElementById('progress-label').textContent =
      `${this.completedItems} / ${this.totalItems} segments${suffix}`;
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
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
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
    const episodeCard = e.target.closest('.episode-card');
    if (episodeCard) {
      resonova._playEpisode(episodeCard.dataset.episodeId);
      return;
    }
    const card = e.target.closest('.playlist-card');
    if (card) {
      resonova._handlePlaylistClick(card.dataset.uri);
    }
  });

  // Skip button
  document.getElementById('prev-btn').addEventListener('click', () => {
    resonova.previous();
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

  // Load more playlists
  document.getElementById('load-more-playlists').addEventListener('click', () => {
    resonova._loadPlaylists();
  });
});
