import { useState, useEffect } from 'react';

// Drop-in replacement for useState that persists to localStorage.
// Assumes a stable `key` for the component lifetime — if the key changes,
// the stored value for the new key is NOT re-read into state.
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item !== null ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // localStorage unavailable or full — fail silently so the UI still works
    }
  }, [key, value]);

  return [value, setValue] as const;
}
