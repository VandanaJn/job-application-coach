import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSessions, createSession, runSession, getSessionStatus, coachAnswer } from '../api/sessions';
import type { CoachRequest } from '../types';

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: listSessions });

export const useCreateSession = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => createSession(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
};

export const useRunSession = () =>
  useMutation({ mutationFn: (sessionId: string) => runSession(sessionId) });

export const useSessionStatus = (sessionId: string) =>
  useQuery({
    queryKey: ['sessions', sessionId, 'status'],
    queryFn: () => getSessionStatus(sessionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'pending' ? 2000 : false;
    },
  });

export const useCoachAnswer = (sessionId: string) =>
  useMutation({
    mutationFn: (body: CoachRequest) => coachAnswer(sessionId, body),
  });
