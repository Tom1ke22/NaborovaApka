import { cn } from '@/lib/utils'
import { Check, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CheckboxRowProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  description?: string
  /** Ak je zadané, vpravo pribudne kôš na odstránenie celého riadku. */
  onRemove?: () => void
}

/** Zaškrtávacie pole ako celý klikateľný riadok — ľahšie sa trafí než malý štvorček. */
export function CheckboxRow({ checked, onChange, label, description, onRemove }: CheckboxRowProps) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border p-3.5 transition-colors duration-150',
        checked
          ? 'border-brand-300 bg-brand-50/70'
          : 'border-line bg-white hover:border-brand-200 hover:bg-brand-50/40',
      )}
    >
      <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-3">
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
      {onRemove && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={`Odstrániť požiadavku ${label}`}
          onClick={onRemove}
          className="-my-2 h-8 w-8 shrink-0 text-ink-faint hover:text-rose-600"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}
