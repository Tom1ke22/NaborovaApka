import { cn } from '@/lib/utils'
import { type InputHTMLAttributes, forwardRef } from 'react'

export const inputBase =
  'flex h-11 w-full rounded-xl border border-line-strong bg-white px-3.5 text-sm text-ink shadow-xs ' +
  'transition-[border-color,box-shadow,background-color] duration-150 ' +
  'placeholder:text-ink-faint ' +
  'hover:border-brand-300 ' +
  'focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-500/20 ' +
  'disabled:cursor-not-allowed disabled:bg-surface disabled:opacity-60'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(inputBase, className)} {...props} />
  ),
)
Input.displayName = 'Input'
