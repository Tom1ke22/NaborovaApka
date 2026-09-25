import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'react'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?:
    | 'default'
    | 'secondary'
    | 'success'
    | 'destructive'
    | 'warning'
    | 'accent'
    | 'outline'
}

const VARIANTS: Record<NonNullable<BadgeProps['variant']>, string> = {
  default: 'bg-brand-50 text-brand-700 ring-brand-200',
  secondary: 'bg-slate-100 text-slate-600 ring-slate-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  destructive: 'bg-rose-50 text-rose-700 ring-rose-200',
  warning: 'bg-amber-50 text-amber-700 ring-amber-200',
  accent: 'bg-accent-50 text-accent-700 ring-accent-200',
  outline: 'bg-white text-ink-soft ring-line-strong',
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset whitespace-nowrap',
        '[&>svg]:shrink-0',
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  )
}
