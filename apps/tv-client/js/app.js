/**
 * Rewind TV Client Application Controller
 * Orchestrates screens S1-S9, session state, spoiler gating, and live backend interactions.
 */

class RewindTvApp {
  constructor() {
    this.currentScreen = 's2-catalog';
    this.screenHistory = [];
    this.selectedMovie = null;
    this.currentSession = null;
    this.pendingSpoilerNonce = null;
    this.lastSubmittedQuestion = '';
    this.playerSubtitles = [];
    this.subtitlesEnabled = false;  // OFF by default — user watches normally, asks when curious
    this.hudIdleTimer = null;
    this.isRecordingVoice = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    
    // Sample fallback script for one-click admin test ingestion
    this.sampleSrt = `1
00:00:10,000 --> 00:00:20,000
COOPER: Earth is dying from the blight. We need to find an exoplanet to save humanity.

2
00:00:30,000 --> 00:00:45,000
BRAND: Professor Brand has been working on the gravity equation for thirty years.

3
00:01:10,000 --> 00:01:25,000
ROMILLY: Miller's planet is next to Gargantua. Every hour on that planet is seven years on Earth.

4
00:02:00,000 --> 00:02:15,000
MANN: The data was faked! There is no surface, only frozen clouds. I cannot die here alone.

5
00:03:00,000 --> 00:03:15,000
COOPER: Murf, it was me! I was your ghost! Love transcended five-dimensional space.
`;

    document.addEventListener('DOMContentLoaded', () => this.init());
  }

  async init() {
    this.bindNavPills();
    this.bindCatalogEvents();
    this.bindDetailsEvents();
    this.bindPlayerEvents();
    this.bindCompanionEvents();
    this.bindAnswerEvents();
    this.bindClarificationEvents();
    this.bindSpoilerModalEvents();
    this.bindSettingsEvents();
    this.bindAdminEvents();
    this.bindProviderEvents();

    // Check backend health & fetch titles
    await this.checkBackendStatus();
    await this.loadCatalog();

    // Initial focus on the catalog or welcome screen
    this.showScreen('s2-catalog');
  }

  /* -------------------------------------------------------------
     Navigation & Screen State Management
     ------------------------------------------------------------- */

