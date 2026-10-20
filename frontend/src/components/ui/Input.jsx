import { forwardRef, useId } from 'react'

/** Labelled text input with inline validation message and hint. */
const Input = forwardRef(function Input(
  { label, error, hint, type = 'text', className = '', id, ...props },
  ref,
) {
  const generatedId = useId()
  const inputId = id ?? `field-${generatedId}`
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined

  return (
    <div className={className}>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-xs font-medium text-text">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        type={type}
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
        <p id={`${inputId}-error`} className="mt-1 text-xs text-expense">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="mt-1 text-xs text-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
})

export default Input
