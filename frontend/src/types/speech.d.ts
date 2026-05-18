// Web Speech API — `SpeechRecognition` is not part of TypeScript's built-in
// DOM lib (it is a non-standard, Chrome/Edge-only API). `SpeechRecognitionEvent`
// and its result types ARE in the lib, so we only declare the recognition
// interface, its constructor, and the Window hooks used by useVoiceInput.

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: Event) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare const SpeechRecognition: {
  prototype: SpeechRecognition;
  new (): SpeechRecognition;
};

interface Window {
  SpeechRecognition?: typeof SpeechRecognition;
  webkitSpeechRecognition?: typeof SpeechRecognition;
}
