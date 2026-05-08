import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBanner from './ErrorBanner';

describe('ErrorBanner', () => {
  it('renders the error message', () => {
    render(<ErrorBanner message="Upload failed" />);
    expect(screen.getByText('Upload failed')).toBeInTheDocument();
  });

  it('exposes role="alert" so screen readers announce it', () => {
    render(<ErrorBanner message="boom" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('hides dismiss button when no onDismiss handler is given', () => {
    render(<ErrorBanner message="boom" />);
    expect(screen.queryByLabelText(/dismiss/i)).not.toBeInTheDocument();
  });

  it('fires onDismiss when the dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    render(<ErrorBanner message="boom" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText(/dismiss/i));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
