import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Send,
  Volume2,
  VolumeX,
  Sparkles,
  Clock,
  ChevronRight,
  Loader2,
  MessageSquare,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';

export function AICompanionDrawer({
  isOpen,
  onClose,
  currentTime,
  sessionId,
  onAskQuestion,
  onSeekTo,
  speech,
}) {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Suggested questions based on movie narrative
  const suggestedQuestions = [
    'Who are they and what are they talking about?',
    'What was the gravitational anomaly Cooper found?',
    'Why is Cooper piloting the Endurance mission?',
    'Explain the wormhole near Saturn.',
  ];

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, isLoading]);

  const formatTimestamp = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) {
      return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleSubmit = async (textToSubmit) => {
    const q = (textToSubmit || question).trim();
    if (!q || isLoading) return;

    setError(null);
    setIsLoading(true);
    setQuestion('');

    const pauseTime = currentTime;
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      text: q,
      timestamp: pauseTime,
    };

    setHistory((prev) => [...prev, userMessage]);

    try {
      const response = await onAskQuestion(q, pauseTime);
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: response.answer || response.clarification_prompt || 'Analyzing scene dialogue...',
        citations: response.citations || [],
        timestamp: pauseTime,
      };

      setHistory((prev) => [...prev, aiMessage]);

      // Speak aloud using speech hook
      if (response.answer && !speech.isMuted) {
        speech.speak(response.answer, response.audio_base64, response.audio_mime_type);
      }
    } catch (err) {
      setError(err.message || 'Failed to get answer. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <aside
      style={{
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        width: '440px',
        maxWidth: '90vw',
        background: 'rgba(8, 8, 8, 0.94)',
        backdropFilter: 'blur(30px) saturate(180%)',
        WebkitBackdropFilter: 'blur(30px) saturate(180%)',
        borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-16px 0 48px rgba(0, 0, 0, 0.8)',
        animation: 'slideInRight 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Drawer Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: '#ffffff',
              color: '#000000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '15px', fontWeight: 600, letterSpacing: '-0.01em', color: '#ffffff' }}>
              Story Companion
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#22c55e',
                  boxShadow: '0 0 6px #22c55e',
                }}
              />
              <span style={{ fontSize: '11px', color: '#888888', fontFamily: 'var(--font-mono)' }}>
                PAUSED AT {formatTimestamp(currentTime)} • SPOILER SAFE
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* TTS Readout Toggle */}
          <button
            onClick={speech.toggleMute}
            title={speech.isMuted ? 'Voice readout muted' : 'Voice readout active'}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: speech.isMuted ? 'transparent' : 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: speech.isMuted ? '#666666' : '#ffffff',
            }}
          >
            {speech.isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>

          {/* Close button */}
          <button
            onClick={onClose}
            title="Close Drawer (Esc)"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#888888',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#888888')}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        {history.length === 0 && (
          <div style={{ marginTop: '10px' }}>
            <p style={{ fontSize: '13px', color: '#999999', lineHeight: 1.6, marginBottom: '16px' }}>
              Ask questions about the plot, characters, or scenes. The AI only knows dialogue up to{' '}
              <span style={{ color: '#ffffff', fontFamily: 'var(--font-mono)' }}>{formatTimestamp(currentTime)}</span>, guaranteeing no spoilers.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#555555', fontWeight: 600 }}>
                Suggested Questions
              </span>
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSubmit(q)}
                  style={{
                    textAlign: 'left',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    background: '#121212',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    color: '#e0e0e0',
                    fontSize: '13px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px',
                    lineHeight: 1.4,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#1a1a1a';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                    e.currentTarget.style.color = '#ffffff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#121212';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                    e.currentTarget.style.color = '#e0e0e0';
                  }}
                >
                  <span>{q}</span>
                  <ChevronRight size={14} style={{ color: '#666666', flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.role === 'user' ? '85%' : '100%',
              gap: '6px',
            }}
          >
            {msg.role === 'user' ? (
              <div
                style={{
                  background: '#222222',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '12px 12px 2px 12px',
                  padding: '10px 14px',
                  color: '#ffffff',
                  fontSize: '13px',
                  lineHeight: 1.5,
                }}
              >
                {msg.text}
              </div>
            ) : (
              <div
                style={{
                  background: '#111111',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px 12px 12px 2px',
                  padding: '16px',
                  color: '#f0f0f0',
                  fontSize: '14px',
                  lineHeight: 1.6,
                }}
              >
                <div style={{ marginBottom: '10px' }}>{msg.text}</div>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div
                    style={{
                      marginTop: '12px',
                      paddingTop: '10px',
                      borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#666666', fontWeight: 600 }}>
                      Dialogue Evidence
                    </span>
                    {msg.citations.map((cite, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onSeekTo && onSeekTo(cite.start_time_seconds)}
                        title="Click to jump to this scene"
                        style={{
                          textAlign: 'left',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '12px',
                          color: '#cccccc',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                        }}
                      >
                        <Clock size={12} style={{ color: '#888888', flexShrink: 0 }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#ffffff' }}>
                          {formatTimestamp(cite.start_time_seconds)}
                        </span>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, color: '#999999' }}>
                          "{cite.text.slice(0, 45)}..."
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '14px 16px',
              background: '#111111',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: '#888888',
              fontSize: '13px',
            }}
          >
            <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            <span>Analyzing dialogue & plot context...</span>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: '10px 14px',
              background: 'rgba(229, 9, 20, 0.1)',
              border: '1px solid rgba(229, 9, 20, 0.3)',
              borderRadius: '8px',
              color: '#ff8888',
              fontSize: '12px',
            }}
          >
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Deck */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(10, 10, 10, 0.98)',
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#161616',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '8px',
            padding: '4px 6px 4px 14px',
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about this scene or character..."
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#ffffff',
              fontSize: '13px',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <button
            type="submit"
            disabled={!question.trim() || isLoading}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: question.trim() ? '#ffffff' : 'rgba(255, 255, 255, 0.08)',
              color: question.trim() ? '#000000' : '#444444',
              cursor: question.trim() && !isLoading ? 'pointer' : 'not-allowed',
            }}
          >
            <Send size={14} />
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px' }}>
          <span style={{ fontSize: '11px', color: '#555555' }}>Press Space to play/pause • Esc to close</span>
          {history.length > 0 && (
            <button
              onClick={() => setHistory([])}
              style={{
                fontSize: '11px',
                color: '#666666',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#666666')}
            >
              <RotateCcw size={11} /> Clear chat
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
