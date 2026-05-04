import request from './client';
import type { UserProfile, UserResumeResponse } from '../types';

export const getUser = (): Promise<UserProfile> =>
  request('/user');

export const uploadResume = (file: File): Promise<UserResumeResponse> => {
  const form = new FormData();
  form.append('resume', file);
  return request('/user/resume', {
    method: 'POST',
    headers: {},
    body: form,
  });
};
