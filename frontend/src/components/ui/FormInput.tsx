import type { InputHTMLAttributes } from "react";

type FormInputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
};

export function FormInput({
  id,
  label,
  hint,
  error,
  className = "",
  ...props
}: FormInputProps) {
  const inputId = id ?? props.name;

  if (!inputId) {
    throw new Error("FormInput requires an id or name for accessibility.");
  }

  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-2">
      <label
        htmlFor={inputId}
        className="notranslate block text-sm font-medium text-text-primary"
      >
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={[
          "block w-full min-w-0 rounded-lg border border-border bg-white px-3 py-2.5 text-sm text-text-primary shadow-sm",
          "min-h-11",
          "placeholder:text-text-secondary/70",
          "disabled:cursor-not-allowed disabled:bg-surface disabled:text-text-secondary",
          error ? "border-red-500" : "",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...props}
      />
      {hint ? (
        <p id={hintId} className="text-sm text-text-secondary">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
