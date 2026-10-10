/**
 * NEXORA AI — Browser Speech Recognition & Audio Synthesis Service
 * Provides:
 * - Web Speech API SpeechRecognition (webkitSpeechRecognition fallback)
 * - Web Speech API SpeechSynthesis with clean text filtering, speed, and pause/resume
 * - Safe permissions lifecycle, audio state events, and error handling
 */

export interface SpeechRecognitionHandlers {
  onStart?: () => void;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (errorMessage: string) => void;
  onEnd?: () => void;
}

class SpeechService {
  private recognition: any = null;
  private isListening: boolean = false;
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private audioPlayer: HTMLAudioElement | null = null;

  constructor() {
    this.initRecognition();
  }

  private initRecognition() {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        this.recognition = new SpeechRec();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
      } catch (e) {
        console.warn('SpeechRecognition initialization failed:', e);
      }
    }
  }

  public isSpeechRecognitionSupported(): boolean {
    return Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }

  public isSpeechSynthesisSupported(): boolean {
    return 'speechSynthesis' in window;
  }

  /**
   * Start listening using browser speech recognition
   */
  public startListening(lang: string = 'en-US', handlers: SpeechRecognitionHandlers = {}): boolean {
    if (!this.recognition) {
      handlers.onError?.('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return false;
    }

    if (this.isListening) {
      this.stopListening();
    }

    try {
      this.recognition.lang = lang === 'auto' ? 'en-US' : lang;

      this.recognition.onstart = () => {
        this.isListening = true;
        handlers.onStart?.();
      };

      this.recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        const currentText = finalTranscript || interimTranscript;
        handlers.onResult?.(currentText, Boolean(finalTranscript));
      };

      this.recognition.onerror = (event: any) => {
        let msg = 'Speech recognition error.';
        if (event.error === 'not-allowed') {
          msg = 'Microphone permission was denied. Please allow microphone access in your browser settings.';
        } else if (event.error === 'no-speech') {
          msg = 'No speech detected. Please speak clearly into your microphone.';
        } else if (event.error === 'network') {
          msg = 'Network issue with speech recognition service.';
        }
        this.isListening = false;
        handlers.onError?.(msg);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        handlers.onEnd?.();
      };

      this.recognition.start();
      return true;
    } catch (err: any) {
      this.isListening = false;
      handlers.onError?.(err.message || 'Failed to start microphone.');
      return false;
    }
  }

  /**
   * Stop speech recognition
   */
  public stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch (e) {
        // Ignored
      }
      this.isListening = false;
    }
  }

  /**
   * Speak sanitized text using browser speech synthesis
   */
  public speakText(params: {
    text: string;
    lang?: string;
    speed?: number;
    onStart?: () => void;
    onEnd?: () => void;
    onError?: (err: any) => void;
  }) {
    if (!this.isSpeechSynthesisSupported()) {
      params.onError?.('Speech synthesis is not supported in this browser.');
      return;
    }

    this.stopSpeaking();

    try {
      const utterance = new SpeechSynthesisUtterance(params.text);
      utterance.rate = params.speed || 1.0;
      utterance.pitch = 1.0;
      if (params.lang && params.lang !== 'auto') {
        utterance.lang = params.lang;
      }

      utterance.onstart = () => {
        params.onStart?.();
      };

      utterance.onend = () => {
        this.currentUtterance = null;
        params.onEnd?.();
      };

      utterance.onerror = (err) => {
        this.currentUtterance = null;
        params.onError?.(err);
      };

      this.currentUtterance = utterance;
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      params.onError?.(err);
    }
  }

  /**
   * Play base64 audio (e.g. from OpenAI TTS)
   */
  public playAudioBase64(base64Data: string, onEnd?: () => void): HTMLAudioElement {
    this.stopSpeaking();
    const audio = new Audio(`data:audio/mpeg;base64,${base64Data}`);
    this.audioPlayer = audio;
    if (onEnd) {
      audio.onended = () => {
        this.audioPlayer = null;
        onEnd();
      };
    }
    audio.play().catch((err) => console.warn('Audio playback error:', err));
    return audio;
  }

  /**
   * Stop any ongoing speech or audio playback
   */
  public stopSpeaking() {
    if (this.isSpeechSynthesisSupported()) {
      window.speechSynthesis.cancel();
    }
    if (this.audioPlayer) {
      this.audioPlayer.pause();
      this.audioPlayer.currentTime = 0;
      this.audioPlayer = null;
    }
    this.currentUtterance = null;
  }

  /**
   * Pause speech synthesis
   */
  public pauseSpeaking() {
    if (this.isSpeechSynthesisSupported() && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
    }
    if (this.audioPlayer && !this.audioPlayer.paused) {
      this.audioPlayer.pause();
    }
  }

  /**
   * Resume speech synthesis
   */
  public resumeSpeaking() {
    if (this.isSpeechSynthesisSupported() && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
    if (this.audioPlayer && this.audioPlayer.paused) {
      this.audioPlayer.play();
    }
  }
}

export const speechService = new SpeechService();
