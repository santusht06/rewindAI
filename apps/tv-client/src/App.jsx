import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { useSpeech } from './hooks/useSpeech';
import { CatalogHero } from './components/CatalogHero';
import { VideoPlayer } from './components/VideoPlayer';

export function App() {
  const [viewMode, setViewMode] = useState('player'); // 'catalog' | 'player'
  const [movie, setMovie] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const speech = useSpeech();

  // Load movie and active session on mount
  useEffect(() => {
    async function init() {
      try {
        const titlesData = await api.getTitles();
        const activeMovie = titlesData.items?.[0] || {
          id: 'interstellar-epic',
          display_title: 'Interstellar',
          year: 2014,
          duration_seconds: 10145,
          stream_url: '/media/interstellar.mp4',
        };
        setMovie(activeMovie);

        // Create or bind session
        const sess = await api.createSession(activeMovie.id);
        setSession(sess);
      } catch (err) {
        console.warn('Initialization note:', err);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const handleSyncProgress = async (positionSeconds) => {
    if (session?.session_id) {
      await api.syncProgress(session.session_id, positionSeconds);
    }
  };

  const handleAskQuestion = async (question, positionSeconds) => {
    if (!session?.session_id) {
      // Create session on the fly if needed
      const sess = await api.createSession(movie?.id || 'interstellar-epic');
      setSession(sess);
      return await api.askQuestion(sess.session_id, question, positionSeconds);
    }
    return await api.askQuestion(session.session_id, question, positionSeconds);
  };

  if (loading) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          background: '#000000',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
          letterSpacing: '0.08em',
        }}
      >
        <span>LOADING REWIND AI...</span>
      </div>
    );
  }

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#000000', overflow: 'hidden' }}>
      {viewMode === 'catalog' ? (
        <CatalogHero
          movie={movie}
          onPlayMovie={() => setViewMode('player')}
          onOpenAI={() => setViewMode('player')}
        />
      ) : (
        <VideoPlayer
          movie={movie}
          sessionId={session?.session_id}
          onBack={() => setViewMode('catalog')}
          onSyncProgress={handleSyncProgress}
          onAskQuestion={handleAskQuestion}
          speech={speech}
        />
      )}
    </div>
  );
}

export default App;
