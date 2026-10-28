import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface DialogProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** "alertdialog" for a pop-up that reports a problem or asks to confirm. */
  role?: "dialog" | "alertdialog";
}

/**
 * A modal pop-up, built here because the stack has no component library.
 *
 * Focus moves into it when it opens and back to whatever opened it when it closes. Tab stays
 * inside it, and Escape closes it. The page behind is dimmed with a flat tint, not a shadow,
 * per DESIGN.md.
 */
export function Dialog({ title, onClose, children, role = "dialog" }: DialogProps) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    // Start on the first field or button in the content, not on Close.
    const first = content.current?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel.current)?.focus();
    return () => opener?.focus();
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab" || !panel.current) return;
    const focusable = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 sm:items-center sm:p-4">
      <div
        ref={panel}
        role={role}
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto border-2 border-ink bg-paper p-5 text-ink focus-visible:outline-none"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={titleId} className="font-display text-xl tracking-wide uppercase">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="min-h-11 min-w-11 border border-gray-400 bg-paper text-lg leading-none hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-brand-600"
          >
            ×
          </button>
        </div>
        <div ref={content} className="mt-4">
          {children}
        </div>
      </div>
    </div>
  );
}
