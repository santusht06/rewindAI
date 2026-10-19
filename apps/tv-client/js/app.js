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
    this.bindCompanionEvents();
    this.bindAnswerEvents();
    this.bindClarificationEvents();
    this.bindSpoilerModalEvents();
    this.bindSettingsEvents();
    this.bindAdminEvents();

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
        if (targetScreen) {
          this.showScreen(targetScreen);
        }
      });
    });
  }

  showScreen(screenId) {
    if (this.currentScreen === screenId) return;

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

    // Start Session Action
    document.getElementById('btn-start-session')?.addEventListener('click', () => {
      this.startViewingSession();
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
