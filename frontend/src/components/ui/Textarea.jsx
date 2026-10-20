import { useId } from 'react'

/** Labelled textarea with optional error and hint text. */
export default function Textarea({ label, error, hint, className = '', id, ...props }) {
  const generatedId = useId()
  const fieldId = id ?? `textarea-${generatedId}`
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined

  return (
    <div className={className}>
      {label && (
        <label htmlFor={fieldId} className="mb-1.5 block text-xs font-medium text-text">
          {label}
        </label>
      )}
      <textarea
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={[
          'w-full rounded-lg border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-muted',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
          error ? 'border-expense' : 'border-border',
        ].join(' ')}
        {...props}
      />
      {error ? (
        <p id={`${fieldId}-error`} className="mt-1 text-xs text-expense">
          {error}
        </p>
      ) : hint ? (
        <p id={`${fieldId}-hint`} className="mt-1 text-xs text-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
