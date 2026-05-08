interface Props {
  message: string;
  onDismiss?: () => void;
}

export default function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <svg
        className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m0 3.75h.008M10.34 3.94l-8.25 14.3A1.5 1.5 0 0 0 3.41 20.5h17.18a1.5 1.5 0 0 0 1.32-2.26l-8.25-14.3a1.5 1.5 0 0 0-2.62 0Z"
        />
      </svg>
      <p className="flex-1 leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="text-red-400 transition-colors hover:text-red-600"
        >
          ×
        </button>
      )}
    </div>
  );
}
