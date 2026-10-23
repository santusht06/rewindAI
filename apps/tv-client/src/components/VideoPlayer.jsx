import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  Volume2,
  Volume1,
  VolumeX,
  Maximize,
  Minimize,
  Sparkles,
  ArrowLeft,
  Settings,
  HelpCircle,
  Subtitles,
  Gauge,
} from 'lucide-react';
import { AICompanionDrawer } from './AICompanionDrawer';

export function VideoPlayer({
  movie,
  sessionId,
  onBack,
  onSyncProgress,
  onAskQuestion,
  speech,
}) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const timelineRef = useRef(null);
  const hideTimeoutRef = useRef(null);

  // Player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(movie?.duration_seconds || 10145);
  const [bufferedTime, setBufferedTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true);

  // UI state
  const [controlsVisible, setControlsVisible] = useState(true);
  const [isHoveringTimeline, setIsHoveringTimeline] = useState(false);
  const [hoverPosition, setHoverPosition] = useState(0);
  const [isDraggingTimeline, setIsDraggingTimeline] = useState(false);
  const [showRemainingTime, setShowRemainingTime] = useState(false);
  const [jumpFeedback, setJumpFeedback] = useState(null); // { type: '+10' | '-10', id: number }
  const [centerPlayIcon, setCenterPlayIcon] = useState(null); // 'play' | 'pause'
  const [isAIDrawerOpen, setIsAIDrawerOpen] = useState(false);
  const [speedMenuOpen, setSpeedMenuOpen] = useState(false);
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false);

  // Auto-hide controls after 2.5s of inactivity while playing
  const resetHideTimer = useCallback(() => {
    setControlsVisible(true);
    if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);

    if (isPlaying && !isAIDrawerOpen && !isDraggingTimeline && !speedMenuOpen && !shortcutsModalOpen) {
      hideTimeoutRef.current = setTimeout(() => {
        setControlsVisible(false);
      }, 2500);
    }
  }, [isPlaying, isAIDrawerOpen, isDraggingTimeline, speedMenuOpen, shortcutsModalOpen]);

  useEffect(() => {
    resetHideTimer();
    return () => {
      if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    };
  }, [resetHideTimer]);

  // Sync progress periodically to backend
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      if (videoRef.current) {
        onSyncProgress(videoRef.current.currentTime);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isPlaying, onSyncProgress]);

  // Video event handlers
  const handleTimeUpdate = () => {
    if (videoRef.current && !isDraggingTimeline) {
      setCurrentTime(videoRef.current.currentTime);

      // Update buffer
      const b = videoRef.current.buffered;
      if (b && b.length > 0) {
        setBufferedTime(b.end(b.length - 1));
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || movie?.duration_seconds || 10145);
    }
  };

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().then(() => {
        setIsPlaying(true);
        setCenterPlayIcon('play');
        setTimeout(() => setCenterPlayIcon(null), 600);
      }).catch(() => {});
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
      setCenterPlayIcon('pause');
      setTimeout(() => setCenterPlayIcon(null), 600);
      onSyncProgress(videoRef.current.currentTime);
    }
  }, [onSyncProgress]);

  const jumpSeconds = useCallback((delta) => {
    if (!videoRef.current) return;
    const newTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + delta));
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
    setJumpFeedback({ type: delta > 0 ? '+10' : '-10', id: Date.now() });
    setTimeout(() => setJumpFeedback(null), 700);
    resetHideTimer();
  }, [duration, resetHideTimer]);

  const handleSeek = (newSeconds) => {
    if (!videoRef.current) return;
    const clamped = Math.max(0, Math.min(duration, newSeconds));
    videoRef.current.currentTime = clamped;
    setCurrentTime(clamped);
    onSyncProgress(clamped);
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const next = !isMuted;
    videoRef.current.muted = next;
    setIsMuted(next);
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (videoRef.current) {
      videoRef.current.volume = val;
      videoRef.current.muted = val === 0;
      setIsMuted(val === 0);
    }
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const handleSpeedSelect = (rate) => {
    setPlaybackRate(rate);
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
    }
    setSpeedMenuOpen(false);
  };

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignore if user is typing in an input
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        if (e.key === 'Escape') {
          setIsAIDrawerOpen(false);
        }
        return;
      }

      switch (e.key.toLowerCase()) {
        case ' ':
        case 'k':
          e.preventDefault();
          togglePlay();
          break;
        case 'j':
        case 'arrowleft':
          e.preventDefault();
          jumpSeconds(-10);
          break;
        case 'l':
        case 'arrowright':
          e.preventDefault();
          jumpSeconds(10);
          break;
        case 'arrowup':
          e.preventDefault();
          setVolume((v) => {
            const next = Math.min(1, v + 0.1);
            if (videoRef.current) videoRef.current.volume = next;
            return next;
          });
          break;
        case 'arrowdown':
          e.preventDefault();
          setVolume((v) => {
            const next = Math.max(0, v - 0.1);
            if (videoRef.current) videoRef.current.volume = next;
            return next;
          });
          break;
        case 'm':
          toggleMute();
          break;
        case 'f':
          toggleFullscreen();
          break;
        case 'q':
          e.preventDefault();
          if (isPlaying) togglePlay();
          setIsAIDrawerOpen((prev) => !prev);
          break;
        case 'escape':
          setIsAIDrawerOpen(false);
          setSpeedMenuOpen(false);
          setShortcutsModalOpen(false);
          break;
        case '?':
          setShortcutsModalOpen((prev) => !prev);
          break;
        default:
          break;
      }
      resetHideTimer();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlay, jumpSeconds, resetHideTimer, isPlaying]);

  // Timeline Scrubbing calculations
  const getTimelineTimeFromEvent = (e) => {
    if (!timelineRef.current) return 0;
    const rect = timelineRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    return (x / rect.width) * duration;
  };

  const handleTimelineMouseDown = (e) => {
    setIsDraggingTimeline(true);
    const targetTime = getTimelineTimeFromEvent(e);
    handleSeek(targetTime);

    const handleMouseMove = (moveEvent) => {
      const moveTime = getTimelineTimeFromEvent(moveEvent);
      handleSeek(moveTime);
    };

    const handleMouseUp = () => {
      setIsDraggingTimeline(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleTimelineMouseMove = (e) => {
    const hoverTime = getTimelineTimeFromEvent(e);
    setHoverPosition(hoverTime);
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) {
      return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;
  const bufferPercent = duration > 0 ? (bufferedTime / duration) * 100 : 0;
  const hoverPercent = duration > 0 ? (hoverPosition / duration) * 100 : 0;

  return (
    <div
      ref={containerRef}
      onMouseMove={resetHideTimer}
      onClick={() => {
        if (!isAIDrawerOpen) {
          // Click anywhere on container to toggle play
          togglePlay();
        }
      }}
      style={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        background: '#000000',
        overflow: 'hidden',
        cursor: controlsVisible ? 'default' : 'none',
      }}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={movie?.stream_url || '/media/interstellar.mp4'}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          background: '#000000',
        }}
        playsInline
      />

      {/* Center Stage Feedback: Jump 10s & Play/Pause Flashes */}
      {jumpFeedback && (
        <div
          key={jumpFeedback.id}
          style={{
            position: 'absolute',
            top: '50%',
            left: jumpFeedback.type === '-10' ? '25%' : '75%',
            transform: 'translate(-50%, -50%)',
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            animation: 'jumpBounce 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards',
          }}
        >
          <div
            style={{
              width: '72px',
              height: '72px',
              borderRadius: '50%',
              background: 'rgba(0, 0, 0, 0.75)',
              border: '2px solid rgba(255, 255, 255, 0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            {jumpFeedback.type === '-10' ? <RotateCcw size={32} /> : <RotateCw size={32} />}
          </div>
          <span style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#ffffff' }}>
            {jumpFeedback.type}s
          </span>
        </div>
      )}

      {centerPlayIcon && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            pointerEvents: 'none',
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            animation: 'jumpBounce 0.5s ease-out forwards',
          }}
        >
          {centerPlayIcon === 'play' ? <Play size={36} fill="#ffffff" /> : <Pause size={36} fill="#ffffff" />}
        </div>
      )}

      {/* TOP SCRIM & CONTROLS (Netflix-style top bar) */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: isAIDrawerOpen ? '440px' : 0,
          padding: '28px 36px',
          background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0) 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          transition: 'opacity 0.25s var(--ease-out)',
          opacity: controlsVisible || !isPlaying ? 1 : 0,
          pointerEvents: controlsVisible || !isPlaying ? 'auto' : 'none',
          zIndex: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button
            onClick={onBack}
            title="Back to Catalog"
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#ffffff',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)')}
          >
            <ArrowLeft size={20} />
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.02em', color: '#ffffff' }}>
                {movie?.display_title || 'Interstellar'}
              </h1>
              <span style={{ fontSize: '12px', padding: '2px 6px', background: 'rgba(255, 255, 255, 0.12)', borderRadius: '4px', color: '#cccccc', fontWeight: 600 }}>
                4K HDR
              </span>
              <span style={{ fontSize: '12px', padding: '2px 6px', background: 'rgba(255, 255, 255, 0.12)', borderRadius: '4px', color: '#cccccc', fontWeight: 600 }}>
                5.1
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#888888', marginTop: '2px' }}>
              2014 • Sci-Fi / Adventure • 2h 49m
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* AI Status Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#22c55e',
                boxShadow: '0 0 8px #22c55e',
              }}
            />
            <span style={{ fontSize: '12px', color: '#e0e0e0', fontWeight: 500 }}>
              AI Companion Active
            </span>
          </div>

          <button
            onClick={() => setShortcutsModalOpen(true)}
            title="Keyboard Shortcuts (?)"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#cccccc',
            }}
          >
            <HelpCircle size={18} />
          </button>
        </div>
      </div>

      {/* BOTTOM SCRIM & CONTROLS DECK (Netflix-style bottom deck) */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: isAIDrawerOpen ? '440px' : 0,
          padding: '0 36px 28px 36px',
          background: 'linear-gradient(0deg, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.75) 50%, rgba(0, 0, 0, 0) 100%)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          transition: 'opacity 0.25s var(--ease-out)',
          opacity: controlsVisible || !isPlaying ? 1 : 0,
          pointerEvents: controlsVisible || !isPlaying ? 'auto' : 'none',
          zIndex: 20,
        }}
      >
        {/* Netflix Timeline / Seekbar */}
        <div
          ref={timelineRef}
          className={`netflix-timeline ${isDraggingTimeline ? 'dragging' : ''}`}
          onMouseDown={handleTimelineMouseDown}
          onMouseEnter={() => setIsHoveringTimeline(true)}
          onMouseLeave={() => setIsHoveringTimeline(false)}
          onMouseMove={handleTimelineMouseMove}
        >
          {/* Background Track */}
          <div className="timeline-track-bg" />

          {/* Buffered Track */}
          <div className="timeline-buffered" style={{ width: `${bufferPercent}%` }} />

          {/* Played Progress Track (Netflix Iconic Red) */}
          <div className="timeline-played" style={{ width: `${progressPercent}%` }} />

          {/* Thumb Playhead */}
          <div className="timeline-thumb" style={{ left: `${progressPercent}%` }} />

          {/* Hover Tooltip Timestamp */}
          {isHoveringTimeline && (
            <div className="timeline-tooltip" style={{ left: `${hoverPercent}%` }}>
              {formatTime(hoverPosition)}
            </div>
          )}
        </div>

        {/* Control Bar (Buttons & Controls) */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          {/* Left Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              title={isPlaying ? 'Pause (Space / K)' : 'Play (Space / K)'}
              style={{
                width: '42px',
                height: '42px',
                color: '#ffffff',
              }}
            >
              {isPlaying ? <Pause size={28} fill="#ffffff" /> : <Play size={28} fill="#ffffff" />}
            </button>

            {/* Rewind 10s */}
            <button
              onClick={() => jumpSeconds(-10)}
              title="Rewind 10 seconds (J / ←)"
              style={{
                width: '38px',
                height: '38px',
                color: '#cccccc',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#cccccc')}
            >
              <RotateCcw size={22} />
              <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>10</span>
            </button>

            {/* Forward 10s */}
            <button
              onClick={() => jumpSeconds(10)}
              title="Forward 10 seconds (L / →)"
              style={{
                width: '38px',
                height: '38px',
                color: '#cccccc',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#cccccc')}
            >
              <RotateCw size={22} />
              <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>10</span>
            </button>

            {/* Volume Control */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <button
                onClick={toggleMute}
                title={isMuted ? 'Unmute (M)' : 'Mute (M)'}
                style={{ width: '38px', height: '38px', color: '#cccccc' }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#cccccc')}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX size={22} />
                ) : volume < 0.5 ? (
                  <Volume1 size={22} />
                ) : (
                  <Volume2 size={22} />
                )}
              </button>

              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                style={{
                  width: '75px',
                  height: '4px',
                  accentColor: '#ffffff',
                  cursor: 'pointer',
                }}
              />
            </div>

            {/* Time Display */}
            <button
              onClick={() => setShowRemainingTime((prev) => !prev)}
              title="Click to toggle remaining time"
              style={{
                color: '#aaaaaa',
                fontSize: '13px',
                fontFamily: 'var(--font-mono)',
                marginLeft: '8px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#aaaaaa')}
            >
              {showRemainingTime
                ? `-${formatTime(duration - currentTime)}`
                : `${formatTime(currentTime)} / ${formatTime(duration)}`}
            </button>
          </div>

          {/* Right Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Ask AI Companion Button (Hero Pill) */}
            <button
              onClick={() => {
                if (isPlaying) togglePlay();
                setIsAIDrawerOpen(true);
              }}
              title="Open Rewind AI Story Companion (Q)"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '8px',
                background: isAIDrawerOpen ? '#ffffff' : 'rgba(255, 255, 255, 0.1)',
                color: isAIDrawerOpen ? '#000000' : '#ffffff',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                fontWeight: 600,
                fontSize: '13px',
                animation: !isPlaying && !isAIDrawerOpen ? 'pulseGlow 2.5s infinite' : 'none',
              }}
              onMouseEnter={(e) => {
                if (!isAIDrawerOpen) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.4)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isAIDrawerOpen) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                }
              }}
            >
              <Sparkles size={16} />
              <span>Ask AI Companion</span>
            </button>

            {/* Subtitles Toggle */}
            <button
              onClick={() => setSubtitlesEnabled((prev) => !prev)}
              title={subtitlesEnabled ? 'Subtitles: English SDH' : 'Subtitles: Off'}
              style={{
                width: '38px',
                height: '38px',
                color: subtitlesEnabled ? '#ffffff' : '#666666',
              }}
            >
              <Subtitles size={20} />
            </button>

            {/* Playback Speed selector */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setSpeedMenuOpen((prev) => !prev)}
                title="Playback Speed"
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                  color: playbackRate !== 1 ? '#ffffff' : '#aaaaaa',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  background: speedMenuOpen ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                }}
              >
                {playbackRate}x
              </button>

              {speedMenuOpen && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '48px',
                    right: 0,
                    background: '#111111',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    padding: '6px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    zIndex: 30,
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.8)',
                  }}
                >
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map((r) => (
                    <button
                      key={r}
                      onClick={() => handleSpeedSelect(r)}
                      style={{
                        padding: '6px 16px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontFamily: 'var(--font-mono)',
                        textAlign: 'left',
                        background: playbackRate === r ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                        color: playbackRate === r ? '#ffffff' : '#888888',
                      }}
                    >
                      {r === 1 ? '1x (Normal)' : `${r}x`}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              title={isFullscreen ? 'Exit Fullscreen (F)' : 'Fullscreen (F)'}
              style={{
                width: '38px',
                height: '38px',
                color: '#cccccc',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#cccccc')}
            >
              {isFullscreen ? <Minimize size={22} /> : <Maximize size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* AI COMPANION SLIDE-OVER DRAWER */}
      <AICompanionDrawer
        isOpen={isAIDrawerOpen}
        onClose={() => setIsAIDrawerOpen(false)}
        currentTime={currentTime}
        sessionId={sessionId}
        onAskQuestion={onAskQuestion}
        onSeekTo={handleSeek}
        speech={speech}
      />

      {/* SHORTCUTS MODAL */}
      {shortcutsModalOpen && (
        <div
          onClick={() => setShortcutsModalOpen(false)}
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '420px',
              maxWidth: '90vw',
              background: '#0e0e0e',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 20px 48px rgba(0, 0, 0, 0.9)',
            }}
          >
            <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#ffffff', marginBottom: '16px' }}>
              Keyboard Controls
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Play / Pause</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>Space / K</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Rewind 10s</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>J / ←</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Forward 10s</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>L / →</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Volume</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>↑ / ↓</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Mute</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>M</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa' }}>
                <span>Fullscreen</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>F</kbd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#aaaaaa', gridColumn: 'span 2' }}>
                <span>Ask AI Story Companion</span>
                <kbd style={{ background: '#222', padding: '2px 6px', borderRadius: '4px', color: '#fff' }}>Q</kbd>
              </div>
            </div>
            <button
              onClick={() => setShortcutsModalOpen(false)}
              style={{
                width: '100%',
                marginTop: '20px',
                padding: '10px',
                borderRadius: '6px',
                background: '#ffffff',
                color: '#000000',
                fontWeight: 600,
                fontSize: '13px',
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
