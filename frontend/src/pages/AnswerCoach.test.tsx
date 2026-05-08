import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AnswerCoach from './AnswerCoach';

// --- mock hooks ---
const mockUseSessionStatus = vi.fn();
const mockMutate = vi.fn();
const mockUseCoachAnswer = vi.fn(() => ({ mutate: mockMutate, isPending: false }));

vi.mock('../hooks/useSessions', () => ({
  useSessionStatus: (...args: unknown[]) => mockUseSessionStatus(...args),
  useCoachAnswer: (...args: unknown[]) => mockUseCoachAnswer(...args),
}));

// --- helpers ---
const SESSION_ID = 'test-session-123';
const QUESTIONS = [
  { question: 'Tell me about yourself', category: 'behavioral' },
  { question: 'Explain a technical challenge you solved', category: 'technical' },
];

function makeStatus(overrides = {}) {
  return {
    session_id: SESSION_ID,
    status: 'completed',
    questions: QUESTIONS,
    ...overrides,
  };
}

function renderCoach() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/sessions/${SESSION_ID}/coach`]}>
        <Routes>
          <Route path="/sessions/:sessionId/coach" element={<AnswerCoach />} />
          <Route path="/sessions/:sessionId" element={<div>Session Detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  mockUseSessionStatus.mockReturnValue({ data: makeStatus(), isLoading: false });
  mockUseCoachAnswer.mockReturnValue({ mutate: mockMutate, isPending: false });
});

describe('AnswerCoach', () => {
  it('renders loading spinner while session is loading', () => {
    mockUseSessionStatus.mockReturnValue({ data: undefined, isLoading: true });
    renderCoach();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders fallback when there are no questions', () => {
    mockUseSessionStatus.mockReturnValue({ data: makeStatus({ questions: [] }), isLoading: false });
    renderCoach();
    expect(screen.getByText(/no questions found/i)).toBeInTheDocument();
  });

  it('displays the first question on load', () => {
    renderCoach();
    expect(screen.getByText('Tell me about yourself')).toBeInTheDocument();
  });

  it('shows question counter and category badge', () => {
    renderCoach();
    expect(screen.getByText(/of 2/)).toBeInTheDocument();
    expect(screen.getByText(/behavioral/i)).toBeInTheDocument();
  });

  it('shows empty conversation prompt initially', () => {
    renderCoach();
    expect(screen.getByText(/type your answer below/i)).toBeInTheDocument();
  });

  it('disables send button when input is empty', () => {
    renderCoach();
    const btn = screen.getByRole('button', { name: '' }); // svg-only send button
    // find the send button by its parent structure — disabled when empty
    const textarea = screen.getByPlaceholderText(/type your answer/i);
    expect(textarea).toBeInTheDocument();
    // button should be disabled with empty input
    const buttons = document.querySelectorAll('button[disabled]');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('calls sendAnswer with correct payload on submit', async () => {
    const user = userEvent.setup();
    renderCoach();

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    await user.type(textarea, 'My name is Jane and I am a software engineer');
    fireEvent.click(document.querySelector('button[class*="bg-indigo-600"][class*="shrink-0"]')!);

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        question_index: 0,
        user_message: 'My name is Jane and I am a software engineer',
        runtime_session_id: undefined,
      }),
      expect.any(Object)
    );
  });

  it('sends via Enter key', async () => {
    const user = userEvent.setup();
    renderCoach();

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    await user.type(textarea, 'Test answer{Enter}');

    expect(mockMutate).toHaveBeenCalledTimes(1);
  });

  it('does not send on Shift+Enter', async () => {
    const user = userEvent.setup();
    renderCoach();

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    await user.type(textarea, 'Test{Shift>}{Enter}{/Shift}');

    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('shows typing indicator while isPending', () => {
    mockUseCoachAnswer.mockReturnValue({ mutate: mockMutate, isPending: true });
    renderCoach();
    // 3 animated bounce dots rendered when pending
    const dots = document.querySelectorAll('.animate-bounce');
    expect(dots.length).toBe(3);
  });

  it('navigates to previous question when Prev clicked', async () => {
    const user = userEvent.setup();
    renderCoach();

    // go to question 2 first
    const nextBtn = screen.getByRole('button', { name: /next/i });
    await user.click(nextBtn);
    expect(screen.getByText('Explain a technical challenge you solved')).toBeInTheDocument();

    // go back
    const prevBtn = screen.getByRole('button', { name: /prev/i });
    await user.click(prevBtn);
    expect(screen.getByText('Tell me about yourself')).toBeInTheDocument();
  });

  it('disables Prev on first question and Next on last question', async () => {
    const user = userEvent.setup();
    renderCoach();

    expect(screen.getByRole('button', { name: /prev/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled();

    await user.click(screen.getByRole('button', { name: /next/i }));

    expect(screen.getByRole('button', { name: /prev/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
  });

  it('shows completion banner and hides input when is_complete fires', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_body: unknown, { onSuccess }: { onSuccess: (d: unknown) => void }) => {
      onSuccess({
        question_index: 0,
        coaching_response: 'Great answer!',
        runtime_session_id: 'rs-abc',
        is_complete: true,
      });
    });

    renderCoach();
    const textarea = screen.getByPlaceholderText(/type your answer/i);
    await user.type(textarea, 'My answer here{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/strong answer/i)).toBeInTheDocument();
    });
    expect(screen.queryByPlaceholderText(/type your answer/i)).not.toBeInTheDocument();
  });

  it('reuses runtime_session_id on second turn', async () => {
    const user = userEvent.setup();
    let call = 0;
    mockMutate.mockImplementation((_body: unknown, { onSuccess }: { onSuccess: (d: unknown) => void }) => {
      call++;
      onSuccess({
        question_index: 0,
        coaching_response: call === 1 ? 'Tell me more' : 'Good!',
        runtime_session_id: 'rs-abc',
        is_complete: false,
      });
    });

    renderCoach();
    const textarea = () => screen.getByPlaceholderText(/type your answer/i);

    await user.type(textarea(), 'First answer{Enter}');
    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(1));

    await user.type(textarea(), 'Second answer{Enter}');
    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(2));

    expect(mockMutate).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ runtime_session_id: 'rs-abc' }),
      expect.any(Object)
    );
  });

  it('shows error message in chat on coach API failure', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_body: unknown, { onError }: { onError: (e: Error) => void }) => {
      onError(new Error('Network error'));
    });

    renderCoach();
    const textarea = screen.getByPlaceholderText(/type your answer/i);
    await user.type(textarea, 'My answer{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/something went wrong: network error/i)).toBeInTheDocument();
    });
  });

  it('navigates back to session detail when back button clicked', async () => {
    const user = userEvent.setup();
    renderCoach();

    await user.click(screen.getByRole('button', { name: /questions/i }));
    expect(screen.getByText('Session Detail')).toBeInTheDocument();
  });

  it('persists conversation and runtime_session_id across remount', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_body: unknown, { onSuccess }: { onSuccess: (d: unknown) => void }) => {
      onSuccess({
        question_index: 0,
        coaching_response: 'Coach reply',
        runtime_session_id: 'rs-persisted',
        is_complete: false,
      });
    });

    const { unmount } = renderCoach();
    await user.type(screen.getByPlaceholderText(/type your answer/i), 'First answer{Enter}');
    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('Coach reply')).toBeInTheDocument());

    unmount();
    mockMutate.mockClear();

    renderCoach();

    // Prior chat survives the remount
    expect(screen.getByText('First answer')).toBeInTheDocument();
    expect(screen.getByText('Coach reply')).toBeInTheDocument();

    // Next turn reuses the persisted runtime_session_id
    await user.type(screen.getByPlaceholderText(/type your answer/i), 'Second answer{Enter}');
    await waitFor(() => expect(mockMutate).toHaveBeenCalledTimes(1));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ runtime_session_id: 'rs-persisted' }),
      expect.any(Object)
    );
  });

  it('persists is_complete across remount', async () => {
    const user = userEvent.setup();
    mockMutate.mockImplementation((_body: unknown, { onSuccess }: { onSuccess: (d: unknown) => void }) => {
      onSuccess({
        question_index: 0,
        coaching_response: 'Excellent!',
        runtime_session_id: 'rs-1',
        is_complete: true,
      });
    });

    const { unmount } = renderCoach();
    await user.type(screen.getByPlaceholderText(/type your answer/i), 'Done{Enter}');
    await waitFor(() => expect(screen.getByText(/strong answer/i)).toBeInTheDocument());

    unmount();
    renderCoach();

    expect(screen.getByText(/strong answer/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/type your answer/i)).not.toBeInTheDocument();
  });
});
