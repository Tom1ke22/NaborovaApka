import { cn } from '@/lib/utils'
import { type ButtonHTMLAttributes, forwardRef } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'accent' | 'soft' | 'outline' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg' | 'icon'
}

const VARIANTS: Record<NonNullable<ButtonProps['variant']>, string> = {
  default:
    'bg-brand-600 text-white shadow-brand hover:bg-brand-700 active:bg-brand-800 focus-visible:ring-brand-500/45',
  accent:
    'bg-accent-600 text-white shadow-soft hover:bg-accent-700 active:bg-accent-800 focus-visible:ring-accent-500/45',
  soft:
    'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200 hover:bg-brand-100 hover:ring-brand-300 focus-visible:ring-brand-500/45',
  outline:
    'bg-white text-ink-soft ring-1 ring-inset ring-line-strong shadow-xs hover:bg-brand-50 hover:text-brand-700 hover:ring-brand-300 focus-visible:ring-brand-500/45',
  ghost:
    'text-ink-soft hover:bg-brand-50 hover:text-brand-700 focus-visible:ring-brand-500/45',
  destructive:
    'bg-rose-600 text-white shadow-soft hover:bg-rose-700 active:bg-rose-800 focus-visible:ring-rose-500/45',
}

const SIZES: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'h-8 gap-1.5 rounded-lg px-3 text-[13px]',
  md: 'h-10 gap-2 rounded-xl px-4 text-sm',
  lg: 'h-12 gap-2 rounded-xl px-6 text-[15px]',
  icon: 'h-10 w-10 rounded-xl',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex shrink-0 select-none items-center justify-center font-medium',
        'transition-[background-color,color,box-shadow,transform] duration-150',
        'focus-visible:outline-none focus-visible:ring-4',
        'active:translate-y-px',
        'disabled:pointer-events-none disabled:opacity-45',
        '[&>svg]:shrink-0',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
