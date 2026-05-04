import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSessions, createSession } from '../api/sessions';

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: listSessions });

export const useCreateSession = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => createSession(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
};
