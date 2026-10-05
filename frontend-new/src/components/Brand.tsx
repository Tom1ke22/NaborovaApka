import { cn } from '@/lib/utils'
import { Briefcase } from 'lucide-react'

/**
 * Značková ikonka — štvorec s prechodom a kufríkom.
 *
 * `onDark` prepína celé pozadie, nie iba farbu: na tmavej hlavičke by sa
 * prechod z `bg-brand-gradient` prekresľoval cez priesvitnú bielu.
 */
export function BrandMark({ onDark = false, className }: { onDark?: boolean; className?: string }) {
  return (
    <span
      className={cn(
        'inline-grid h-9 w-9 shrink-0 place-items-center rounded-xl text-white',
        onDark ? 'bg-white/15 ring-1 ring-inset ring-white/25' : 'bg-brand-gradient shadow-brand',
        className,
      )}
    >
      <Briefcase className="h-[18px] w-[18px]" strokeWidth={2.2} />
    </span>
  )
}

/** Logo s názvom. `onDark` sa používa v tmavej hlavičke administrácie. */
export function BrandLogo({
  subtitle,
  onDark = false,
  className,
}: {
  subtitle?: string
  onDark?: boolean
  className?: string
}) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      <BrandMark onDark={onDark} />
      <span className="min-w-0 leading-tight">
        <span
          className={cn(
            'block truncate text-[15px] font-bold tracking-tight',
            onDark ? 'text-white' : 'text-ink',
          )}
        >
          Náborová <span className={onDark ? 'text-accent-300' : 'text-brand-600'}>Aplikácia</span>
        </span>
        {subtitle && (
          <span
            className={cn(
              'block truncate text-[11px] font-medium',
              onDark ? 'text-white/65' : 'text-ink-faint',
            )}
          >
            {subtitle}
          </span>
        )}
      </span>
    </span>
  )
}
