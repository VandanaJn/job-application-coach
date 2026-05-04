import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../hooks/useUser';

export default function Home() {
  const { data, isLoading } = useUser();
  const navigate = useNavigate();

  useEffect(() => {
    if (!data) return;
    navigate(data.has_resume ? '/jobs' : '/resume', { replace: true });
  }, [data, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return null;
}
