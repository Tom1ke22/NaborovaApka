import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  /** Napríklad tlačidlo „Pridať prvú pozíciu". */
  action?: ReactNode
}

/** Prázdny zoznam — namiesto holej sivej vety ponúkne aj ďalší krok. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line-strong bg-white/60 px-6 py-16 text-center animate-fade">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-500 ring-1 ring-brand-100">
        <Icon className="h-7 w-7" />
      </div>
      <p className="text-base font-semibold text-ink">{title}</p>
      {description && <p className="mt-1.5 max-w-sm text-sm text-ink-faint">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
