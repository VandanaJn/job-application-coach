import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSessionStatus } from '../hooks/useSessions';
import { useCoachAnswer } from '../hooks/useSessions';
import type { QuestionItem } from '../types';

interface Message {
  role: 'user' | 'coach';
  text: string;
}

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

function QuestionHeader({
  index,
  total,
  item,
  onPrev,
  onNext,
}: {
  index: number;
  total: number;
  item: QuestionItem;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 text-sm font-semibold flex items-center justify-center">
            {index + 1}
          </span>
          <span className="text-xs text-gray-400">of {total}</span>
          <CategoryBadge category={item.category} />
        </div>
        <div className="flex gap-1">
          <button
            onClick={onPrev}
            disabled={index === 0}
            className="px-3 py-1 text-sm rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Prev
          </button>
          <button
            onClick={onNext}
            disabled={index === total - 1}
            className="px-3 py-1 text-sm rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      </div>
      <p className="text-gray-900 leading-relaxed font-medium">{item.question}</p>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
        }`}
      >
        {!isUser && (
          <p className="text-xs font-semibold text-indigo-500 mb-1">Coach</p>
        )}
        <p className="whitespace-pre-wrap">{message.text}</p>
      </div>
    </div>
  );
}

function EmptyConversation() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
      <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center mb-3">
        <span className="text-2xl">💬</span>
      </div>
      <p className="text-gray-500 text-sm">Type your answer below to start coaching</p>
    </div>
  );
}

function QuestionComplete({ onNext, isLast }: { onNext: () => void; isLast: boolean }) {
  return (
    <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-green-600 text-lg">✓</span>
        <p className="text-sm text-green-800 font-medium">Strong answer — well done!</p>
      </div>
      {!isLast && (
        <button
          onClick={onNext}
          className="text-sm px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          Next question →
        </button>
      )}
    </div>
  );
}

export default function AnswerCoach() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: status, isLoading } = useSessionStatus(sessionId!);
  const { mutate: sendAnswer, isPending } = useCoachAnswer(sessionId!);

  const [questionIndex, setQuestionIndex] = useState(0);
  const [conversations, setConversations] = useState<Record<number, Message[]>>({});
  const [runtimeSessionIds, setRuntimeSessionIds] = useState<Record<number, string>>({});
  const [completedQuestions, setCompletedQuestions] = useState<Set<number>>(new Set());
  const [inputText, setInputText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const questions = status?.questions ?? [];
  const currentConversation = conversations[questionIndex] ?? [];
  const isComplete = completedQuestions.has(questionIndex);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation]);

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || isPending || isComplete) return;

    const userMessage: Message = { role: 'user', text };
    setConversations(prev => ({
      ...prev,
      [questionIndex]: [...(prev[questionIndex] ?? []), userMessage],
    }));
    setInputText('');

    sendAnswer(
      {
        question_index: questionIndex,
        user_message: text,
        runtime_session_id: runtimeSessionIds[questionIndex],
      },
      {
        onSuccess: (data) => {
          if (!runtimeSessionIds[questionIndex]) {
            setRuntimeSessionIds(prev => ({ ...prev, [questionIndex]: data.runtime_session_id }));
          }
          setConversations(prev => ({
            ...prev,
            [questionIndex]: [
              ...(prev[questionIndex] ?? []),
              { role: 'coach', text: data.coaching_response },
            ],
          }));
          if (data.is_complete) {
            setCompletedQuestions(prev => new Set(prev).add(questionIndex));
          }
        },
        onError: (err) => {
          setConversations(prev => ({
            ...prev,
            [questionIndex]: [
              ...(prev[questionIndex] ?? []),
              { role: 'coach', text: `Something went wrong: ${err.message}` },
            ],
          }));
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No questions found for this session.</p>
          <button
            onClick={() => navigate(`/sessions/${sessionId}`)}
            className="text-indigo-600 hover:underline text-sm"
          >
            ← Back to session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="max-w-2xl mx-auto w-full px-6 py-8 flex flex-col flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate(`/sessions/${sessionId}`)}
            className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1"
          >
            ← Questions
          </button>
          <h1 className="text-lg font-bold text-gray-900">Answer Coach</h1>
          <div className="w-20" />
        </div>

        {/* Question */}
        <QuestionHeader
          index={questionIndex}
          total={questions.length}
          item={questions[questionIndex]}
          onPrev={() => setQuestionIndex(i => i - 1)}
          onNext={() => setQuestionIndex(i => i + 1)}
        />

        {/* Conversation */}
        <div className="flex-1 flex flex-col mt-4 min-h-0">
          <div className="flex-1 overflow-y-auto space-y-3 pb-4">
            {currentConversation.length === 0 ? (
              <EmptyConversation />
            ) : (
              currentConversation.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))
            )}
            {isPending && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3">
                  <p className="text-xs font-semibold text-indigo-500 mb-1">Coach</p>
                  <div className="flex gap-1 items-center h-4">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Complete banner */}
          {isComplete && (
            <div className="mb-3">
              <QuestionComplete
                onNext={() => setQuestionIndex(i => i + 1)}
                isLast={questionIndex === questions.length - 1}
              />
            </div>
          )}

          {/* Input */}
          {!isComplete && (
            <div className="bg-white border border-gray-200 rounded-xl p-3 flex gap-3 items-end">
              <textarea
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your answer… (Enter to send, Shift+Enter for new line)"
                rows={3}
                className="flex-1 resize-none text-sm text-gray-900 placeholder-gray-400 outline-none leading-relaxed"
              />
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || isPending}
                className="shrink-0 w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="w-4 h-4 rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
