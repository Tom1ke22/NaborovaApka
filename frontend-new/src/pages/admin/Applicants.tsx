import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { SectionLoader } from '@/components/ui/spinner'
import { AdminLayout } from '@/components/AdminLayout'
import { ScoreRing } from '@/components/ScoreRing'
import { type AiStatus, scoreLabel } from '@/lib/score'
import type { Position } from '@/types'
import { cn, formatDateShort } from '@/lib/utils'
import { Search, Inbox, ChevronRight, X, ArrowUpDown, Mail, Phone, Briefcase } from 'lucide-react'

interface ApplicantRow {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  ai_score: number | null
  ai_status: AiStatus
  other_applications: number
  submitted_at: string
  position_id: string
  position_title: string
}

type Sort = 'newest' | 'score'

function initials(first: string, last: string) {
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase()
}

export default function AdminApplicants() {
  const [searchParams] = useSearchParams()
  const positionId = searchParams.get('position')

  const [applicants, setApplicants] = useState<ApplicantRow[]>([])
  const [positionTitle, setPositionTitle] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<Sort>('newest')

  useEffect(() => {
    setLoading(true)
    api
      .get('/admin/applicants', { params: positionId ? { position_id: positionId } : undefined })
      .then((r) => setApplicants(r.data))
      .finally(() => setLoading(false))
  }, [positionId])

  // Názov pozície do hlavičky. Admin nemá endpoint na jednu pozíciu,
  // tak ho vytiahneme zo zoznamu — prežije to aj obnovenie stránky.
  useEffect(() => {
    if (!positionId) {
      setPositionTitle(null)
      return
    }
    api
      .get('/admin/positions')
      .then((r) =>
        setPositionTitle((r.data as Position[]).find((p) => p.id === positionId)?.title ?? null),
      )
      .catch(() => setPositionTitle(null))
  }, [positionId])

  // Hľadanie aj zoradenie bežia nad načítaným zoznamom, bez ďalších volaní API.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = q
      ? applicants.filter((a) =>
          [`${a.first_name} ${a.last_name}`, a.email, a.phone, a.position_title].some((f) =>
            f?.toLowerCase().includes(q),
          ),
        )
      : applicants

    return [...filtered].sort((a, b) => {
      if (sort === 'score') return (b.ai_score ?? -1) - (a.ai_score ?? -1)
      return new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime()
    })
  }, [applicants, query, sort])

  const scored = applicants.filter((a) => a.ai_score != null)
  const strong = scored.filter((a) => (a.ai_score ?? 0) >= 7).length

  return (
    <AdminLayout
      title="Záujemcovia"
      subtitle={
        positionTitle ? (
          <span className="flex items-center gap-2">
            <span className="truncate">Filtrované na: {positionTitle}</span>
            <Link
              to="/admin/applicants"
              className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 transition-colors hover:bg-brand-100"
            >
              <X className="h-3 w-3" />
              Zrušiť
            </Link>
          </span>
        ) : (
          'Všetci uchádzači naprieč pozíciami'
        )
      }
      actions={
        !loading &&
        applicants.length > 0 && (
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{applicants.length} celkom</Badge>
            {strong > 0 && <Badge variant="success">{strong} veľmi vhodných</Badge>}
          </div>
        )
      }
      width="narrow"
    >
      {loading ? (
        <SectionLoader label="Načítavame záujemcov…" />
      ) : applicants.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title={
            positionId
              ? 'Na túto pozíciu sa zatiaľ nikto neprihlásil'
              : 'Zatiaľ žiadni záujemcovia'
          }
          description="Keď niekto prejaví záujem cez kariérnu stránku, objaví sa tu aj s hodnotením od AI."
        />
      ) : (
        <>
          {/* Hľadanie a zoradenie */}
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <div className="relative min-w-0 flex-1 sm:max-w-sm">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Hľadať podľa mena, emailu, telefónu alebo pozície…"
                className="pl-10"
                aria-label="Hľadať v záujemcoch"
              />
            </div>

            <button
              onClick={() => setSort((s) => (s === 'newest' ? 'score' : 'newest'))}
              className="inline-flex h-11 shrink-0 items-center gap-2 rounded-xl border border-line-strong bg-white px-3.5 text-sm font-medium text-ink-soft shadow-xs transition-colors hover:border-brand-300 hover:text-brand-700"
            >
              <ArrowUpDown className="h-4 w-4" />
              {sort === 'newest' ? 'Najnovšie' : 'Najvyššie skóre'}
            </button>
          </div>

          {visible.length === 0 ? (
            <EmptyState
              icon={Search}
              title="Nič sa nenašlo"
              description={`Pre „${query}" nemáme žiadneho záujemcu.`}
            />
          ) : (
            <div className="space-y-3">
              {visible.map((app, i) => (
                <Card
                  key={app.id}
                  interactive
                  className="animate-rise"
                  style={{ animationDelay: `${Math.min(i, 6) * 45}ms` }}
                  // Filter nesieme so sebou, nech sa zo šípky v detaile
                  // vrátime naspäť do zoznamu pre danú pozíciu.
                  to={`/admin/applicants/${app.id}${positionId ? `?position=${positionId}` : ''}`}
                >
                  <CardContent className="flex items-center gap-4 p-4 sm:p-5">
                    <span
                      className={cn(
                        'grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-bold',
                        'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100',
                      )}
                    >
                      {initials(app.first_name, app.last_name)}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <p className="truncate font-semibold text-ink">
                          {app.first_name} {app.last_name}
                        </p>
                        {/* Bez filtra na pozíciu je zoznam naprieč všetkými — inak
                            nebolo vidieť, kam sa kto vlastne hlási. S filtrom je to
                            už jasné z podnadpisu stránky, tak sa tu neopakuje. */}
                        {!positionId && (
                          <Badge variant="outline" className="gap-1">
                            <Briefcase className="h-3 w-3" />
                            {app.position_title}
                          </Badge>
                        )}
                        {app.other_applications > 0 && (
                          <Badge
                            variant="warning"
                            title={`Ďalšie prihlášky z tohto e-mailu: ${app.other_applications}`}
                          >
                            Opakovaná prihláška
                          </Badge>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-ink-faint">
                        <span className="inline-flex items-center gap-1 truncate">
                          <Mail className="h-3 w-3 shrink-0" />
                          {app.email}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Phone className="h-3 w-3 shrink-0" />
                          {app.phone}
                        </span>
                      </div>
                    </div>

                    <div className="hidden shrink-0 text-right sm:block">
                      <p className="text-xs font-medium text-ink-soft">{scoreLabel(app.ai_score, app.ai_status)}</p>
                      <p className="mt-0.5 text-xs text-ink-faint">
                        {formatDateShort(app.submitted_at)}
                      </p>
                    </div>

                    <ScoreRing score={app.ai_score} status={app.ai_status} size="sm" />

                    <ChevronRight className="hidden h-5 w-5 shrink-0 text-ink-faint sm:block" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </AdminLayout>
  )
}
