import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Načítava sa"
      className={cn(
        'inline-block h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600',
        className,
      )}
    />
  )
}

/** Celostránkový stav načítania — používa sa, kým nepríde prvá odpoveď z API. */
export function PageLoader({ label = 'Načítava sa…' }: { label?: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-canvas">
      <Spinner className="h-9 w-9 border-[3px]" />
      <p className="text-sm font-medium text-ink-faint">{label}</p>
    </div>
  )
}

/** Načítanie v rámci obsahu stránky, keď hlavička už stojí. */
export function SectionLoader({ label = 'Načítava sa…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20">
      <Spinner className="h-8 w-8" />
      <p className="text-sm text-ink-faint">{label}</p>
    </div>
  )
}
