import { Loader2 } from 'lucide-react'

const VARIANTS = {
  primary: 'bg-primary text-on-primary hover:opacity-90 disabled:opacity-60',
  secondary:
    'border border-border bg-surface text-text hover:bg-surface-raised disabled:opacity-60',
  ghost: 'text-text-muted hover:bg-surface-raised hover:text-text disabled:opacity-60',
  danger: 'bg-expense text-white hover:opacity-90 disabled:opacity-60',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-4 py-2.5 text-sm',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  fullWidth = false,
  className = '',
  children,
  disabled,
  ...props
}) {
  return (
    <button
      type="button"
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
        VARIANTS[variant] ?? VARIANTS.primary,
        SIZES[size] ?? SIZES.md,
        fullWidth ? 'w-full' : '',
        className,
      ].join(' ')}
      {...props}
    >
      {isLoading && <Loader2 size={15} className="animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
}
