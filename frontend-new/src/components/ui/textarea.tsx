import { cn } from '@/lib/utils'
import { type TextareaHTMLAttributes, forwardRef } from 'react'

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'flex min-h-[88px] w-full resize-y rounded-xl border border-line-strong bg-white px-3.5 py-2.5 text-sm leading-relaxed text-ink shadow-xs',
        'transition-[border-color,box-shadow] duration-150',
        'placeholder:text-ink-faint',
        'hover:border-brand-300',
        'focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-500/20',
        'disabled:cursor-not-allowed disabled:bg-surface disabled:opacity-60',
        className,
      )}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'
