import { useParams, useNavigate, Link } from 'react-router-dom';
import { useJob } from '../hooks/useJobs';
import { useSessions, useCreateSession } from '../hooks/useSessions';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
};

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading: jobLoading } = useJob(jobId!);
  const { data: sessionList, isLoading: sessionsLoading } = useSessions();
  const { mutate: createSession, isPending } = useCreateSession();

  const sessions = sessionList?.sessions.filter((s) => s.job_id === jobId) ?? [];

  const handleStartPractice = () => {
    createSession(jobId!, {
      onSuccess: (session) => navigate(`/sessions/${session.session_id}`),
    });
  };

  if (jobLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Job not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button onClick={() => navigate('/jobs')} className="text-sm text-gray-400 hover:text-gray-600 mb-6 flex items-center gap-1">
          ← Back to jobs
        </button>

        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h1 className="text-2xl font-bold text-gray-900">{job.job_title || 'Untitled role'}</h1>
          <p className="text-gray-500 mt-1">{job.company || 'Unknown company'}</p>
          <details className="mt-4">
            <summary className="text-sm text-indigo-600 cursor-pointer hover:underline">View job description</summary>
            <p className="mt-3 text-sm text-gray-600 whitespace-pre-line leading-relaxed">{job.job_description}</p>
          </details>
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Practice sessions</h2>
          <button
            onClick={handleStartPractice}
            disabled={isPending}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Starting…' : '+ Start practice'}
          </button>
        </div>

        {sessionsLoading && (
          <div className="flex justify-center py-10">
            <div className="w-6 h-6 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {!sessionsLoading && sessions.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p>No practice sessions yet.</p>
            <p className="text-sm mt-1">Start a session to practise your interview.</p>
          </div>
        )}

        <div className="space-y-3">
          {sessions.map((session) => (
            <Link
              key={session.session_id}
              to={`/sessions/${session.session_id}`}
              className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600 font-mono">{session.session_id.slice(0, 8)}…</p>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[session.status] ?? 'bg-gray-100 text-gray-600'}`}>
                  {session.status}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">{new Date(session.created_at).toLocaleString()}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
