import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getSession } from '../api/sessions';

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading } = useQuery({
    queryKey: ['sessions', sessionId],
    queryFn: () => getSession(sessionId!),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button
          onClick={() => navigate(`/jobs/${session?.job_id}`)}
          className="text-sm text-gray-400 hover:text-gray-600 mb-6 flex items-center gap-1"
        >
          ← Back to job
        </button>

        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🎯</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Interview practice</h1>
          <p className="text-gray-500 mb-6">
            Agent pipeline coming soon — questions, answer coaching, and feedback will appear here.
          </p>
          <div className="inline-block bg-yellow-50 border border-yellow-200 text-yellow-700 text-sm px-4 py-2 rounded-lg">
            Status: {session?.status ?? '…'}
          </div>
        </div>
      </div>
    </div>
  );
}
