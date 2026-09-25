import { cn } from '@/lib/utils'
import { type SelectHTMLAttributes, forwardRef } from 'react'
import { ChevronDown } from 'lucide-react'

/** Natívny <select> v šate zvyšku formulára — vrátane vlastnej šípky. */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          'flex h-11 w-full appearance-none rounded-xl border border-line-strong bg-white pl-3.5 pr-10 text-sm text-ink shadow-xs',
          'transition-[border-color,box-shadow] duration-150',
          'hover:border-brand-300',
          'focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-500/20',
          'disabled:cursor-not-allowed disabled:bg-surface disabled:opacity-60',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
    </div>
  ),
)
Select.displayName = 'Select'
