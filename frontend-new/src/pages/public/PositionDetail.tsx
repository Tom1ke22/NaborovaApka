import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type Position, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { InfoChip, DetailRow } from '@/components/ui/info-chip'
import { PageLoader } from '@/components/ui/spinner'
import { PublicShell } from '@/components/PublicShell'
import { formatDateShort, formatMoney, plural } from '@/lib/utils'
import {
  ArrowLeft,
  MapPin,
  Euro,
  Users,
  Calendar,
  CircleCheck,
  MessageSquare,
  FileText,
  Info,
  ListChecks,
  Clock,
  Timer,
  Coffee,
  Sofa,
  Utensils,
  User,
  Sparkles,
} from 'lucide-react'

export default function PositionDetail() {
  const { slug, positionId } = useParams<{ slug: string; positionId: string }>()
  const navigate = useNavigate()
  const [position, setPosition] = useState<Position | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get(`/${slug}/positions/${positionId}`)
      .then((r) => setPosition(r.data))
      .catch(() => navigate(`/${slug}`))
      .finally(() => setLoading(false))
  }, [slug, positionId, navigate])

  if (loading) return <PageLoader label="Načítavame pozíciu…" />
  if (!position) return null

  const req = position.requirements
  const requirementItems = req
    ? [
        req.education_level && `Vzdelanie: ${req.education_level}`,
        req.experience_required &&
          `Prax: ${
            req.experience_years
              ? `min. ${req.experience_years} ${plural(req.experience_years, 'rok', 'roky', 'rokov')}`
              : 'požadovaná'
          }`,
        req.slovak_language_level && `Slovenčina: ${req.slovak_language_level}`,
        req.foreign_language_level && `Cudzí jazyk: ${req.foreign_language_level}`,
        req.hygiene_minimum_required && 'Hygienické minimum',
        req.health_certificate_required && 'Zdravotný preukaz',
      ].filter((x): x is string => Boolean(x))
    : []

  const conditions = [
    position.working_hours && { icon: Clock, label: 'Pracovný čas', value: position.working_hours },
    position.shift_type && { icon: Timer, label: 'Zmennosť', value: position.shift_type },
    position.work_regime && { icon: Timer, label: 'Pracovný režim', value: position.work_regime },
    position.break_info && { icon: Coffee, label: 'Prestávka', value: position.break_info },
    position.vacation_days != null && {
      icon: Sofa,
      label: 'Dovolenka',
      value: `${position.vacation_days} ${plural(position.vacation_days, 'deň', 'dni', 'dní')}`,
    },
    position.meal_allowance && {
      icon: Utensils,
      label: 'Stravné',
      value: position.meal_allowance,
    },
    position.contact_person && {
      icon: User,
      label: 'Kontaktná osoba',
      value: position.contact_person,
    },
  ].filter((x): x is { icon: typeof Clock; label: string; value: string } => Boolean(x))

  return (
    <PublicShell slug={slug}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <button
          onClick={() => navigate(`/${slug}`)}
          className="group mb-6 inline-flex items-center gap-2 rounded-lg py-1 text-sm font-medium text-ink-soft transition-colors hover:text-brand-700"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Späť na zoznam pozícií
        </button>

        {/* Hlavička pozície */}
        <Card className="overflow-hidden animate-rise">
          <div className="bg-brand-gradient px-6 py-7 sm:px-8">
            <div className="flex flex-wrap items-start gap-x-4 gap-y-3">
              <div className="min-w-0 flex-1">
                <h1 className="text-2xl font-bold leading-tight tracking-tight text-white sm:text-3xl">
                  {position.title}
                </h1>
                <p className="mt-1.5 text-sm text-white/75">{position.work_area}</p>
              </div>
              <span className="rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white ring-1 ring-inset ring-white/25">
                {CONTRACT_TYPE_LABELS[position.contract_type]}
              </span>
            </div>
          </div>

          <CardContent className="flex flex-wrap gap-2 p-5 sm:px-8">
            <InfoChip icon={MapPin} tone="brand">
              {position.location}
            </InfoChip>
            {position.salary_amount && (
              <InfoChip icon={Euro} tone="emerald">
                {formatMoney(position.salary_amount)} / {SALARY_PERIOD_LABELS[position.salary_period]}
              </InfoChip>
            )}
            <InfoChip icon={Users} tone="accent">
              {position.open_slots}{' '}
              {plural(position.open_slots, 'voľné miesto', 'voľné miesta', 'voľných miest')}
            </InfoChip>
            {position.start_date && (
              <InfoChip icon={Calendar} tone="amber">
                Nástup {formatDateShort(position.start_date)}
              </InfoChip>
            )}
          </CardContent>
        </Card>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Ľavý stĺpec — obsah inzerátu */}
          <div className="space-y-6 lg:col-span-2">
            {position.description && (
              <Card className="animate-rise">
                <CardContent className="p-6 sm:p-7">
                  <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-ink">
                    <FileText className="h-4 w-4 text-brand-500" />
                    Náplň práce
                  </h2>
                  <p className="whitespace-pre-wrap leading-relaxed text-ink-soft">
                    {position.description}
                  </p>
                </CardContent>
              </Card>
            )}

            {requirementItems.length > 0 && (
              <Card className="animate-rise">
                <CardContent className="p-6 sm:p-7">
                  <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-ink">
                    <ListChecks className="h-4 w-4 text-accent-600" />
                    Čo od vás očakávame
                  </h2>
                  <ul className="grid gap-2.5 sm:grid-cols-2">
                    {requirementItems.map((item) => (
                      <li
                        key={item}
                        className="flex items-start gap-2.5 rounded-xl bg-emerald-50/60 px-3.5 py-2.5 text-sm text-ink ring-1 ring-inset ring-emerald-100"
                      >
                        <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {position.additional_info && (
              <Card className="animate-rise">
                <CardContent className="p-6 sm:p-7">
                  <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-ink">
                    <Info className="h-4 w-4 text-amber-500" />
                    Doplňujúce informácie
                  </h2>
                  <p className="whitespace-pre-wrap leading-relaxed text-ink-soft">
                    {position.additional_info}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Pravý stĺpec — výzva k akcii a podmienky, drží sa pri scrollovaní */}
          <div className="lg:sticky lg:top-24 lg:self-start">
            <div className="space-y-4">
              <Card className="overflow-hidden border-brand-200 animate-rise">
                <CardContent className="p-6">
                  <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-accent-50 px-2.5 py-1 text-[11px] font-semibold text-accent-700 ring-1 ring-inset ring-accent-100">
                    <Sparkles className="h-3 w-3" />
                    Odpoveď hneď
                  </span>
                  <h2 className="text-base font-semibold text-ink">Zaujala vás pozícia?</h2>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
                    Napíšte nášmu asistentovi. Odpovie na otázky k pozícii a potom môžete rovno
                    prejaviť záujem.
                  </p>
                  <Button
                    className="mt-5 w-full"
                    size="lg"
                    onClick={() => navigate(`/${slug}/${positionId}/chat`)}
                  >
                    <MessageSquare className="h-4 w-4" />
                    Mám záujem / Chcem sa opýtať
                  </Button>
                </CardContent>
              </Card>

              {conditions.length > 0 && (
                <Card className="animate-rise">
                  <CardContent className="p-6">
                    <h2 className="mb-2 text-base font-semibold text-ink">Pracovné podmienky</h2>
                    <div className="divide-y divide-line">
                      {conditions.map(({ icon, label, value }) => (
                        <DetailRow key={label} icon={icon} label={label} value={value} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>
    </PublicShell>
  )
}
