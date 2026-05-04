import request from './client';
import type { Session, SessionListResponse } from '../types';

export const listSessions = (): Promise<SessionListResponse> =>
  request('/sessions');

export const getSession = (sessionId: string): Promise<Session> =>
  request(`/sessions/${sessionId}`);

export const createSession = (jobId: string): Promise<Session> =>
  request('/sessions', { method: 'POST', body: JSON.stringify({ job_id: jobId }) });
