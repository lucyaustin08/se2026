interface LoadingProps {
  label?: string;
}

export function Loading({ label = "Loading…" }: LoadingProps) {
  return (
    <p role="status" className="text-gray-700">
      {label}
    </p>
  );
}

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-900">
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded border border-red-800 px-3 py-1 text-sm font-medium hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-red-800"
        >
          Try again
        </button>
      )}
    </div>
  );
}
