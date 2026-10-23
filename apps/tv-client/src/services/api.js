/**
 * Rewind AI API Service
 * Handles session management, playback progress sync, and context-bounded AI queries.
 */

const API_BASE = '/api/v1';
const DEFAULT_USER_ID = 'viewer-firetv-default';

class RewindAPI {
  constructor() {
    this.userId = DEFAULT_USER_ID;
  }

  _headers(extra = {}) {
    return {
      'Content-Type': 'application/json',
      'X-User-ID': this.userId,
      ...extra,
    };
  }

  async checkHealth() {
    try {
      const res = await fetch('/health/ready');
      return await res.json();
    } catch {
      return { status: 'offline' };
    }
  }

  async getTitles() {
    const res = await fetch(`${API_BASE}/titles`, {
      headers: this._headers(),
    });
    if (!res.ok) throw new Error(`Failed to load titles: ${res.status}`);
    return await res.json();
  }

  async createSession(titleId = 'interstellar-epic') {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ title_id: titleId }),
    });
    if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
    return await res.json();
  }

  async syncProgress(sessionId, positionSeconds) {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}/progress`, {
        method: 'PATCH',
        headers: this._headers(),
        body: JSON.stringify({
          current_position_seconds: Math.floor(positionSeconds),
          progress_source: 'playback_sync',
        }),
      });
    } catch {
      // Non-critical background sync
    }
  }

  async askQuestion(sessionId, question, positionSeconds) {
    const res = await fetch(`${API_BASE}/assistant/text-query`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({
        session_id: sessionId,
        question: question.trim(),
        playback_position_seconds: positionSeconds,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `Query failed: ${res.status}`);
    }
    return await res.json();
  }
}

export const api = new RewindAPI();
