import request from './client';
import type { Session, SessionListResponse, SessionStatus, CoachRequest, CoachResponse } from '../types';

export const listSessions = (): Promise<SessionListResponse> =>
  request('/sessions');

export const getSession = (sessionId: string): Promise<Session> =>
  request(`/sessions/${sessionId}`);

export const createSession = (jobId: string): Promise<Session> =>
  request('/sessions', { method: 'POST', body: JSON.stringify({ job_id: jobId }) });

export const runSession = (sessionId: string): Promise<Session> =>
  request(`/sessions/${sessionId}/run`, { method: 'POST' });

export const getSessionStatus = (sessionId: string): Promise<SessionStatus> =>
  request(`/sessions/${sessionId}/status`);

export const coachAnswer = (sessionId: string, body: CoachRequest): Promise<CoachResponse> =>
  request(`/sessions/${sessionId}/coach`, { method: 'POST', body: JSON.stringify(body) });
