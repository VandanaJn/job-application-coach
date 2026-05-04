import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUser, uploadResume } from '../api/user';

export const useUser = () =>
  useQuery({ queryKey: ['user'], queryFn: getUser });

export const useUploadResume = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: uploadResume,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user'] }),
  });
};
