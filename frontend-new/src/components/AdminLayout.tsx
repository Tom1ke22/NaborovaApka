/**
 * Spoločný rám administrácie.
 *
 * Predtým mala každá admin stránka vlastnú hlavičku a medzi zoznamom pozícií
 * a zoznamom záujemcov sa dalo preklikať len cez tlačidlo v karte pozície.
 * Tu je navigácia stála, takže obe sekcie sú vždy na jedno kliknutie.
 */
import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { ArrowLeft, Briefcase, LogOut, Users } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { BrandLogo } from '@/components/Brand'

const NAV: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/admin/positions', label: 'Pozície', icon: Briefcase },
  { to: '/admin/applicants', label: 'Záujemcovia', icon: Users },
]

interface AdminLayoutProps {
  title: string
  subtitle?: ReactNode
  /** Tlačidlá vpravo v hlavičke stránky. */
  actions?: ReactNode
  /** Šípka späť vľavo od nadpisu. */
  backTo?: string
  /** Pás pod nadpisom — napríklad prehľad počtov. */
  banner?: ReactNode
  children: ReactNode
  /** Šírka obsahu. */
  width?: 'narrow' | 'wide'
}

export function AdminLayout({
  title,
  subtitle,
  actions,
  backTo,
  banner,
  children,
  width = 'wide',
}: AdminLayoutProps) {
  const { logout } = useAuth()

  return (
    <div className="min-h-screen bg-canvas">
      {/* Horný tmavý pruh so značkou a navigáciou */}
      <header className="bg-brand-gradient">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6">
          <BrandLogo onDark />

          <nav className="ml-auto hidden items-center gap-1 sm:flex">
            {NAV.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors duration-150',
                    isActive
                      ? 'bg-white/20 text-white ring-1 ring-inset ring-white/25'
                      : 'text-white/75 hover:bg-white/10 hover:text-white',
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <button
            onClick={logout}
            className="ml-auto flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-white/75 transition-colors hover:bg-white/10 hover:text-white sm:ml-2"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden md:inline">Odhlásiť</span>
          </button>
        </div>

        {/* Navigácia na mobile — vlastný riadok, aby sa zmestila */}
        <nav className="flex gap-1 px-4 pb-3 sm:hidden">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-white/20 text-white ring-1 ring-inset ring-white/25'
                    : 'text-white/75 hover:bg-white/10',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      {/* Hlavička stránky */}
      <div className="border-b border-line bg-white/80 backdrop-blur">
        <div
          className={cn(
            'mx-auto px-4 py-5 sm:px-6',
            width === 'wide' ? 'max-w-7xl' : 'max-w-4xl',
          )}
        >
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
            {backTo && (
              <Button
                variant="outline"
                size="icon"
                to={backTo}
                aria-label="Späť"
                className="h-9 w-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-xl font-bold tracking-tight text-ink sm:text-2xl">
                {title}
              </h1>
              {subtitle && <div className="mt-0.5 truncate text-sm text-ink-faint">{subtitle}</div>}
            </div>
            {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
          </div>
          {banner && <div className="mt-4">{banner}</div>}
        </div>
      </div>

      <main
        className={cn(
          'mx-auto px-4 py-8 sm:px-6',
          width === 'wide' ? 'max-w-7xl' : 'max-w-4xl',
        )}
      >
        {children}
      </main>
    </div>
  )
}
