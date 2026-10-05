/**
 * Čitateľný rozpis toho, ako uchádzač sadol na požiadavky pozície.
 *
 * Backend ukladá do `applicants.qualification_answers` celý podklad k skóre:
 * fakty, ktoré model vytiahol z CV a chatu, aj deterministický rozpis bodov
 * za jednotlivé požiadavky. Tu sa z toho robí niečo, čo prečíta personalistka
 * — nie surový JSON.
 */
import { CircleAlert, CircleCheck, CircleQuestionMark, CircleX, ListChecks } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { AI_SOURCE_LABELS, aiVerdict } from '@/types'
import type { AiCriterion, AiEvaluation, AiFact, AiProfile, AiVerdict } from '@/types'

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

/**
 * Zelená patrí výhradne `documented`. Tvrdenie z chatu je žlté a výslovne
 * pomenované „podľa uchádzača", aby si personalistka nikdy nemohla pomýliť
 * doklad so vetou, ktorú uchádzač napísal do chatu.
 *
 * „Nedoložené" je zámerne neutrálne sivé, nie žlté: žltá teraz znamená
 * „pozor, neoverené", a chýbajúci údaj nie je to isté ako neoverené tvrdenie.
 */
const VERDICT_META: Record<
  AiVerdict,
  { label: string; Icon: typeof CircleCheck; icon: string; chip: string; row: string; note?: string }
> = {
  documented: {
    label: 'Doložené v CV',
    Icon: CircleCheck,
    icon: 'text-emerald-600',
    chip: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    row: 'bg-emerald-50/40',
  },
  claimed: {
    label: 'Podľa uchádzača',
    Icon: CircleAlert,
    icon: 'text-amber-500',
    chip: 'bg-amber-50 text-amber-800 ring-amber-300',
    row: 'bg-amber-50/50',
    note: 'Uchádzač to uviedol v chate, v životopise to doložené nie je.',
  },
  unmet: {
    label: 'Nespĺňa',
    Icon: CircleX,
    icon: 'text-rose-500',
    chip: 'bg-rose-50 text-rose-700 ring-rose-200',
    row: 'bg-rose-50/40',
  },
  undocumented: {
    label: 'Nedoložené',
    Icon: CircleQuestionMark,
    icon: 'text-ink-faint',
    chip: 'bg-surface-sunken text-ink-soft ring-line-strong',
    row: 'bg-surface-sunken/60',
    note: 'Uchádzač to neuviedol v životopise ani v chate.',
  },
}

/** „prax v odbore" → „Prax v odbore". CSS `capitalize` by zdvihlo každé slovo. */
function sentenceCase(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function factFor(profile: AiProfile | undefined, key: string): AiFact | undefined {
  if (!profile) return undefined
  if ((FACT_KEYS as readonly string[]).includes(key)) {
    return profile[key as (typeof FACT_KEYS)[number]]
  }
  // Vlastné požiadavky nemajú pevné pole, chodia ako zoznam s kľúčom.
  return profile.custom_requirements?.find((fact) => fact.key === key)
}

/* --------------------------------------------------------------------------
 * Splnenie požiadaviek — rozpis po jednotlivých kritériách
 * ------------------------------------------------------------------------ */

function CriterionRow({ criterion, fact }: { criterion: AiCriterion; fact?: AiFact }) {
  const verdict = aiVerdict(criterion)
  const meta = VERDICT_META[verdict]
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
        </div>

        {criterion.detail && <p className="mt-1 text-sm text-ink-soft">{criterion.detail}</p>}

        {fact?.evidence && (
          <p className="mt-2 border-l-2 border-line-strong pl-2.5 text-sm italic text-ink-soft">
            „{fact.evidence}“
            {source && <span className="not-italic text-xs text-ink-faint"> — {source}</span>}
          </p>
        )}

        {meta.note && <p className="mt-1.5 text-sm text-ink-faint">{meta.note}</p>}
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
  const claimed = criteria.filter((c) => aiVerdict(c) === 'claimed')

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
              Splnené na {pct} %
            </span>
          )}
        </div>

        <p className="text-xs text-ink-faint">
          Čo model našiel v životopise a v chate k požiadavkám, ktoré má pozícia zapnuté.
          Zelené je doložené v životopise, žlté uchádzač iba povedal v chate.
        </p>

        {claimed.length > 0 && (
          <p className="mt-3 flex gap-2 rounded-xl bg-amber-50 px-3 py-2.5 text-sm text-amber-900 ring-1 ring-inset ring-amber-200">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <span>
              {claimed.length === 1
                ? 'Jedna požiadavka je splnená len podľa slov uchádzača'
                : `${claimed.length} požiadavky sú splnené len podľa slov uchádzača`}{' '}
              a v životopise doložené nie sú: {claimed.map((c) => c.label).join(', ')}. Do skóre
              sa počítajú len čiastočne — overte si ich na pohovore.
            </span>
          </p>
        )}

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
