import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listJobs, getJob, createJob } from '../api/jobs';
import type { JobCreate } from '../types';

export const useJobs = () =>
  useQuery({ queryKey: ['jobs'], queryFn: listJobs });

export const useJob = (jobId: string) =>
  useQuery({ queryKey: ['jobs', jobId], queryFn: () => getJob(jobId) });

export const useCreateJob = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: JobCreate) => createJob(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  });
};
