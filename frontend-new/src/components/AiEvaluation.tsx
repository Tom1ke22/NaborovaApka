/**
 * Čitateľný rozpis toho, ako uchádzač sadol na požiadavky pozície.
 *
 * Backend ukladá do `applicants.qualification_answers` celý podklad k skóre:
 * fakty, ktoré model vytiahol z CV a chatu, aj deterministický rozpis bodov
 * za jednotlivé požiadavky. Tu sa z toho robí niečo, čo prečíta personalistka
 * — nie surový JSON.
 */
import { CircleCheck, CircleQuestionMark, CircleX, ListChecks } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { AI_SOURCE_LABELS } from '@/types'
import type { AiAnswer, AiCriterion, AiEvaluation, AiFact, AiProfile } from '@/types'

/* --------------------------------------------------------------------------
 * Pomocné mapovania
 * ------------------------------------------------------------------------ */

/** Kľúče kritérií, ku ktorým existuje fakt v profile (rovnaké názvy polí). */
const FACT_KEYS = [
  'hygiene_minimum',
  'health_certificate',
  'experience',
  'education',
  'slovak_language',
  'foreign_language',
] as const

const STATUS_META: Record<
  AiAnswer,
  { label: string; Icon: typeof CircleCheck; icon: string; chip: string; row: string }
> = {
  yes: {
    label: 'Spĺňa',
    Icon: CircleCheck,
    icon: 'text-emerald-600',
    chip: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    row: 'bg-emerald-50/40',
  },
  no: {
    label: 'Nespĺňa',
    Icon: CircleX,
    icon: 'text-rose-500',
    chip: 'bg-rose-50 text-rose-700 ring-rose-200',
    row: 'bg-rose-50/40',
  },
  unknown: {
    label: 'Nedoložené',
    Icon: CircleQuestionMark,
    icon: 'text-amber-500',
    chip: 'bg-amber-50 text-amber-700 ring-amber-200',
    row: 'bg-amber-50/40',
  },
}

/** 2 → „2", 1.5 → „1,5". Body chodia z backendu ako desatinné čísla. */
function num(n: number): string {
  return Number(n.toFixed(2)).toString().replace('.', ',')
}

/** „prax v odbore" → „Prax v odbore". CSS `capitalize` by zdvihlo každé slovo. */
function sentenceCase(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function factFor(profile: AiProfile | undefined, key: string): AiFact | undefined {
  if (!profile || !(FACT_KEYS as readonly string[]).includes(key)) return undefined
  return profile[key as (typeof FACT_KEYS)[number]]
}

/* --------------------------------------------------------------------------
 * Splnenie požiadaviek — rozpis po jednotlivých kritériách
 * ------------------------------------------------------------------------ */

function CriterionRow({ criterion, fact }: { criterion: AiCriterion; fact?: AiFact }) {
  const meta = STATUS_META[criterion.status] ?? STATUS_META.unknown
  const { Icon } = meta
  const source = AI_SOURCE_LABELS[fact?.source ?? criterion.source] || ''

  return (
    <div className={`flex gap-3 rounded-xl px-3.5 py-3 ${meta.row}`}>
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${meta.icon}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">{sentenceCase(criterion.label)}</span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${meta.chip}`}
          >
            {meta.label}
          </span>
          <span className="ml-auto shrink-0 text-xs font-medium tabular-nums text-ink-faint">
            {num(criterion.earned)} z {num(criterion.weight)} b.
          </span>
        </div>

        {criterion.detail && <p className="mt-1 text-sm text-ink-soft">{criterion.detail}</p>}

        {fact?.evidence ? (
          <p className="mt-2 border-l-2 border-line-strong pl-2.5 text-sm italic text-ink-soft">
            „{fact.evidence}“
            {source && <span className="not-italic text-xs text-ink-faint"> — {source}</span>}
          </p>
        ) : (
          criterion.status === 'unknown' && (
            <p className="mt-1.5 text-sm text-ink-faint">
              Uchádzač to neuviedol v životopise ani v chate.
            </p>
          )
        )}
      </div>
    </div>
  )
}

export function RequirementsCard({ evaluation }: { evaluation: AiEvaluation }) {
  const detail = evaluation.score
  const criteria = detail?.criteria ?? []

  if (!detail) return null

  const ratio = detail.requirements_ratio
  const pct = ratio != null ? Math.round(ratio * 100) : null

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-1 flex items-center gap-2">
          <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
            <ListChecks className="h-4 w-4 text-accent-600" />
            Splnenie požiadaviek
          </h2>
          {pct != null && (
            <span className="ml-auto text-sm font-semibold tabular-nums text-ink-soft">
              {pct} % bodov
            </span>
          )}
        </div>

        <p className="text-xs text-ink-faint">
          Čo model našiel v životopise a v chate k požiadavkám, ktoré má pozícia zapnuté.
        </p>

        {pct != null && (
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-sunken">
            <div
              className={`h-full rounded-full transition-[width] duration-700 ${
                pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        )}

        {criteria.length === 0 ? (
          <p className="mt-4 rounded-xl bg-surface-sunken px-4 py-6 text-center text-sm text-ink-soft">
            Pozícia nemá zadané žiadne požiadavky, nie je čo porovnávať.
          </p>
        ) : (
          <div className="mt-4 space-y-2">
            {criteria.map((c) => (
              <CriterionRow key={c.key} criterion={c} fact={factFor(evaluation.profile, c.key)} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