  bindNavPills() {
    const navButtons = document.querySelectorAll('.tv-nav-btn');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetScreen = btn.getAttribute('data-screen');
        if (targetScreen === 's-player') {
          this.launchMediaPlayer(this.selectedMovie, 0);
        } else if (targetScreen) {
          this.showScreen(targetScreen);
        }
      });
    });
  }

  showScreen(screenId) {
    if (this.currentScreen === screenId) return;

    // Pause video playback if navigating away from player screen
    if (this.currentScreen === 's-player' && screenId !== 's-player') {
      const video = document.getElementById('main-video-player');
      if (video && !video.paused) {
        video.pause();
      }
    }

    if (this.currentScreen) {
      this.screenHistory.push(this.currentScreen);
    }

    const currentScreenEl = document.getElementById(this.currentScreen);
    if (currentScreenEl) {
      currentScreenEl.classList.remove('active');
    }

    const nextScreenEl = document.getElementById(screenId);
    if (nextScreenEl) {
      nextScreenEl.classList.add('active');
      this.currentScreen = screenId;
    }

    // Update active nav pill
    document.querySelectorAll('.tv-nav-btn').forEach(btn => {
      if (btn.getAttribute('data-screen') === screenId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Move spatial focus to first item on new screen
    window.TvNavigator?.focusFirstOnScreen();
  }

  navigateBack() {
    // 0. If in-screen AI drawer is open, close drawer and resume video playback
    const drawer = document.getElementById('player-ai-drawer');
    if (drawer && drawer.classList.contains('open')) {
      this.closePlayerAiDrawer(true);
      return;
    }

    // Pause video if leaving player
    if (this.currentScreen === 's-player') {
      const video = document.getElementById('main-video-player');
      if (video && !video.paused) {
        video.pause();
      }
    }

    if (this.screenHistory.length > 0) {
      const prevScreen = this.screenHistory.pop();
      const currentEl = document.getElementById(this.currentScreen);
      if (currentEl) currentEl.classList.remove('active');

      const prevEl = document.getElementById(prevScreen);
      if (prevEl) {
        prevEl.classList.add('active');
        this.currentScreen = prevScreen;
      }

      // Update nav pill
      document.querySelectorAll('.tv-nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-screen') === prevScreen);
      });

      window.TvNavigator?.focusFirstOnScreen();
    } else {
      // Default to catalog if history is empty
      this.showScreen('s2-catalog');
    }
  }

  closeModal() {
    window.TvNavigator?.releaseModalFocus();
  }

  /* -------------------------------------------------------------
     Screen 2: Catalog Browsing
     ------------------------------------------------------------- */

  bindCatalogEvents() {
    // Welcome screen start button
    document.getElementById('btn-welcome-start')?.addEventListener('click', () => {
      this.showScreen('s2-catalog');
    });
  }

  async loadCatalog() {
    const gridContainer = document.getElementById('catalog-grid-container');
    const loader = document.getElementById('catalog-loader');

    try {
      const res = await window.RewindApi.getTitles(20, 0);
      const items = res?.items || [];

      if (loader) loader.style.display = 'none';

      if (items.length === 0) {
        gridContainer.innerHTML = `
          <div class="catalog-empty-card outer-bezel" style="grid-column: 1 / -1; max-width: 600px; margin: 40px auto;">
            <div class="inner-core" style="padding: 36px; text-align: center;">
              <h3>No Published Titles Found</h3>
              <p style="color: var(--text-secondary); margin: 12px 0 24px 0;">
                The backend catalog has not indexed any subtitle assets yet.
              </p>
              <button class="tv-btn tv-btn-primary tv-focusable" id="btn-seed-catalog" tabindex="0">
                <span>Ingest Sample Movie (Interstellar)</span>
                <span class="btn-icon-circle">⚡</span>
              </button>
            </div>
          </div>
        `;
        document.getElementById('btn-seed-catalog')?.addEventListener('click', () => this.seedSampleMovie());
        return;
      }

      gridContainer.innerHTML = '';
      items.forEach(movie => {
        const card = document.createElement('div');
        card.className = 'movie-card outer-bezel tv-focusable';
        card.setAttribute('tabindex', '0');
        card.setAttribute('data-movie-id', movie.id || movie.title_id);

        const durationMinutes = Math.floor(movie.duration_seconds / 60);
        const hours = Math.floor(durationMinutes / 60);
        const mins = durationMinutes % 60;
        const durFormatted = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;

        card.innerHTML = `
          <div class="inner-core movie-card-inner">
            <div>
              <div class="movie-badge-row">
                <span class="badge-status-ready">● Questions Ready</span>
                <span class="movie-year">${movie.year || '2014'}</span>
              </div>
              <h3 class="movie-card-title">${this.escapeHtml(movie.display_title)}</h3>
              <p class="movie-card-desc">Dialogue and scene timestamps indexed for spoiler-safe exploration.</p>
            </div>
            <div class="movie-card-footer">
              <span class="movie-duration">${durFormatted}</span>
              <span class="movie-cta-tag">Select Movie ➔</span>
            </div>
          </div>
        `;

        card.addEventListener('click', () => this.selectMovie(movie));
        gridContainer.appendChild(card);
      });

    } catch (err) {
      if (loader) loader.style.display = 'none';
      gridContainer.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: #f87171;">
          <p>Failed to load title catalog: ${this.escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  async selectMovie(movie) {
    this.selectedMovie = movie;
    
    // Update Details Screen (S3) DOM
    document.getElementById('det-movie-title').textContent = movie.display_title;
    document.getElementById('det-movie-year').textContent = `${movie.year || '2014'} • ${Math.floor(movie.duration_seconds / 60)}m`;
    document.getElementById('det-duration-display').textContent = `/ ${this.formatTime(movie.duration_seconds)}`;
    
    const slider = document.getElementById('det-progress-slider');
    slider.max = movie.duration_seconds || 10000;
    slider.value = 50; // Default to 50s for testing
    this.updateSliderTimeDisplay(50);

    // Update Header
    document.getElementById('hdr-movie-title').textContent = movie.display_title;
    document.getElementById('hdr-progress-time').textContent = this.formatTime(50);

    this.showScreen('s3-details');
  }

  /* -------------------------------------------------------------
     Screen 3: Title Details & Playback Setup
     ------------------------------------------------------------- */

  bindDetailsEvents() {
    const slider = document.getElementById('det-progress-slider');
    slider?.addEventListener('input', (e) => {
      this.updateSliderTimeDisplay(parseInt(e.target.value, 10));
    });

    // Quick jump pills (+5m, +15m, +30m, +1h)
    document.querySelectorAll('.jump-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const jump = parseInt(btn.getAttribute('data-jump'), 10) || 0;
        const currentVal = parseInt(slider.value, 10) || 0;
        const maxVal = parseInt(slider.max, 10) || 10000;
        const newVal = Math.min(maxVal, currentVal + jump);
        slider.value = newVal;
        this.updateSliderTimeDisplay(newVal);
      });
    });

    // Back to catalog
    document.getElementById('btn-back-to-catalog')?.addEventListener('click', () => {
      this.showScreen('s2-catalog');
    });

    // Start Session Action (Stand-alone Companion)
    document.getElementById('btn-start-session')?.addEventListener('click', () => {
      this.startViewingSession();
    });

    // Play Movie Action (Watch Movie with In-Screen AI)
    document.getElementById('btn-play-movie')?.addEventListener('click', () => {
      const slider = document.getElementById('det-progress-slider');
      const position = parseInt(slider?.value, 10) || 50;
      this.launchMediaPlayer(this.selectedMovie, position);
    });
  }

  updateSliderTimeDisplay(seconds) {
    const timeDisplay = document.getElementById('det-time-display');
    const hdrTime = document.getElementById('hdr-progress-time');
    const formatted = this.formatTime(seconds);
    if (timeDisplay) timeDisplay.textContent = formatted;
    if (hdrTime) hdrTime.textContent = formatted;
  }

  async startViewingSession() {
    if (!this.selectedMovie) return;

    const slider = document.getElementById('det-progress-slider');
    const position = parseInt(slider.value, 10) || 50;

    try {
      const session = await window.RewindApi.createSession(
        this.selectedMovie.id || this.selectedMovie.title_id,
        position,
        'safe'
      );
      this.currentSession = session;
      this.showToast(`Session active at ${this.formatTime(position)} (Safe Mode)`);
      this.updateCompanionContext();
      this.showScreen('s4-companion');
    } catch (err) {
      this.showToast(`Error starting session: ${err.message}`);
    }
  }

  /* -------------------------------------------------------------
     Screen: In-Screen Media Player & Zero-Switch AI Assistant Drawer
     ------------------------------------------------------------- */

  async launchMediaPlayer(movie = null, startSeconds = 0) {
    if (!movie && !this.selectedMovie) {
      try {
        const res = await window.RewindApi.getTitles(20, 0);
        const found = res?.items?.find(m => m.id === 'interstellar-epic') || res?.items?.[0];
        if (found) this.selectedMovie = found;
      } catch (e) {
        console.warn('Could not auto-fetch title for player:', e);
      }
    } else if (movie) {
      this.selectedMovie = movie;
    }

    const movieTitle = this.selectedMovie?.display_title || 'Interstellar (2014)';
    // Preferred stream URL: Server MinIO Object Storage (with YouTube-style Range Request Chunking)
    // Secondary: ImageKit HLS adaptive stream if configured
    const defaultStream = this.selectedMovie?.stream_url || 'https://rewind.sharexpress.in/minio/interstellar.mp4';
    const streamUrl = defaultStream;
    const totalDuration = this.selectedMovie?.duration_seconds || 10145;

    // Update Player HUD DOM
    const hudTitle = document.getElementById('player-hud-title');
    if (hudTitle) hudTitle.textContent = movieTitle;

    const totalDisplay = document.getElementById('player-total-duration');
    if (totalDisplay) totalDisplay.textContent = `/ ${this.formatTime(totalDuration)}`;

    const slider = document.getElementById('player-timeline-slider');
    if (slider) {
      slider.max = totalDuration;
      slider.value = startSeconds;
    }

    const video = document.getElementById('main-video-player');
    if (video) {
      this.initVideoStreaming(video, streamUrl, startSeconds);
    }

    // Ensure backend session exists for this title
    if (!this.currentSession && this.selectedMovie) {
      try {
        this.currentSession = await window.RewindApi.createSession(
          this.selectedMovie.id || this.selectedMovie.title_id || 'interstellar-epic',
          startSeconds,
          'safe'
        );
      } catch (err) {
        console.warn('Session create for player:', err);
      }
    }

    // Load subtitle track for real-time cue display
    this.loadSubtitles();

    this.showScreen('s-player');
    this.resetHudIdleTimer();

    // Start playback
    if (video) {
      video.play().then(() => {
        this.updatePlayPauseUI(true);
      }).catch(() => {
        this.updatePlayPauseUI(false);
      });
    }
  }

  /**
   * Initializes YouTube-style chunked streaming architecture:
   * 1. Adaptive Bitrate Streaming (HLS) via MediaSource Extensions (MSE) with Hls.js
   * 2. HTTP 206 Byte-Range Chunk fallback for direct CDN video delivery
   */
  initVideoStreaming(video, streamUrl, startSeconds = 0) {
    if (!video) return;

    const chunkModeBadge = document.getElementById('player-chunk-mode');
    const isHlsUrl = streamUrl.includes('.m3u8') || streamUrl.includes('ik-master');

    // YouTube Architecture Pattern: MSE HLS Chunked Delivery
    if (isHlsUrl && window.Hls && window.Hls.isSupported()) {
      if (this.hlsInstance) {
        this.hlsInstance.destroy();
      }
      this.hlsInstance = new window.Hls({
        maxBufferLength: 30, // Buffers 30s ahead (matching YouTube chunk buffer window)
        maxMaxBufferLength: 60,
        maxBufferSize: 60 * 1024 * 1024,
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 30,
      });

      this.hlsInstance.loadSource(streamUrl);
      this.hlsInstance.attachMedia(video);

      this.hlsInstance.on(window.Hls.Events.MANIFEST_PARSED, (evt, data) => {
        if (chunkModeBadge) chunkModeBadge.textContent = 'HLS Chunks (MSE)';
        const levels = data.levels || [];
        const resBadge = document.getElementById('player-resolution-badge');
        if (resBadge && levels.length > 0) {
          const topLevel = levels[levels.length - 1];
          resBadge.textContent = `${topLevel.height || 1080}p HD`;
        }
        if (startSeconds > 0) video.currentTime = startSeconds;
      });

      this.hlsInstance.on(window.Hls.Events.FRAG_LOADED, () => {
        this.updateBufferBar(video);
      });

      this.hlsInstance.on(window.Hls.Events.ERROR, (evt, data) => {
        if (data.fatal) {
          console.warn('HLS stream failed, falling back to direct Range-Request CDN chunks:', data);
          this.hlsInstance.destroy();
          this.hlsInstance = null;
          // Fallback to direct byte-range chunks
          this.initDirectRangeStreaming(video, '/media/interstellar.mp4', startSeconds);
        }
      });
    } else if (isHlsUrl && video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native Apple HLS (Safari / macOS)
      video.src = streamUrl;
      if (chunkModeBadge) chunkModeBadge.textContent = 'HLS Chunks (Native)';
      if (startSeconds > 0) video.currentTime = startSeconds;
      video.load();
    } else {
      // HTTP 206 Partial Content Byte-Range Chunk Delivery
      this.initDirectRangeStreaming(video, streamUrl, startSeconds);
    }
  }

  initDirectRangeStreaming(video, streamUrl, startSeconds = 0) {
    const chunkModeBadge = document.getElementById('player-chunk-mode');
    if (chunkModeBadge) {
      if (streamUrl.includes('ik.imagekit.io')) {
        chunkModeBadge.textContent = 'ImageKit Chunks (206)';
      } else if (streamUrl.includes('minio')) {
        chunkModeBadge.textContent = 'Server MinIO Chunks (206)';
      } else if (streamUrl.includes('sharexpress')) {
        chunkModeBadge.textContent = 'Cloudflare CDN Chunks';
      } else {
        chunkModeBadge.textContent = 'Local Chunks (206)';
      }
    }
    const currentSrc = video.currentSrc || video.src;
    if (!currentSrc || !currentSrc.includes(streamUrl)) {
      video.src = streamUrl;
      video.load();
    }
    if (startSeconds > 0) {
      video.currentTime = startSeconds;
    }

    // Robust fallback to local static media if CDN is unreachable
    video.onerror = () => {
      const localFallback = '/media/interstellar.mp4';
      if (!video.src.endsWith(localFallback)) {
        console.warn('Primary stream failed, seamlessly falling back to:', localFallback);
        video.src = localFallback;
        video.load();
        if (chunkModeBadge) chunkModeBadge.textContent = 'Local Chunks (206)';
      }
    };
  }

  updateBufferBar(video) {
    if (!video) return;
    const dur = video.duration || this.selectedMovie?.duration_seconds || 10145;
    if (!dur) return;

    let currentBufferedEnd = 0;
    const curTime = video.currentTime || 0;

    for (let i = 0; i < video.buffered.length; i++) {
      const start = video.buffered.start(i);
      const end = video.buffered.end(i);
      if (start <= curTime + 0.5 && end >= curTime - 0.5) {
        currentBufferedEnd = end;
        break;
      }
      if (end > currentBufferedEnd) {
        currentBufferedEnd = end;
      }
    }

    const bufferPct = Math.min(100, Math.max(0, (currentBufferedEnd / dur) * 100));
    const bufferBar = document.getElementById('player-buffer-bar');
    if (bufferBar) bufferBar.style.width = `${bufferPct}%`;

    const bufferStats = document.getElementById('buffer-text');
    if (bufferStats) {
      const aheadSeconds = Math.max(0, currentBufferedEnd - curTime);
      bufferStats.textContent = `Buffer: ${aheadSeconds.toFixed(1)}s`;
    }
  }

  bindPlayerEvents() {
    const video = document.getElementById('main-video-player');
    const timeline = document.getElementById('player-timeline-slider');
    const playPauseBtn = document.getElementById('player-btn-playpause');
    const rewindBtn = document.getElementById('player-btn-rewind30');
    const fwd30Btn = document.getElementById('player-btn-fwd30');
    const fwd5mBtn = document.getElementById('player-btn-fwd5m');
    const hudBack = document.getElementById('player-hud-back');
    const subtitlesToggle = document.getElementById('player-hud-subtitles-toggle');
    const askHeroBtn = document.getElementById('player-btn-ask-ai-hero');
    const askAiBtn = document.getElementById('player-btn-ask-ai');
    const drawerResumeBtn = document.getElementById('drawer-btn-resume');
    const drawerResumeAfterAns = document.getElementById('drawer-btn-resume-after-ans');
    const drawerSubmitBtn = document.getElementById('drawer-btn-submit');
    const drawerCustomInput = document.getElementById('drawer-custom-input');
    const drawerVoiceBtn = document.getElementById('drawer-voice-ptt');
    const drawerAskMoreBtn = document.getElementById('drawer-btn-ask-more');

    // Play / Pause Toggle
    playPauseBtn?.addEventListener('click', () => {
      if (!video) return;
      if (video.paused) {
        video.play();
      } else {
        video.pause();
      }
    });

    video?.addEventListener('play', () => this.updatePlayPauseUI(true));
    video?.addEventListener('pause', () => this.updatePlayPauseUI(false));

    // Timeline Progress, Buffer & Subtitle Sync
    video?.addEventListener('timeupdate', () => {
      const curTime = Math.floor(video.currentTime || 0);
      const dur = video.duration || this.selectedMovie?.duration_seconds || 10145;

      if (timeline && !timeline.matches(':active')) {
        timeline.value = curTime;
      }

      // Update YouTube-style Progress bar
      const progBar = document.getElementById('player-progress-bar');
      if (progBar && dur > 0) {
        progBar.style.width = `${Math.min(100, (curTime / dur) * 100)}%`;
      }

      const curFormatted = this.formatTime(curTime);
      const curDisplay = document.getElementById('player-current-time');
      const hdrProgress = document.getElementById('hdr-progress-time');
      if (curDisplay) curDisplay.textContent = curFormatted;
      if (hdrProgress) hdrProgress.textContent = curFormatted;

      if (this.subtitlesEnabled) {
        this.renderActiveSubtitle(video.currentTime);
      }
    });

    // YouTube-style Buffer updates on progress event
    video?.addEventListener('progress', () => {
      this.updateBufferBar(video);
    });

    // Seeking via timeline slider
    timeline?.addEventListener('input', (e) => {
      if (video) {
        const val = parseFloat(e.target.value);
        video.currentTime = val;
        const dur = video.duration || this.selectedMovie?.duration_seconds || 10145;
        const progBar = document.getElementById('player-progress-bar');
        if (progBar && dur > 0) {
          progBar.style.width = `${Math.min(100, (val / dur) * 100)}%`;
        }
        this.resetHudIdleTimer();
      }
    });

    // Quick Jumps
    rewindBtn?.addEventListener('click', () => {
      if (video) {
        video.currentTime = Math.max(0, video.currentTime - 30);
        this.resetHudIdleTimer();
      }
    });

    fwd30Btn?.addEventListener('click', () => {
      if (video) {
        video.currentTime = Math.min(video.duration || 10145, video.currentTime + 30);
        this.resetHudIdleTimer();
      }
    });

    fwd5mBtn?.addEventListener('click', () => {
      if (video) {
        video.currentTime = Math.min(video.duration || 10145, video.currentTime + 300);
        this.resetHudIdleTimer();
      }
    });

    // Exit Player
    hudBack?.addEventListener('click', () => {
      video?.pause();
      this.showScreen('s2-catalog');
    });

    // Subtitle Toggle
    subtitlesToggle?.addEventListener('click', () => {
      this.subtitlesEnabled = !this.subtitlesEnabled;
      subtitlesToggle.classList.toggle('active', this.subtitlesEnabled);
      const overlay = document.getElementById('player-subtitle-overlay');
      if (!this.subtitlesEnabled && overlay) overlay.classList.add('hidden');
      this.showToast(this.subtitlesEnabled ? 'Subtitles: ON' : 'Subtitles: OFF');
      this.resetHudIdleTimer();
    });

    // Zero-Screen-Switch AI Triggers
    askHeroBtn?.addEventListener('click', () => this.openPlayerAiDrawer());
    askAiBtn?.addEventListener('click', () => this.openPlayerAiDrawer());

    // Drawer Actions
    drawerResumeBtn?.addEventListener('click', () => this.closePlayerAiDrawer(true));
    drawerResumeAfterAns?.addEventListener('click', () => this.closePlayerAiDrawer(true));

    // Custom Question Submission
    drawerSubmitBtn?.addEventListener('click', () => {
      const q = drawerCustomInput?.value?.trim();
      if (q) this.submitDrawerQuestion(q);
    });

    drawerCustomInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = drawerCustomInput?.value?.trim();
        if (q) this.submitDrawerQuestion(q);
      }
    });

    drawerVoiceBtn?.addEventListener('click', () => this.handleDrawerVoicePtt());

    drawerAskMoreBtn?.addEventListener('click', () => {
      if (drawerCustomInput) {
        drawerCustomInput.value = '';
        drawerCustomInput.focus();
      }
    });

    // HUD Auto-hide on mouse activity
    const playerWrapper = document.getElementById('player-wrapper');
    playerWrapper?.addEventListener('mousemove', () => this.resetHudIdleTimer());
    playerWrapper?.addEventListener('click', (e) => {
      if (e.target === video || e.target === playerWrapper) {
        this.resetHudIdleTimer();
      }
    });
  }

  updatePlayPauseUI(isPlaying) {
    const icon = document.getElementById('player-playpause-icon');
    const text = document.getElementById('player-playpause-text');
    if (icon) icon.textContent = isPlaying ? '⏸' : '▶';
    if (text) text.textContent = isPlaying ? 'Pause' : 'Play';
  }

  handlePlayerSpaceAction() {
    const drawer = document.getElementById('player-ai-drawer');
    const video = document.getElementById('main-video-player');
    if (!video) return;

    if (drawer && drawer.classList.contains('open')) {
      // Space while drawer is open → close drawer and resume
      this.closePlayerAiDrawer(true);
    } else if (video.paused) {
      // Space while paused and drawer closed → open drawer (they paused to ask)
      this.openPlayerAiDrawer();
    } else {
      // Space while playing → pause and open drawer
      this.openPlayerAiDrawer();
    }
  }

  async openPlayerAiDrawer() {
    const video = document.getElementById('main-video-player');
    if (video && !video.paused) {
      video.pause();
    }

    const currentSec = Math.floor(video?.currentTime || 0);
    const formatted = this.formatTime(currentSec);

    // Update paused timestamp badge
    const badge = document.getElementById('drawer-paused-timestamp');
    if (badge) badge.textContent = `Paused at ${formatted}`;

    // Update backend session progress in background
    if (this.currentSession) {
      const sessId = this.currentSession.id || this.currentSession.session_id;
      window.RewindApi.updateProgress(sessId, currentSec).catch(() => {});
    }

    // Open drawer overlay
    const drawer = document.getElementById('player-ai-drawer');
    if (drawer) {
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
    }

    // Scroll thread to bottom
    const thread = document.getElementById('drawer-chat-thread');
    if (thread) thread.scrollTop = thread.scrollHeight;

    // Focus the text input
    setTimeout(() => {
      const input = document.getElementById('drawer-custom-input');
      if (input) input.focus();
    }, 80);
  }

  closePlayerAiDrawer(resumeVideo = true) {
    const drawer = document.getElementById('player-ai-drawer');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }

    if (resumeVideo) {
      const video = document.getElementById('main-video-player');
      video?.play().catch(() => {});
    }

    // Return focus to the Ask AI button in the HUD
    setTimeout(() => {
      const askBtn = document.getElementById('player-btn-ask-ai');
      if (askBtn) window.TvNavigator?.setFocus(askBtn);
    }, 80);
  }

  async submitDrawerQuestion(questionText) {
    if (!questionText) return;

    const video = document.getElementById('main-video-player');
    const currentSec = Math.floor(video?.currentTime || 0);

    const thread = document.getElementById('drawer-chat-thread');
    const loader = document.getElementById('drawer-loading');
    const input = document.getElementById('drawer-custom-input');

    // Append user bubble
    if (thread) {
      const userMsg = document.createElement('div');
      userMsg.className = 'chat-msg user';
      userMsg.innerHTML = `
        <div class="chat-avatar">👤</div>
        <div class="chat-bubble">${this.escapeHtml(questionText)}</div>
      `;
      thread.appendChild(userMsg);
      thread.scrollTop = thread.scrollHeight;
    }

    // Clear input
    if (input) input.value = '';

    // Show thinking
    if (loader) loader.classList.remove('hidden');

    try {
      // Ensure session exists
      if (!this.currentSession) {
        this.currentSession = await window.RewindApi.createSession(
          this.selectedMovie?.id || 'interstellar-epic',
          currentSec,
          'safe'
        );
      }

      const sessId = this.currentSession.id || this.currentSession.session_id;

      // Update progress to exact paused frame
      await window.RewindApi.updateProgress(sessId, currentSec).catch(() => {});

      const result = await window.RewindApi.askQuestion(sessId, questionText);

      if (loader) loader.classList.add('hidden');

      // Build AI answer bubble
      const answerText = result.answer || result.text || 'Context retrieved.';
      const citations = result.citations || result.sources || [];

      if (thread) {
        const aiMsg = document.createElement('div');
        aiMsg.className = 'chat-msg ai';

        let citationsHtml = '';
        if (citations.length > 0) {
          const chips = citations.map(c => {
            const cueSec = Math.floor(c.start_time_seconds || c.start_seconds || 0);
            return `<button class="citation-chip" data-sec="${cueSec}" title="${this.escapeHtml(c.text || 'Jump to scene')}">
              ⏱ ${this.formatTime(cueSec)} ${c.speaker ? '· ' + this.escapeHtml(c.speaker) : ''}
            </button>`;
          }).join('');
          citationsHtml = `<div class="chat-citations">${chips}</div>`;
        }

        aiMsg.innerHTML = `
          <div class="chat-avatar">✦</div>
          <div class="chat-bubble">
            ${this.escapeHtml(answerText)}
            ${citationsHtml}
          </div>
        `;

        thread.appendChild(aiMsg);

        // Wire citation chips to seek
        aiMsg.querySelectorAll('.citation-chip').forEach(chip => {
          chip.addEventListener('click', () => {
            const sec = parseInt(chip.getAttribute('data-sec'), 10);
            if (video && !isNaN(sec)) video.currentTime = sec;
            this.closePlayerAiDrawer(true);
            this.showToast(`Jumped to ${this.formatTime(sec)}`);
          });
        });

        thread.scrollTop = thread.scrollHeight;
      }

      // TTS audio playback if available
      if (result.audio_base64) {
        const audioEl = document.getElementById('drawer-tts-audio');
        if (audioEl) {
          audioEl.src = `data:audio/mp3;base64,${result.audio_base64}`;
          audioEl.play().catch(() => {});
        }
      }

      // Focus input for follow-up
      setTimeout(() => {
        if (input) input.focus();
      }, 80);

    } catch (err) {
      if (loader) loader.classList.add('hidden');

      // Show error as AI bubble
      if (thread) {
        const errMsg = document.createElement('div');
        errMsg.className = 'chat-msg ai';
        let errText = `Unable to retrieve dialogue context: ${err.message}`;
        if (err.code === 'SPOILER_BLOCKED' || err.status === 409) {
          errText = "⚠️ Future spoiler blocked \u2014 this answer reveals events you haven\u2019t reached yet. Safe Mode is protecting you.";
        }
        errMsg.innerHTML = `
          <div class="chat-avatar">✦</div>
          <div class="chat-bubble" style="border-color: rgba(245,158,11,0.3); color: #fbbf24;">${errText}</div>
        `;
        thread.appendChild(errMsg);
        thread.scrollTop = thread.scrollHeight;
      }
    }
  }

  async handleDrawerVoicePtt() {
    const micIcon = document.getElementById('drawer-ptt-mic');
    const label = document.getElementById('drawer-ptt-label');

    if (this.isRecordingVoice) {
      // Stop recording
      this.isRecordingVoice = false;
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }
      if (micIcon) micIcon.textContent = '🎙️';
      if (label) label.textContent = 'Processing Voice Query...';
      return;
    }

    // Start recording
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.showToast('Microphone input is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.isRecordingVoice = true;
      this.audioChunks = [];
      if (micIcon) micIcon.textContent = '⏹️';
      if (label) label.textContent = 'Listening... Click to Finish';

      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const base64Data = reader.result.split(',')[1];
          if (micIcon) micIcon.textContent = '🎙️';
          if (label) label.textContent = 'Push to Talk (Voice Query)';

          // Submit voice query to backend
          const video = document.getElementById('main-video-player');
          const currentSec = Math.floor(video?.currentTime || 0);
          const sessId = this.currentSession?.id || this.currentSession?.session_id;

          try {
            const res = await window.RewindApi.submitVoiceQuery(sessId, base64Data, currentSec, 'safe', true);
            if (res.transcript) {
              const queryEl = document.getElementById('drawer-custom-input');
              if (queryEl) queryEl.value = res.transcript;
            }
            if (res.answer) {
              const ansBox = document.getElementById('drawer-answer-box');
              const textEl = document.getElementById('drawer-answer-text');
              const queryTitle = document.getElementById('drawer-answer-query');
              if (queryTitle) queryTitle.textContent = `"${res.transcript || 'Voice Query'}"`;
              if (textEl) textEl.textContent = res.answer;
              if (ansBox) ansBox.classList.remove('hidden');

              if (res.audio_base64) {
                const audioEl = document.getElementById('drawer-tts-audio');
                if (audioEl) {
                  audioEl.src = `data:audio/mp3;base64,${res.audio_base64}`;
                  audioEl.play().catch(() => {});
                }
              }
            }
          } catch (vErr) {
            this.showToast(`Voice query failed: ${vErr.message}`);
          }
        };
        reader.readAsDataURL(audioBlob);
      };

      this.mediaRecorder.start();
    } catch (permErr) {
      this.isRecordingVoice = false;
      if (micIcon) micIcon.textContent = '🎙️';
      if (label) label.textContent = 'Push to Talk (Voice Query)';
      this.showToast(`Microphone permission denied: ${permErr.message}`);
    }
  }

  async loadSubtitles() {
    if (this.playerSubtitles && this.playerSubtitles.length > 0) return;
    try {
      const res = await fetch('/media/interstellar.srt');
      if (res.ok) {
        const text = await res.text();
        this.playerSubtitles = this.parseSrt(text);
        console.log(`Loaded ${this.playerSubtitles.length} subtitle cues for on-screen playback.`);
      }
    } catch (e) {
      console.warn('Subtitle track load:', e);
    }
  }

  parseSrt(srtText) {
    const cues = [];
    if (!srtText) return cues;
    const blocks = srtText.trim().replace(/\r\n/g, '\n').split(/\n\s*\n/);
    for (const block of blocks) {
      const lines = block.split('\n');
      if (lines.length >= 2) {
        const timeMatch = lines[1].match(/(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/);
        if (timeMatch) {
          const start = parseInt(timeMatch[1], 10) * 3600 + parseInt(timeMatch[2], 10) * 60 + parseInt(timeMatch[3], 10) + parseInt(timeMatch[4], 10) / 1000;
          const end = parseInt(timeMatch[5], 10) * 3600 + parseInt(timeMatch[6], 10) * 60 + parseInt(timeMatch[7], 10) + parseInt(timeMatch[8], 10) / 1000;
          const text = lines.slice(2).join(' ').replace(/<[^>]+>/g, '').trim();
          if (text) {
            cues.push({ start, end, text });
          }
        }
      }
    }
    return cues;
  }

  renderActiveSubtitle(currentTime) {
    const overlay = document.getElementById('player-subtitle-overlay');
    const textEl = document.getElementById('player-subtitle-text');
    if (!overlay || !textEl || !this.playerSubtitles) return;

    const cue = this.playerSubtitles.find(c => currentTime >= c.start && currentTime <= c.end);
    if (cue) {
      textEl.textContent = cue.text;
      overlay.classList.remove('hidden');
    } else {
      overlay.classList.add('hidden');
    }
  }

  resetHudIdleTimer() {
    const hud = document.getElementById('player-hud');
    if (!hud) return;

    hud.classList.remove('idle-hidden');
    if (this.hudIdleTimer) clearTimeout(this.hudIdleTimer);

    const video = document.getElementById('main-video-player');
    const drawer = document.getElementById('player-ai-drawer');

    // Only hide HUD if video is actively playing and drawer is NOT open
    if (video && !video.paused && (!drawer || !drawer.classList.contains('open'))) {
      this.hudIdleTimer = setTimeout(() => {
        hud.classList.add('idle-hidden');
      }, 4500);
    }
  }

  /* -------------------------------------------------------------
     Screen 4: Companion & Question Submission
     ------------------------------------------------------------- */

  bindCompanionEvents() {
    // Preset questions
    document.querySelectorAll('.preset-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const questionText = btn.getAttribute('data-q');
        if (questionText) {
          this.submitQuestion(questionText);
        }
      });
    });

    // Custom input submit button
    document.getElementById('btn-submit-question')?.addEventListener('click', () => {
      const input = document.getElementById('custom-question-input');
      const val = input?.value?.trim();
      if (val) {
        this.submitQuestion(val);
      }
    });

    // Enter key inside custom input
    document.getElementById('custom-question-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const val = e.target.value?.trim();
        if (val) {
          this.submitQuestion(val);
        }
      }
    });

    // Push-to-Talk Voice Button (REWIND-REQ-020)
    const pttBtn = document.getElementById('btn-voice-ptt');
    const pttLabel = document.getElementById('voice-ptt-label');
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];

    pttBtn?.addEventListener('click', async () => {
      if (!this.currentSession) return;
      if (!isRecording) {
        try {
          if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = (e) => {
              if (e.data.size > 0) audioChunks.push(e.data);
            };
            mediaRecorder.onstop = async () => {
              const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
              const reader = new FileReader();
              reader.onloadend = async () => {
                const b64 = reader.result.split(',')[1];
                await this.submitVoiceQuery(b64);
              };
              reader.readAsDataURL(audioBlob);
              stream.getTracks().forEach(track => track.stop());
            };
            mediaRecorder.start();
            isRecording = true;
            if (pttLabel) pttLabel.textContent = 'Listening... (Click to Send)';
            pttBtn.classList.add('recording-pulse');
            this.showToast('Microphone active. Speak your story question now.');
          } else {
            this.showToast('MediaDevices unavailable; using voice assistant fallback.');
            const fakeAudioB64 = btoa('MOCK_STT:What is happening in this scene right now?');
            await this.submitVoiceQuery(fakeAudioB64);
          }
        } catch (micErr) {
          this.showToast(`Mic access: ${micErr.message}. Running voice assistant fallback.`);
          const fakeAudioB64 = btoa('MOCK_STT:Explain the current scene simply.');
          await this.submitVoiceQuery(fakeAudioB64);
        }
      } else {
        isRecording = false;
        if (pttLabel) pttLabel.textContent = 'Processing Voice...';
        pttBtn.classList.remove('recording-pulse');
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
        }
      }
    });

    document.getElementById('btn-search-subtitle-line')?.addEventListener('click', () => {
      this.searchSubtitleLines();
    });
    document.getElementById('subtitle-line-query')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.searchSubtitleLines();
    });
    document.getElementById('btn-load-characters')?.addEventListener('click', () => {
      this.loadCharacterCards();
    });

    // Adjust time button
    document.getElementById('comp-btn-adjust-time')?.addEventListener('click', () => {
      this.showScreen('s3-details');
    });

    // Toggle mode button
    document.getElementById('comp-btn-toggle-safe')?.addEventListener('click', async () => {
      if (!this.currentSession) return;
      if (this.currentSession.spoiler_mode === 'safe') {
        this.showToast('To switch to Full Spoilers, submit a future question to obtain verification nonce.');
      } else {
        await window.RewindApi.revertSafeMode(this.currentSession.session_id);
        this.currentSession.spoiler_mode = 'safe';
        this.updateCompanionContext();
        this.showToast('Reverted to Safe Mode (future spoilers protected).');
      }
    });
  }

  async submitVoiceQuery(audioB64) {
    if (!this.currentSession) return;
    const loader = document.getElementById('question-loader');
    loader?.classList.remove('hidden');

    try {
      const response = await window.RewindApi.submitVoiceQuery(
        this.currentSession.session_id,
        audioB64,
        this.currentSession.current_position_seconds,
        this.currentSession.spoiler_mode || 'safe',
        true
      );
      loader?.classList.add('hidden');
      const pttLabel = document.getElementById('voice-ptt-label');
      if (pttLabel) pttLabel.textContent = 'Push to Talk';

      const qInput = document.getElementById('custom-question-input');
      if (qInput && response.recognized_question) {
        qInput.value = response.recognized_question;
      }
      this.lastSubmittedQuestion = response.recognized_question;
      this.showToast(`Recognized: "${response.recognized_question}"`);

      // Play synthesized audio if available (AT-11)
      if (response.audio_base64) {
        const ttsPlayer = document.getElementById('assistant-tts-player');
        if (ttsPlayer) {
          ttsPlayer.src = `data:audio/wav;base64,${response.audio_base64}`;
          ttsPlayer.play().catch(() => {});
        }
      }

      this.handleQuestionOutcome(response);
    } catch (err) {
      loader?.classList.add('hidden');
      const pttLabel = document.getElementById('voice-ptt-label');
      if (pttLabel) pttLabel.textContent = 'Push to Talk';
      this.showToast(`Voice query failed: ${err.message}`);
    }
  }


  updateCompanionContext() {
    if (!this.currentSession) return;

    const movieTitle = this.selectedMovie?.display_title || 'Interstellar';
    document.getElementById('comp-title-val').textContent = movieTitle;
    document.getElementById('comp-pos-val').textContent = this.formatTime(this.currentSession.current_position_seconds);

    const badge = document.getElementById('comp-spoiler-badge');
    if (this.currentSession.spoiler_mode === 'safe') {
      badge.textContent = '🛡️ SAFE (Protected)';
      badge.className = 'ctx-val spoiler-badge safe';
    } else {
      badge.textContent = '⚠️ FULL SPOILERS';
      badge.className = 'ctx-val spoiler-badge full';
    }
  }

  async submitQuestion(questionText) {
    if (!this.currentSession) return;

    this.lastSubmittedQuestion = questionText;
    const loader = document.getElementById('question-loader');
    loader?.classList.remove('hidden');

    try {
      const response = await window.RewindApi.askQuestion(
        this.currentSession.session_id,
        questionText
      );

      loader?.classList.add('hidden');
      this.handleQuestionOutcome(response);
    } catch (err) {
      loader?.classList.add('hidden');
      this.showToast(`Error: ${err.message}`);
    }
  }

  async searchSubtitleLines() {
    if (!this.currentSession) return;
    const query = document.getElementById('subtitle-line-query')?.value?.trim();
    const results = document.getElementById('subtitle-line-results');
    if (!query || query.length < 2) {
      this.showToast('Enter at least two words or characters from the subtitle.');
      return;
    }
    results.textContent = 'Searching available subtitle passages…';
    try {
      const response = await window.RewindApi.searchSubtitleLines(
        this.currentSession.session_id,
        query
      );
      results.replaceChildren();
      if (!response.items?.length) {
        results.textContent = 'No matching subtitle is available within this spoiler boundary.';
        return;
      }
      response.items.forEach(line => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'subtitle-result tv-focusable';
        button.tabIndex = 0;
        button.textContent = `${this.formatTime(line.start_time_seconds)} · ${line.text}`;
        button.addEventListener('click', () => this.translateSubtitle(line));
        results.appendChild(button);
      });
    } catch (err) {
      results.textContent = `Could not search subtitles: ${err.message}`;
    }
  }

  async translateSubtitle(line) {
    const targetLocale = document.getElementById('translation-target-locale')?.value || 'hi';
    const explainContext = document.getElementById('translation-explain-context')?.checked ?? true;
    try {
      const response = await window.RewindApi.translateSubtitle(
        this.currentSession.session_id,
        line.cue_id,
        targetLocale,
        explainContext
      );
      if (response.outcome !== 'translated') {
        this.showToast(response.message || 'Translation abstained: the line could not be translated reliably.');
        return;
      }
      this.renderTranslation(response);
      this.showScreen('s5-answer');
    } catch (err) {
      this.showToast(`Translation failed: ${err.message}`);
    }
  }

  async loadCharacterCards() {
    if (!this.currentSession) return;
    const container = document.getElementById('character-card-results');
    container.textContent = 'Loading character details…';
    try {
      const response = await window.RewindApi.getCharacters(this.currentSession.session_id);
      container.replaceChildren();
      if (!response.items?.length) {
        container.textContent = 'No curated character facts are available up to this point.';
        return;
      }
      response.items.forEach(character => {
        const card = document.createElement('article');
        card.className = 'character-card tv-focusable';
        card.tabIndex = 0;
        const heading = document.createElement('h4');
        heading.textContent = character.character_name;
        card.appendChild(heading);
        character.facts.forEach(fact => {
          const text = document.createElement('p');
          text.textContent = fact.relationship
            ? `${fact.fact} ${fact.relationship}`
            : fact.fact;
          card.appendChild(text);
          const reveal = document.createElement('span');
          reveal.className = 'character-reveal-time';
          reveal.textContent = `Known by ${this.formatTime(fact.first_known_at_seconds)}`;
          card.appendChild(reveal);
        });
        container.appendChild(card);
      });
    } catch (err) {
      container.textContent = `Could not load character details: ${err.message}`;
    }
  }

  handleQuestionOutcome(response) {
    const outcome = response?.outcome;

    if (outcome === 'answered') {
      // Screen 5: Grounded Answer
      this.renderAnswer(response);
      this.showScreen('s5-answer');
    } else if (outcome === 'spoiler_confirmation_required') {
      // Screen 7: Spoiler Confirmation Modal
      this.pendingSpoilerNonce = response.confirmation_nonce;
      this.openSpoilerModal(response);
    } else if (outcome === 'insufficient_evidence') {
      // Screen 6: Clarification & Safe Abstention
      document.getElementById('clarification-text').textContent = response.answer;
      this.showScreen('s6-clarification');
    } else {
      this.showToast(response?.answer || 'Response received.');
    }
  }

  /* -------------------------------------------------------------
     Screen 5: Grounded Answer & Citations
     ------------------------------------------------------------- */

  bindAnswerEvents() {
    document.getElementById('btn-ans-ask-another')?.addEventListener('click', () => {
      this.showScreen('s4-companion');
    });

    document.getElementById('btn-ans-adjust-progress')?.addEventListener('click', () => {
      this.showScreen('s3-details');
    });
  }

  renderAnswer(response) {
    document.getElementById('translation-answer')?.classList.add('hidden');
    document.getElementById('ans-body-text')?.classList.remove('hidden');
    document.getElementById('answer-badge-label').textContent = 'GROUNDED IN DIALOGUE';
    document.getElementById('ans-query-display').textContent = `"${this.lastSubmittedQuestion}"`;
    document.getElementById('ans-body-text').textContent = response.answer;
    document.getElementById('ans-playback-tag').textContent = `Scene up to ${this.formatTime(this.currentSession?.current_position_seconds || 50)}`;

    const container = document.getElementById('ans-citations-container');
    container.innerHTML = '';

    const citations = response.citations || (response.citation ? [response.citation] : []);
    if (citations.length === 0) {
      container.innerHTML = `<span style="color: var(--text-muted); font-size: 13px;">No direct citations referenced.</span>`;
      return;
    }

    citations.forEach(cit => {
      const card = document.createElement('div');
      card.className = 'citation-card';
      card.innerHTML = `
        <span class="citation-time-badge">${this.formatTime(cit.start_time_seconds)} - ${this.formatTime(cit.end_time_seconds)}</span>
        <p class="citation-quote">"${this.escapeHtml(cit.text)}"</p>
      `;
      container.appendChild(card);
    });
  }

  renderTranslation(response) {
    const translation = document.getElementById('translation-answer');
    document.getElementById('ans-body-text').classList.add('hidden');
    translation.classList.remove('hidden');
    document.getElementById('answer-badge-label').textContent = 'TRANSLATED FROM AUTHORIZED SUBTITLE';
    document.getElementById('ans-query-display').textContent =
      `Translation to ${response.target_locale.toUpperCase()}`;
    document.getElementById('ans-playback-tag').textContent =
      `Scene ${this.formatTime(response.citation.start_time_seconds)}`;
    document.getElementById('translation-original').textContent = response.original_text;
    document.getElementById('translation-translated').textContent = response.translation;
    const explanation = document.getElementById('translation-explanation-wrap');
    if (response.contextual_explanation) {
      explanation.classList.remove('hidden');
      document.getElementById('translation-explanation').textContent = response.contextual_explanation;
    } else {
      explanation.classList.add('hidden');
      document.getElementById('translation-explanation').textContent = '';
    }
    const container = document.getElementById('ans-citations-container');
    container.replaceChildren();
    const citation = document.createElement('div');
    citation.className = 'citation-card';
    const time = document.createElement('span');
    time.className = 'citation-time-badge';
    time.textContent =
      `${this.formatTime(response.citation.start_time_seconds)} - ${this.formatTime(response.citation.end_time_seconds)}`;
    const quote = document.createElement('p');
    quote.className = 'citation-quote';
    quote.textContent = response.citation.text;
    citation.append(time, quote);
    container.appendChild(citation);
  }

  /* -------------------------------------------------------------
     Screen 6: Clarification & Abstention
     ------------------------------------------------------------- */

  bindClarificationEvents() {
    document.getElementById('btn-clari-back-companion')?.addEventListener('click', () => {
      this.showScreen('s4-companion');
    });

    document.getElementById('clari-opt-advance')?.addEventListener('click', () => {
      this.showScreen('s3-details');
    });

    document.getElementById('clari-opt-rephrase')?.addEventListener('click', () => {
      this.showScreen('s4-companion');
    });

    document.getElementById('clari-opt-safe')?.addEventListener('click', () => {
      this.showToast('Safe mode is currently active. Adjust time slider or unlock spoilers.');
    });
  }

  /* -------------------------------------------------------------
     Screen 7: Spoiler Confirmation Modal (SRS-SPO-004, AC-009)
     ------------------------------------------------------------- */

  bindSpoilerModalEvents() {
    // Default focus is Cancel to protect against accidental click
    document.getElementById('btn-spoiler-cancel')?.addEventListener('click', () => {
      this.closeModal();
      this.showToast('Spoilers prevented. Kept in Safe Mode.');
    });

    document.getElementById('btn-spoiler-confirm')?.addEventListener('click', async () => {
      if (!this.pendingSpoilerNonce || !this.currentSession) return;

      try {
        const confRes = await window.RewindApi.confirmSpoiler(
          this.currentSession.session_id,
          this.pendingSpoilerNonce
        );
        this.currentSession.spoiler_mode = confRes.spoiler_mode;
        this.closeModal();
        this.updateCompanionContext();
        this.showToast('Elevated to Full Spoilers. Answering question...');

        // Re-execute question now that mode is full
        if (this.lastSubmittedQuestion) {
          this.submitQuestion(this.lastSubmittedQuestion);
        }
      } catch (err) {
        this.showToast(`Confirmation rejected: ${err.message}`);
      }
    });
  }

  openSpoilerModal(response) {
    const modal = document.getElementById('s7-spoiler-modal');
    document.getElementById('modal-spoiler-explanation').textContent = response.answer;
    document.getElementById('modal-nonce-val').textContent = response.confirmation_nonce || 'AUTHORIZED-NONCE';
    
    // Default focus must be CANCEL
    window.TvNavigator?.trapModalFocus(modal, 'btn-spoiler-cancel');
  }

  /* -------------------------------------------------------------
     Screen 8: Settings & Privacy
     ------------------------------------------------------------- */

  bindSettingsEvents() {
    document.getElementById('btn-clear-session')?.addEventListener('click', () => {
      this.currentSession = null;
      this.selectedMovie = null;
      document.getElementById('hdr-movie-title').textContent = 'No Active Title';
      document.getElementById('hdr-progress-time').textContent = '00:00:00';
      this.showToast('Session reset. Progress cleared.');
      this.showScreen('s2-catalog');
    });
  }

  /* -------------------------------------------------------------
     Screen 9: Admin Diagnostics & Ingestion
     ------------------------------------------------------------- */

  bindAdminEvents() {
    document.getElementById('btn-admin-run-sample')?.addEventListener('click', async () => {
      const log = document.getElementById('admin-log-output');
      const movieSelect = document.getElementById('admin-movie-select');
      const movieId = movieSelect?.value || 'interstellar-epic';
      const adminToken = this.getAdminToken();

      log.textContent = `Starting ingestion for title ${movieId}...\nValidating subtitle checksum & timestamps...`;

      try {
        const res = await window.RewindApi.adminIngest(movieId, this.sampleSrt, true, adminToken);
        log.textContent = `[SUCCESS] Ingested Content Version: ${res.content_version_id}\n` +
                          `Status: ${res.status}\n` +
                          `Chunks Created: ${res.chunks_created}\n` +
                          `Time Range: 0s to ${res.max_end_time_seconds}s\n` +
                          `Checksum: ${res.checksum}\n` +
                          `Version is active and ready for questions!`;
        this.showToast('Test subtitle ingested & published successfully.');
        await this.loadCatalog();
      } catch (err) {
        log.textContent = `[ERROR] Ingestion failed: ${err.message}`;
      }
    });
  }

  getAdminToken() {
    return document.getElementById('admin-api-token')?.value.trim() || '';
  }

  async seedSampleMovie() {
    this.showToast('Seeding Interstellar into catalog...');
    try {
      await window.RewindApi.adminIngest('interstellar-epic', this.sampleSrt, true, this.getAdminToken());
      this.showToast('Seeded! Reloading catalog...');
      await this.loadCatalog();
    } catch (err) {
      this.showToast(`Seeding failed: ${err.message}`);
    }
  }

  async checkBackendStatus() {
    try {
      const health = await window.RewindApi.checkHealth();
      const pill = document.getElementById('admin-health-pill');
      const text = document.getElementById('admin-health-text');
      if (health?.status === 'ready') {
        text.textContent = 'API Ready (Connected)';
      }
    } catch {
      const text = document.getElementById('admin-health-text');
      if (text) text.textContent = 'Backend Offline';
    }
  }

  /* -------------------------------------------------------------
     Utilities
     ------------------------------------------------------------- */

  formatTime(totalSeconds) {
    if (!totalSeconds || isNaN(totalSeconds)) totalSeconds = 0;
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = Math.floor(totalSeconds % 60);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'tv-toast';
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  bindProviderEvents() {
    this.activeProvider = 'netflix';
    const providerButtons = document.querySelectorAll('.provider-btn');
    providerButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        providerButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeProvider = btn.getAttribute('data-provider') || 'netflix';
        const providerName = btn.textContent.trim();
        const compProviderEl = document.getElementById('comp-provider-val');
        if (compProviderEl) compProviderEl.textContent = providerName;
        const hdrMovieEl = document.getElementById('hdr-movie-title');
        if (hdrMovieEl && this.activeMovie) {
          hdrMovieEl.textContent = `[${providerName}] ${this.activeMovie.display_title || this.activeMovie.title}`;
        }
        this.showToast(`Switched active streaming app to ${providerName}`);
      });
    });

    const returnBtn = document.getElementById('comp-btn-return-stream');
    if (returnBtn) {
      returnBtn.addEventListener('click', () => {
        this.simulateReturnToStream();
      });
    }
  }

  simulateReturnToStream() {
    const providerName = document.querySelector('.provider-btn.active')?.textContent.trim() || 'Streaming App';
    this.showToast(`Returning to ${providerName}... Rewind overlay dismissed.`);
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}


// Global App instance
window.TvApp = new RewindTvApp();
