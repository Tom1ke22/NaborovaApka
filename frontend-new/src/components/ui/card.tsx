import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'react'
import { Link } from 'react-router-dom'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Zvýrazní kartu pri prejdení myšou — pre klikateľné karty v zoznamoch. */
  interactive?: boolean
  /**
   * Cieľ preklikania. Karta sa vykreslí ako odkaz, takže cmd/ctrl + klik
   * otvorí novú kartu a shift + klik nové okno — tak, ako to robí prehliadač.
   */
  to?: string
}

export function Card({ className, interactive = false, to, ...props }: CardProps) {
  const classes = cn(
    'rounded-2xl border border-line bg-white shadow-soft',
    interactive &&
      'cursor-pointer transition-[box-shadow,transform,border-color] duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lift',
    className,
  )

  if (to) {
    return (
      <Link
        to={to}
        className={cn('block', classes)}
        {...(props as HTMLAttributes<HTMLAnchorElement>)}
      />
    )
  }

  return <div className={classes} {...props} />
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col gap-1 px-6 pt-6', className)} {...props} />
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn('flex items-center gap-2 text-base font-semibold text-ink', className)}
      {...props}
    />
  )
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-ink-faint', className)} {...props} />
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-6 pb-6', className)} {...props} />
}
