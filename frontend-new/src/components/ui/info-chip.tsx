import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export type Tone = 'brand' | 'accent' | 'amber' | 'emerald' | 'slate'

const TONES: Record<Tone, string> = {
  brand: 'bg-brand-50 text-brand-700 ring-brand-100',
  accent: 'bg-accent-50 text-accent-700 ring-accent-100',
  amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  slate: 'bg-slate-50 text-slate-600 ring-slate-200',
}

/** Malý farebný štítok s ikonou — miesto, mzda, počet miest, dátum nástupu. */
export function InfoChip({
  icon: Icon,
  tone = 'slate',
  children,
  className,
}: {
  icon: LucideIcon
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium ring-1 ring-inset',
        TONES[tone],
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" />
      {children}
    </span>
  )
}

/** Riadok „popis → hodnota" v bočných kartách s detailmi. */
export function DetailRow({
  icon: Icon,
  label,
  value,
  tone = 'brand',
}: {
  icon: LucideIcon
  label: string
  value: ReactNode
  tone?: Tone
}) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <span
        className={cn(
          'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
          TONES[tone],
        )}
      >
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">{label}</p>
        <p className="text-sm text-ink">{value}</p>
      </div>
    </div>
  )
}
