import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SessionDetail from './SessionDetail';

const mockUseSessionStatus = vi.fn();
const mockUseRunSession = vi.fn(() => ({ mutate: vi.fn(), isPending: false }));

vi.mock('../hooks/useSessions', () => ({
  useSessionStatus: (id: string) => mockUseSessionStatus(id),
  useRunSession: () => mockUseRunSession(),
}));

const SESSION_ID = 'sess-123';
const QUESTIONS = [{ question: 'Tell me about yourself', category: 'behavioral' }];

function makeStatus(overrides = {}) {
  return {
    session_id: SESSION_ID,
    status: 'completed',
    questions: QUESTIONS,
    ...overrides,
  };
}

function renderDetail() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/sessions/${SESSION_ID}`]}>
        <Routes>
          <Route path="/sessions/:sessionId" element={<SessionDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseSessionStatus.mockReturnValue({ data: makeStatus(), isLoading: false });
  mockUseRunSession.mockReturnValue({ mutate: vi.fn(), isPending: false });
});

describe('SessionDetail token usage badge', () => {
  it('shows formatted token total when usage is present', () => {
    mockUseSessionStatus.mockReturnValue({
      data: makeStatus({
        usage: { input_tokens: 1234, output_tokens: 567, total_tokens: 1801 },
      }),
      isLoading: false,
    });
    renderDetail();
    expect(screen.getByText(/1,801 tokens/)).toBeInTheDocument();
  });

  it('omits the token badge when usage is absent', () => {
    renderDetail();
    expect(screen.queryByText(/tokens/)).not.toBeInTheDocument();
  });

  it('exposes input/output breakdown via title attribute', () => {
    mockUseSessionStatus.mockReturnValue({
      data: makeStatus({
        usage: { input_tokens: 100, output_tokens: 50, total_tokens: 150 },
      }),
      isLoading: false,
    });
    renderDetail();
    const badge = screen.getByText(/150 tokens/);
    expect(badge).toHaveAttribute('title', expect.stringContaining('Input: 100'));
    expect(badge).toHaveAttribute('title', expect.stringContaining('Output: 50'));
  });
});
