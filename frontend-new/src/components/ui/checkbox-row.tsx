import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

interface CheckboxRowProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  description?: string
}

/** Zaškrtávacie pole ako celý klikateľný riadok — ľahšie sa trafí než malý štvorček. */
export function CheckboxRow({ checked, onChange, label, description }: CheckboxRowProps) {
  return (
    <label
      className={cn(
        'flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors duration-150',
        checked
          ? 'border-brand-300 bg-brand-50/70'
          : 'border-line bg-white hover:border-brand-200 hover:bg-brand-50/40',
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className={cn(
          'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors duration-150',
          'peer-focus-visible:ring-4 peer-focus-visible:ring-brand-500/25',
          checked ? 'border-brand-600 bg-brand-600 text-white' : 'border-line-strong bg-white',
        )}
      >
        {checked && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
      </span>
      <span className="min-w-0">
        <span className={cn('block text-sm font-medium', checked ? 'text-brand-800' : 'text-ink')}>
          {label}
        </span>
        {description && <span className="mt-0.5 block text-xs text-ink-faint">{description}</span>}
      </span>
    </label>
  )
}
