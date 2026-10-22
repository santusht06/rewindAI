/**
 * Rewind TV API Client
 * Typed communication layer matching the authoritative 04_API_CONTRACT.
 */

class RewindApiClient {
  constructor(baseUrl = '') {
    // If running in browser alongside FastAPI, use origin; otherwise localhost:8000
    this.baseUrl = baseUrl || (window.location.origin.includes('http') ? `${window.location.origin}/api/v1` : 'http://localhost:8000/api/v1');
    this.userId = localStorage.getItem('rewind_user_id') || 'viewer-firetv-default';
  }

  setUserId(userId) {
    this.userId = userId;
    localStorage.setItem('rewind_user_id', userId);
  }

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-User-ID': this.userId,
    };
  }

  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const defaultHeaders = this.getHeaders();
    
    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const error = new Error(data?.message || `HTTP ${response.status}: Request failed`);
        error.status = response.status;
        error.code = data?.code || 'API_ERROR';
        error.requestId = data?.request_id;
        error.details = data?.details;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        const netErr = new Error('Cannot connect to Rewind Backend. Is the API server running?');
        netErr.code = 'NETWORK_OFFLINE';
        throw netErr;
      }
      throw err;
    }
  }

  // Titles
  async getTitles(limit = 20, offset = 0) {
    return this._request(`/titles?limit=${limit}&offset=${offset}`);
  }

  async getTitle(titleId) {
    return this._request(`/titles/${encodeURIComponent(titleId)}`);
  }

  // Sessions
  async createSession(titleId, initialPosition = 0, spoilerMode = 'safe') {
    return this._request('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        title_id: titleId,
        position_seconds: initialPosition,
        source: 'manual_slider',
      }),
    });
  }

  async getSession(sessionId) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}`);
  }

  async updateProgress(sessionId, positionSeconds, source = 'manual_slider') {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/progress`, {
      method: 'PATCH',
      body: JSON.stringify({
        position_seconds: positionSeconds,
        current_position_seconds: positionSeconds,
        source: source,
      }),
    });
  }

  async confirmSpoiler(sessionId, nonce) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/spoiler-confirmation`, {
      method: 'POST',
      body: JSON.stringify({
        confirmation_nonce: nonce,
      }),
    });
  }

  async revertSafeMode(sessionId) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/safe-mode`, {
      method: 'POST',
    });
  }

  // Question & RAG
  async askQuestion(sessionId, questionText) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/questions`, {
      method: 'POST',
      body: JSON.stringify({
        question: questionText,
      }),
    });
  }

  async searchSubtitleLines(sessionId, query) {
    return this._request(
      `/sessions/${encodeURIComponent(sessionId)}/subtitle-lines?query=${encodeURIComponent(query)}`
    );
  }

  async translateSubtitle(sessionId, cueId, targetLocale, explainContext = true) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/translations`, {
      method: 'POST',
      body: JSON.stringify({
        cue_id: cueId,
        target_locale: targetLocale,
        explain_context: explainContext,
      }),
    });
  }

  async getCharacters(sessionId) {
    return this._request(`/sessions/${encodeURIComponent(sessionId)}/characters`);
  }

  // Admin Ingestion & Publish
  async adminIngest(movieId, subtitleContent, autoPublish = true, adminToken = '') {
    return this._request(`/admin/titles/${encodeURIComponent(movieId)}/ingest`, {
      method: 'POST',
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {},
      body: JSON.stringify({
        raw_content: subtitleContent,
        auto_publish: autoPublish,
      }),
    });
  }

  async adminPublishVersion(movieId, contentVersionId, adminToken = '') {
    return this._request(`/admin/titles/${encodeURIComponent(movieId)}/publish-version/${encodeURIComponent(contentVersionId)}`, {
      method: 'POST',
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {},
    });
  }

  async adminCreateCharacterFact(movieId, fact, adminToken = '') {
    return this._request(`/admin/titles/${encodeURIComponent(movieId)}/character-facts`, {
      method: 'POST',
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {},
      body: JSON.stringify(fact),
    });
  }

  // System Health
  async checkHealth() {
    const healthUrl = this.baseUrl.replace('/api/v1', '/health/ready');
    const res = await fetch(healthUrl);
    return res.json();
  }

  // Cross-App Assistant & Provider Registry
  async getAssistantProviders() {
    return this._request('/assistant/providers');
  }

  async getAssistantModes() {
    return this._request('/assistant/modes');
  }

  async getAssistantContext(sessionId) {
    return this._request(`/assistant/sessions/${encodeURIComponent(sessionId)}/context`);
  }

  async updateAssistantContext(sessionId, providerId, positionSeconds, source = 'manual_slider') {
    return this._request(`/assistant/sessions/${encodeURIComponent(sessionId)}/context`, {
      method: 'POST',
      body: JSON.stringify({
        provider_id: providerId,
        position_seconds: positionSeconds,
        source: source,
      }),
    });
  }

  // Push-To-Talk Voice Query (REWIND-REQ-018 / 020)
  async submitVoiceQuery(sessionId, audioBase64, positionSeconds = null, spoilerMode = 'safe', synthesizeSpeech = true) {
    return this._request('/assistant/voice-query', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        audio_base64: audioBase64,
        playback_position_seconds: positionSeconds,
        spoiler_mode: spoilerMode,
        synthesize_speech: synthesizeSpeech,
      }),
    });
  }

  // Media Processing Pipeline (REWIND-REQ-019)
  async adminUploadMedia(movieId, fileName, fileBase64, contentType = 'video/mp4', suppliedSrt = null, adminToken = '') {
    return this._request(`/admin/movies/${encodeURIComponent(movieId)}/media`, {
      method: 'POST',
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {},
      body: JSON.stringify({
        file_name: fileName,
        file_base64: fileBase64,
        content_type: contentType,
        supplied_srt_content: suppliedSrt,
      }),
    });
  }

  async adminGetJobStatus(jobId, adminToken = '') {
    return this._request(`/admin/jobs/${encodeURIComponent(jobId)}`, {
      headers: adminToken ? { 'X-Admin-Token': adminToken } : {},
    });
  }
}


// Global API instance
window.RewindApi = new RewindApiClient();

