import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type PositionListItem, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { InfoChip } from '@/components/ui/info-chip'
import { EmptyState } from '@/components/ui/empty-state'
import { PageLoader } from '@/components/ui/spinner'
import { PublicShell } from '@/components/PublicShell'
import { companyNameFromSlug, formatDateShort, formatMoney, plural } from '@/lib/utils'
import {
  MapPin,
  Calendar,
  Euro,
  Users,
  Search,
  ChevronRight,
  Briefcase,
  Building2,
} from 'lucide-react'

export default function PositionList() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [positions, setPositions] = useState<PositionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState('')

  useEffect(() => {
    api
      .get(`/${slug}/positions`)
      .then((r) => setPositions(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [slug])

  // Filtrovanie beží nad už načítaným zoznamom — žiadne ďalšie volanie API.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return positions
    return positions.filter((p) =>
      [p.title, p.work_area, p.location].some((field) => field?.toLowerCase().includes(q)),
    )
  }, [positions, query])

  if (loading) return <PageLoader label="Načítavame pozície…" />

  if (error)
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
        <Card className="max-w-md">
          <CardContent className="flex flex-col items-center p-10 text-center">
            <span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-rose-50 text-rose-500 ring-1 ring-inset ring-rose-100">
              <Building2 className="h-7 w-7" />
            </span>
            <h1 className="text-lg font-semibold text-ink">Firma nebola nájdená</h1>
            <p className="mt-1.5 text-sm text-ink-soft">
              Skontrolujte prosím odkaz, ktorý ste dostali.
            </p>
          </CardContent>
        </Card>
      </div>
    )

  return (
    <PublicShell slug={slug}>
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <div className="animate-rise">
          <h1 className="text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Voľné pracovné miesta
          </h1>
          <p className="mt-2 text-ink-soft">
            {positions.length === 0
              ? `${companyNameFromSlug(slug)} momentálne nemá zverejnené žiadne pozície.`
              : `${companyNameFromSlug(slug)} · ${positions.length} ${plural(
                  positions.length,
                  'otvorená pozícia',
                  'otvorené pozície',
                  'otvorených pozícií',
                )}`}
          </p>
        </div>

        {positions.length > 2 && (
          <div className="relative mt-6 max-w-md animate-fade">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Hľadať podľa názvu, oblasti alebo mesta…"
              className="pl-10"
              aria-label="Hľadať v pozíciách"
            />
          </div>
        )}

        <div className="mt-6 space-y-4">
          {positions.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="Zatiaľ žiadne voľné pozície"
              description="Pozrite sa sem neskôr — nové miesta pribúdajú priebežne."
            />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={Search}
              title="Nič sa nenašlo"
              description={`Pre „${query}" nemáme žiadnu pozíciu. Skúste iné slovo.`}
            />
          ) : (
            visible.map((pos, i) => (
              <Card
                key={pos.id}
                interactive
                className="stripe-brand animate-rise"
                style={{ animationDelay: `${Math.min(i, 6) * 55}ms` }}
                onClick={() => navigate(`/${slug}/${pos.id}`)}
              >
                <CardContent className="p-5 sm:p-6">
                  <div className="flex items-start gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                        <h2 className="text-lg font-semibold text-ink sm:text-xl">{pos.title}</h2>
                        <Badge>{CONTRACT_TYPE_LABELS[pos.contract_type]}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-ink-faint">{pos.work_area}</p>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <InfoChip icon={MapPin} tone="brand">
                          {pos.location}
                        </InfoChip>
                        {pos.salary_amount && (
                          <InfoChip icon={Euro} tone="emerald">
                            {formatMoney(pos.salary_amount)} / {SALARY_PERIOD_LABELS[pos.salary_period]}
                          </InfoChip>
                        )}
                        <InfoChip icon={Users} tone="accent">
                          {pos.open_slots}{' '}
                          {plural(pos.open_slots, 'voľné miesto', 'voľné miesta', 'voľných miest')}
                        </InfoChip>
                        {pos.start_date && (
                          <InfoChip icon={Calendar} tone="amber">
                            Nástup {formatDateShort(pos.start_date)}
                          </InfoChip>
                        )}
                      </div>
                    </div>

                    <span className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-600 transition-colors sm:grid">
                      <ChevronRight className="h-5 w-5" />
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </PublicShell>
  )
}
