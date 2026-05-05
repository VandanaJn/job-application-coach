import { useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useSessionStatus, useRunSession } from '../hooks/useSessions';
import type { QuestionItem } from '../types';

const CATEGORY_STYLES: Record<string, string> = {
  behavioral:  'bg-blue-50 text-blue-700',
  technical:   'bg-purple-50 text-purple-700',
  situational: 'bg-orange-50 text-orange-700',
};

function CategoryBadge({ category }: { category: string }) {
  const style = CATEGORY_STYLES[category.toLowerCase()] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${style}`}>
      {category}
    </span>
  );
}

function QuestionCard({ index, item }: { index: number; item: QuestionItem }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start gap-4">
        <span className="shrink-0 w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 text-sm font-semibold flex items-center justify-center">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-gray-900 leading-relaxed">{item.question}</p>
          <div className="mt-2">
            <CategoryBadge category={item.category} />
          </div>
        </div>
      </div>
    </div>
  );
}

function GeneratingState() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
      <p className="text-lg font-semibold text-gray-900">Generating your interview questions</p>
      <p className="text-gray-400 text-sm mt-2">Analysing your resume against the job description…</p>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
      <p className="text-red-600 font-semibold mb-2">Something went wrong</p>
      <p className="text-gray-500 text-sm mb-6">{message}</p>
      <button
        onClick={onRetry}
        className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: status, isLoading } = useSessionStatus(sessionId!);
  const { mutate: runSession, isPending: isRunning } = useRunSession();
  const hasTriggeredRun = useRef(false);

  useEffect(() => {
    if (status?.status === 'pending' && !hasTriggeredRun.current) {
      hasTriggeredRun.current = true;
      runSession(sessionId!);
    }
  }, [status?.status, sessionId, runSession]);

  const handleRetry = () => {
    hasTriggeredRun.current = true;
    runSession(sessionId!, {
      onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions', sessionId, 'status'] }),
    });
  };

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
          onClick={() => navigate(-1)}
          className="text-sm text-gray-400 hover:text-gray-600 mb-6 flex items-center gap-1"
        >
          ← Back
        </button>

        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Interview questions</h1>
          {status?.status === 'completed' && (
            <span className="text-xs px-3 py-1 rounded-full bg-green-100 text-green-700 font-medium">
              {status.questions?.length ?? 0} questions
            </span>
          )}
        </div>

        {(status?.status === 'pending' || status?.status === 'running' || isRunning) && (
          <GeneratingState />
        )}

        {status?.status === 'error' && !isRunning && (
          <ErrorState
            message={status.error ?? 'An unknown error occurred.'}
            onRetry={handleRetry}
          />
        )}

        {status?.status === 'completed' && status.questions && (
          <div className="space-y-3">
            {status.questions.map((q, i) => (
              <QuestionCard key={i} index={i} item={q} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
