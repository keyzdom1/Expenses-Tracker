import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

const VARIANTS = {
  success: { className: 'bg-income-soft text-income', Icon: CheckCircle2, role: 'status' },
  error: { className: 'bg-expense-soft text-expense', Icon: XCircle, role: 'alert' },
  warning: { className: 'bg-warning-soft text-warning', Icon: AlertTriangle, role: 'alert' },
  info: { className: 'bg-surface-raised text-info', Icon: Info, role: 'status' },
}

/** Status message. Icon + text means meaning never depends on colour. */
export default function Alert({ variant = 'info', title, children, className = '' }) {
  const { className: variantClass, Icon, role } = VARIANTS[variant] ?? VARIANTS.info

  return (
    <div role={role} className={`flex items-start gap-2 rounded-xl p-3 text-sm ${variantClass} ${className}`}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={title ? 'mt-0.5 text-xs' : ''}>{children}</div>}
      </div>
    </div>
  )
}
