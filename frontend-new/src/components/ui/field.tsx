import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'
import { TriangleAlert } from 'lucide-react'

interface FieldProps {
  label: string
  children: ReactNode
  /** Doplní červenú hviezdičku k názvu poľa. */
  required?: boolean
  /** Pokojná pomocná veta pod poľom. */
  hint?: string
  /** Chybová hláška — nahradí hint a zafarbí sa načerveno. */
  error?: string
  className?: string
}

/** Jednotný obal pre pole formulára: popis, obsah, hint alebo chyba. */
export function Field({ label, children, required, hint, error, className }: FieldProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label className="text-sm font-medium text-ink-soft">
        {label}
        {required && <span className="ml-0.5 text-rose-500">*</span>}
      </label>
      {children}
      {error ? (
        <p className="flex items-center gap-1.5 text-xs font-medium text-rose-600 animate-fade">
          <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-ink-faint">{hint}</p>
      )}
    </div>
  )
}
