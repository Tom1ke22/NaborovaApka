/**
 * Pásma AI skóre uchádzača (0–10).
 *
 * Hranice sú rovnaké, aké používal zoznam záujemcov predtým (7 a 5), aby sa
 * hodnotenie nezmenilo — pribudol len jednotný názov a farba pre každé pásmo.
 */
export type ScoreBand = 'strong' | 'medium' | 'weak' | 'pending'

export const BAND_META: Record<
  ScoreBand,
  { arc: string; track: string; text: string; label: string }
> = {
  strong: { arc: '#059669', track: '#d1fae5', text: 'text-emerald-700', label: 'Veľmi vhodný' },
  medium: { arc: '#d97706', track: '#fef3c7', text: 'text-amber-700', label: 'Čiastočne vhodný' },
  weak: { arc: '#e11d48', track: '#ffe4e6', text: 'text-rose-700', label: 'Skôr nevhodný' },
  pending: { arc: '#cbd5e1', track: '#eceffa', text: 'text-ink-faint', label: 'Vyhodnocuje sa' },
}

export function scoreBand(score: number | null | undefined): ScoreBand {
  if (score == null) return 'pending'
  if (score >= 7) return 'strong'
  if (score >= 5) return 'medium'
  return 'weak'
}

export function scoreLabel(score: number | null | undefined): string {
  return BAND_META[scoreBand(score)].label
}
