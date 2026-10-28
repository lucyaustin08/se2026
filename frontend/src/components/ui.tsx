/**
 * Small building blocks for screens built to DESIGN.md: square corners, paper surfaces, a
 * poster-red main action and a 2px poster-red focus outline. Buttons are at least 44px tall
 * (the Thumb Rule).
 */
import type { ReactNode } from "react";

export const primaryButton =
  "min-h-11 bg-brand-700 px-4 py-2 font-medium text-paper hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60";
export const secondaryButton =
  "min-h-11 border border-gray-400 bg-paper px-4 py-2 font-medium text-ink hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60";
export const pageHeading = "font-display text-2xl tracking-wide uppercase";
export const sectionHeading = "font-display text-lg tracking-wide uppercase";

const fieldClass =
  "mt-1 block min-h-11 w-full border bg-paper px-3 py-2 text-ink focus-visible:outline-2 focus-visible:outline-brand-600";

export interface InputProps {
  id: string;
  className: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
}

interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  input: (props: InputProps) => ReactNode;
}

/** A labelled control with an optional hint and an error tied to it by aria-describedby. */
export function FormField({ id, label, hint, error, input }: FormFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ");
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {input({
        id,
        className: `${fieldClass} ${error ? "border-2 border-brand-700" : "border-gray-400"}`,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy || undefined,
      })}
      {hint && (
        <p id={hintId} className="mt-1 text-sm text-gray-600">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1 text-sm font-medium text-brand-700">
          {error}
        </p>
      )}
    </div>
  );
}
