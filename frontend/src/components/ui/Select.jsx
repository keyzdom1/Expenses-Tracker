import { useId } from 'react'

/** Labelled native select with optional error and hint text. */
export default function Select({
  label,
  error,
  hint,
  options = [],
  placeholder,
  className = '',
  id,
  children,
  ...props
}) {
  const generatedId = useId()
  const selectId = id ?? `select-${generatedId}`
  const describedBy = error ? `${selectId}-error` : hint ? `${selectId}-hint` : undefined

  return (
    <div className={className}>
      {label && (
        <label htmlFor={selectId} className="mb-1.5 block text-xs font-medium text-text">
          {label}
        </label>
      )}
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={[
          'w-full rounded-lg border bg-surface px-3 py-2 text-sm text-text',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
          error ? 'border-expense' : 'border-border',
        ].join(' ')}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
        {children}
      </select>
      {error ? (
        <p id={`${selectId}-error`} className="mt-1 text-xs text-expense">
          {error}
        </p>
      ) : hint ? (
        <p id={`${selectId}-hint`} className="mt-1 text-xs text-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
