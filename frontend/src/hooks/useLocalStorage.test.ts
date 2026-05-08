import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from './useLocalStorage';

beforeEach(() => {
  localStorage.clear();
});

describe('useLocalStorage', () => {
  it('returns initialValue when nothing is stored', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('returns stored value when present', () => {
    localStorage.setItem('k', JSON.stringify('stored'));
    const { result } = renderHook(() => useLocalStorage('k', 'default'));
    expect(result.current[0]).toBe('stored');
  });

  it('writes to localStorage when value changes', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'default'));
    act(() => {
      result.current[1]('updated');
    });
    expect(localStorage.getItem('k')).toBe(JSON.stringify('updated'));
    expect(result.current[0]).toBe('updated');
  });

  it('supports functional updates', () => {
    const { result } = renderHook(() => useLocalStorage('k', 0));
    act(() => {
      result.current[1]((prev) => prev + 1);
    });
    expect(result.current[0]).toBe(1);
    expect(localStorage.getItem('k')).toBe('1');
  });

  it('round-trips complex objects', () => {
    const initial = { a: 1, b: { c: 'x' } };
    const { result } = renderHook(() => useLocalStorage('k', initial));
    act(() => {
      result.current[1]({ a: 2, b: { c: 'y' } });
    });
    expect(JSON.parse(localStorage.getItem('k')!)).toEqual({ a: 2, b: { c: 'y' } });
  });

  it('returns initialValue when stored JSON is malformed', () => {
    localStorage.setItem('k', '{not valid json');
    const { result } = renderHook(() => useLocalStorage('k', 'fallback'));
    expect(result.current[0]).toBe('fallback');
  });

  it('survives a remount via fresh hook instance', () => {
    const { result, unmount } = renderHook(() => useLocalStorage('k', 'default'));
    act(() => {
      result.current[1]('persisted');
    });
    unmount();

    const { result: r2 } = renderHook(() => useLocalStorage('k', 'default'));
    expect(r2.current[0]).toBe('persisted');
  });
});
