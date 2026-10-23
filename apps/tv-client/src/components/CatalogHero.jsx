import React from 'react';
import { Play, Sparkles, Info, Shield, Database, Film, Volume2, CheckCircle2 } from 'lucide-react';

export function CatalogHero({ movie, onPlayMovie, onOpenAI }) {
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        background: '#000000',
        color: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Top Navbar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 56px',
          background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0) 100%)',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
          {/* Brand Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: '#ffffff',
                color: '#000000',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 900,
                fontSize: '16px',
              }}
            >
              ◂◂
            </div>
            <span style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              REWIND
            </span>
          </div>

          {/* Navigation Links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '28px', fontSize: '14px', fontWeight: 500 }}>
            <span style={{ color: '#ffffff', cursor: 'pointer' }}>Home</span>
            <span style={{ color: '#777777', cursor: 'pointer' }}>Movies</span>
            <span style={{ color: '#777777', cursor: 'pointer' }}>AI Companion</span>
            <span style={{ color: '#777777', cursor: 'pointer' }}>Settings</span>
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Indexing Status Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              fontSize: '12px',
              color: '#cccccc',
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
            <span>197 Dialogue Chunks Indexed</span>
          </div>

          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              background: '#222222',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            TV
          </div>
        </div>
      </header>

      {/* Main Hero Billboard */}
      <div
        style={{
          position: 'relative',
          flex: 1,
          padding: '60px 56px 40px 56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          maxWidth: '920px',
          zIndex: 5,
        }}
      >
        {/* Ambient Dark Backdrop Artwork */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: 'radial-gradient(circle at 75% 30%, rgba(35, 35, 35, 0.35) 0%, rgba(0, 0, 0, 0.95) 65%)',
            pointerEvents: 'none',
            zIndex: -1,
          }}
        />

        {/* Feature Tag */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: '#888888',
              padding: '4px 8px',
              background: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '4px',
            }}
          >
            FEATURED FILM • AI COMPANION READY
          </span>
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: '72px',
            fontWeight: 800,
            letterSpacing: '-0.03em',
            lineHeight: 1.05,
            color: '#ffffff',
            marginBottom: '16px',
          }}
        >
          {movie?.display_title || 'Interstellar'}
        </h1>

        {/* Metadata Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#e0e0e0' }}>2014</span>
          <span style={{ fontSize: '12px', padding: '1px 6px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: '3px', color: '#ccc' }}>PG-13</span>
          <span style={{ fontSize: '13px', color: '#aaaaaa' }}>2h 49m</span>
          <span style={{ fontSize: '12px', padding: '1px 6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', color: '#eee' }}>4K ULTRA HD</span>
          <span style={{ fontSize: '12px', padding: '1px 6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', color: '#eee' }}>5.1 SURROUND</span>
          <span style={{ fontSize: '13px', color: '#888888' }}>Sci-Fi • Adventure • Drama</span>
        </div>

        {/* Logline */}
        <p
          style={{
            fontSize: '17px',
            lineHeight: 1.6,
            color: '#b3b3b3',
            maxWidth: '720px',
            marginBottom: '32px',
          }}
        >
          When Earth faces ecological extinction, former NASA test pilot Joseph Cooper is recruited for a secret interstellar voyage through a newly detected gravitational wormhole near Saturn to find humanity a new home.
        </p>

        {/* Hero Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={onPlayMovie}
            style={{
              padding: '16px 36px',
              borderRadius: '8px',
              background: '#ffffff',
              color: '#000000',
              fontWeight: 700,
              fontSize: '16px',
              letterSpacing: '-0.01em',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 4px 20px rgba(255, 255, 255, 0.25)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#e6e6e6')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#ffffff')}
          >
            <Play size={22} fill="#000000" />
            <span>Play Movie</span>
          </button>

          <button
            onClick={onOpenAI}
            style={{
              padding: '16px 28px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              fontWeight: 600,
              fontSize: '15px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backdropFilter: 'blur(12px)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.18)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.35)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            }}
          >
            <Sparkles size={18} />
            <span>How Story AI Works</span>
          </button>
        </div>
      </div>

      {/* Feature Bento Grid (Pure Minimalist Black & White) */}
      <div
        style={{
          padding: '24px 56px 56px 56px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          zIndex: 5,
        }}
      >
        <div
          style={{
            background: '#0d0d0d',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff' }}>
            <Shield size={18} />
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Zero-Spoiler Guarantee</h3>
          </div>
          <p style={{ fontSize: '12px', color: '#777777', lineHeight: 1.5 }}>
            Whenever you pause, the AI's temporal search boundary is locked strictly to that second. Future plot twists remain safe.
          </p>
        </div>

        <div
          style={{
            background: '#0d0d0d',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff' }}>
            <Database size={18} />
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>3072-Dim Embeddings</h3>
          </div>
          <p style={{ fontSize: '12px', color: '#777777', lineHeight: 1.5 }}>
            All 197 dialogue scenes are vector-indexed with Gemini. Instant cosine similarity matches what characters are discussing.
          </p>
        </div>

        <div
          style={{
            background: '#0d0d0d',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff' }}>
            <Film size={18} />
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Clickable Scene Citations</h3>
          </div>
          <p style={{ fontSize: '12px', color: '#777777', lineHeight: 1.5 }}>
            Answers link to verified dialogue excerpts with exact timestamps. Click any citation to jump straight to that moment.
          </p>
        </div>

        <div
          style={{
            background: '#0d0d0d',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff' }}>
            <Volume2 size={18} />
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Speech Synthesis Audio</h3>
          </div>
          <p style={{ fontSize: '12px', color: '#777777', lineHeight: 1.5 }}>
            Answers are spoken aloud on your TV or browser with natural speech, so you never have to squint at small text.
          </p>
        </div>
      </div>
    </div>
  );
}
