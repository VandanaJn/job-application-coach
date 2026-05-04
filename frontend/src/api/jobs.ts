import request from './client';
import type { Job, JobCreate, JobListResponse } from '../types';

export const listJobs = (): Promise<JobListResponse> =>
  request('/jobs');

export const getJob = (jobId: string): Promise<Job> =>
  request(`/jobs/${jobId}`);

export const createJob = (body: JobCreate): Promise<Job> =>
  request('/jobs', { method: 'POST', body: JSON.stringify(body) });
