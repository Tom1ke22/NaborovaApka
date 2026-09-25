/**
 * Rám verejnej časti — hlavička s názvom firmy a pätička.
 *
 * Názov firmy sa odvodzuje zo slugu v URL, aby uchádzač vždy videl, u koho
 * sa vlastne hlási. Backend samostatný endpoint na firmu neponúka.
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { companyNameFromSlug } from '@/lib/utils'
import { BrandMark } from '@/components/Brand'

export function PublicShell({
  slug,
  children,
}: {
  slug: string | undefined
  children: ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="sticky top-0 z-20 border-b border-line/80 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-3 px-4 sm:px-6">
          <Link to={`/${slug ?? ''}`} className="flex min-w-0 items-center gap-2.5">
            <BrandMark />
            <span className="min-w-0 leading-tight">
              <span className="block truncate text-[15px] font-bold tracking-tight text-ink">
                {companyNameFromSlug(slug)}
              </span>
              <span className="block text-[11px] font-medium text-ink-faint">Kariérna stránka</span>
            </span>
          </Link>

          <span className="ml-auto hidden items-center gap-1.5 rounded-full bg-accent-50 px-3 py-1.5 text-xs font-semibold text-accent-700 ring-1 ring-inset ring-accent-100 sm:inline-flex">
            <Sparkles className="h-3.5 w-3.5" />
            S AI asistentom
          </span>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-line bg-white/60">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-1 px-4 py-6 text-center sm:px-6">
          <p className="text-xs text-ink-faint">
            © {new Date().getFullYear()} NáborováApka · {companyNameFromSlug(slug)}
          </p>
        </div>
      </footer>
    </div>
  )
}
