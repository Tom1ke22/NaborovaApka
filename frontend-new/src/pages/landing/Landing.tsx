import { Link } from 'react-router-dom'
import { Building2, MessageSquare, Send, Sparkles, FileCheck } from 'lucide-react'
import { BrandLogo } from '@/components/Brand'
import { Card, CardContent } from '@/components/ui/card'

const STEPS = [
  {
    icon: Building2,
    title: 'Vyberte pozíciu',
    text: 'Prezrite si voľné miesta vrátane mzdy, pracovného času a podmienok.',
    tint: 'bg-brand-50 text-brand-600 ring-brand-100',
  },
  {
    icon: MessageSquare,
    title: 'Opýtajte sa asistenta',
    text: 'AI asistent odpovie na otázky k pozícii kedykoľvek, aj cez víkend.',
    tint: 'bg-accent-50 text-accent-600 ring-accent-100',
  },
  {
    icon: Send,
    title: 'Prejavte záujem',
    text: 'Vyplňte kontakt, priložte životopis a firma sa vám ozve.',
    tint: 'bg-amber-50 text-amber-600 ring-amber-100',
  },
]

export default function Landing() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="mx-auto flex w-full max-w-5xl items-center px-4 py-6 sm:px-6">
        <BrandLogo subtitle="Nábor s AI asistentom" />
        <Link
          to="/admin/login"
          className="ml-auto rounded-xl px-3.5 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-white hover:text-brand-700"
        >
          Pre firmy
        </Link>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-16 sm:px-6">
        <section className="py-10 text-center sm:py-16">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-semibold text-brand-700 shadow-soft ring-1 ring-inset ring-brand-100 animate-fade">
            <Sparkles className="h-3.5 w-3.5" />
            Nábor, ktorý odpovedá hneď
          </span>

          <h1 className="mx-auto mt-6 max-w-2xl text-balance text-4xl font-bold leading-[1.1] tracking-tight text-ink sm:text-5xl animate-rise">
            Nájdite si prácu v{' '}
            <span className="bg-gradient-to-r from-brand-600 to-accent-600 bg-clip-text text-transparent">
              najlepších firmách
            </span>
          </h1>

          <p className="mx-auto mt-5 max-w-xl text-pretty text-base leading-relaxed text-ink-soft sm:text-lg">
            Vyberte si firmu a prezrite si voľné pracovné pozície. Náš AI asistent vám pomôže
            zorientovať sa a odpovedá na vaše otázky.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, text, tint }, i) => (
            <Card key={title} className="animate-rise" style={{ animationDelay: `${i * 70}ms` }}>
              <CardContent className="p-6">
                <span
                  className={`mb-4 inline-grid h-11 w-11 place-items-center rounded-xl ring-1 ring-inset ${tint}`}
                >
                  <Icon className="h-5 w-5" />
                </span>
                <p className="flex items-baseline gap-2 font-semibold text-ink">
                  <span className="text-xs font-bold text-ink-faint tabular-nums">{i + 1}</span>
                  {title}
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{text}</p>
              </CardContent>
            </Card>
          ))}
        </section>

        <section className="mt-6">
          <Card className="overflow-hidden">
            <div className="flex flex-col items-center gap-4 px-6 py-10 text-center sm:px-10">
              <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-50 text-brand-500 ring-1 ring-inset ring-brand-100">
                <FileCheck className="h-6 w-6" />
              </span>
              <div>
                <h2 className="text-lg font-semibold text-ink">Naše firmy</h2>
                <p className="mt-1.5 max-w-md text-sm text-ink-soft">
                  Zoznam partnerských firiem bude zverejnený čoskoro. Ak ste dostali odkaz priamo od
                  firmy, otvorte ho a uvidíte jej voľné pozície.
                </p>
              </div>
            </div>
          </Card>
        </section>
      </main>

      <footer className="border-t border-line bg-white/60">
        <div className="mx-auto max-w-5xl px-4 py-6 text-center text-xs text-ink-faint sm:px-6">
          © {new Date().getFullYear()} Náborová Aplikácia · <Link to="/admin/login">Pre firmy</Link>
        </div>
      </footer>
    </div>
  )
}
