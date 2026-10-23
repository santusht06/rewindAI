import { useState, useEffect, useCallback, useRef } from 'react';

export function useSpeech() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      stop();
    };
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, []);

  const speak = useCallback(
    (text, audioBase64 = null, mimeType = 'audio/mpeg') => {
      stop();
      if (isMuted || !text) return;

      // 1. If audioBase64 was provided by the server, use HTML5 Audio
      if (audioBase64) {
        try {
          const audio = new Audio(`data:${mimeType};base64,${audioBase64}`);
          audioRef.current = audio;
          setIsSpeaking(true);
          audio.onended = () => {
            setIsSpeaking(false);
            audioRef.current = null;
          };
          audio.onerror = () => {
            setIsSpeaking(false);
            audioRef.current = null;
            // Fall back to browser speech synthesis
            speakWithBrowser(text);
          };
          audio.play().catch(() => speakWithBrowser(text));
          return;
        } catch {
          // Fall back to browser TTS
        }
      }

      // 2. Browser SpeechSynthesis fallback
      speakWithBrowser(text);
    },
    [isMuted, stop]
  );

  const speakWithBrowser = (text) => {
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.lang = 'en-US';

      const voices = window.speechSynthesis.getVoices();
      const naturalVoice = voices.find(
        (v) =>
          v.lang.startsWith('en') &&
          (v.name.includes('Natural') ||
            v.name.includes('Siri') ||
            v.name.includes('Samantha') ||
            v.name.includes('Google') ||
            v.name.includes('Daniel'))
      );
      if (naturalVoice) utterance.voice = naturalVoice;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } catch {
      setIsSpeaking(false);
    }
  };

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      if (next) stop();
      return next;
    });
  }, [stop]);

  return {
    isSpeaking,
    isMuted,
    speak,
    stop,
    toggleMute,
  };
}
