/**
 * Čitateľný rozpis toho, ako uchádzač sadol na požiadavky pozície.
 *
 * Backend ukladá do `applicants.qualification_answers` celý podklad k skóre:
 * fakty, ktoré model vytiahol z CV a chatu, aj deterministický rozpis bodov
 * za jednotlivé požiadavky. Tu sa z toho robí niečo, čo prečíta personalistka
 * — nie surový JSON.
 */
import { CircleCheck, CircleQuestionMark, CircleX } from 'lucide-react'
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

const STATUS_META: Record<AiAnswer, { label: string; Icon: typeof CircleCheck; icon: string; chip: string }> = {
  yes: { label: 'Spĺňa', Icon: CircleCheck, icon: 'text-green-600', chip: 'bg-green-50 text-green-700' },
  no: { label: 'Nespĺňa', Icon: CircleX, icon: 'text-red-500', chip: 'bg-red-50 text-red-700' },
  unknown: {
    label: 'Nedoložené',
    Icon: CircleQuestionMark,
    icon: 'text-amber-500',
    chip: 'bg-amber-50 text-amber-700',
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
    <div className="flex gap-3 py-3">
      <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${meta.icon}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-gray-900">{sentenceCase(criterion.label)}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.chip}`}>{meta.label}</span>
          <span className="ml-auto shrink-0 text-xs text-gray-400">
            {num(criterion.earned)} z {num(criterion.weight)} b.
          </span>
        </div>

        {criterion.detail && <p className="mt-1 text-sm text-gray-600">{criterion.detail}</p>}

        {fact?.evidence ? (
          <p className="mt-1.5 border-l-2 border-gray-200 pl-2.5 text-sm italic text-gray-500">
            „{fact.evidence}“{source && <span className="not-italic text-xs text-gray-400"> — {source}</span>}
          </p>
        ) : (
          criterion.status === 'unknown' && (
            <p className="mt-1.5 text-sm text-gray-400">Uchádzač to neuviedol v životopise ani v chate.</p>
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

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-1">
          <h2 className="font-semibold text-gray-900">Splnenie požiadaviek</h2>
          {detail.requirements_ratio != null && (
            <span className="ml-auto text-sm text-gray-500">
              {Math.round(detail.requirements_ratio * 100)} % bodov
            </span>
          )}
        </div>
        <p className="text-xs text-gray-400 mb-2">
          Čo model našiel v životopise a v chate k požiadavkám, ktoré má pozícia zapnuté.
        </p>

        {criteria.length === 0 ? (
          <p className="py-3 text-sm text-gray-500">
            Pozícia nemá zadané žiadne požiadavky, nie je čo porovnávať.
          </p>
        ) : (
          <div className="divide-y divide-gray-100">
            {criteria.map((c) => (
              <CriterionRow key={c.key} criterion={c} fact={factFor(evaluation.profile, c.key)} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
