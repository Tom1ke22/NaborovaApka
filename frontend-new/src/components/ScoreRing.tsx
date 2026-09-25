/**
 * Kruhový ukazovateľ AI skóre uchádzača (0–10).
 *
 * Číslo samo o sebe personalistke veľa nepovie, preto ho dopĺňa farba a
 * vyplnený oblúk: zelená = sedí, jantárová = čiastočne, ružová = skôr nie.
 * Kým hodnotenie nedobehne, skóre je `null` a kruh ostáva prázdny.
 */
import { cn } from '@/lib/utils'
import { BAND_META, scoreBand } from '@/lib/score'

const SIZES = {
  sm: { box: 'h-12 w-12', ring: 4, num: 'text-sm', sub: 'text-[9px]' },
  md: { box: 'h-16 w-16', ring: 5, num: 'text-lg', sub: 'text-[10px]' },
  lg: { box: 'h-24 w-24', ring: 7, num: 'text-3xl', sub: 'text-[11px]' },
}

export function ScoreRing({
  score,
  size = 'md',
  className,
}: {
  score: number | null | undefined
  size?: keyof typeof SIZES
  className?: string
}) {
  const colors = BAND_META[scoreBand(score)]
  const dims = SIZES[size]
  const pct = score == null ? 0 : Math.max(0, Math.min(1, score / 10)) * 100

  return (
    <div
      className={cn('relative grid shrink-0 place-items-center', dims.box, className)}
      role="img"
      aria-label={score == null ? 'Skóre sa vyhodnocuje' : `AI skóre ${score} z 10`}
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(${colors.arc} ${pct}%, ${colors.track} ${pct}% 100%)`,
        }}
      />
      <div className="absolute rounded-full bg-white" style={{ inset: `${dims.ring}px` }} />
      <div className="relative flex flex-col items-center leading-none">
        {score == null ? (
          <span className={cn('font-bold text-ink-faint', dims.num)}>–</span>
        ) : (
          <>
            <span className={cn('font-bold tabular-nums', dims.num, colors.text)}>{score}</span>
            <span className={cn('mt-0.5 font-medium text-ink-faint', dims.sub)}>/10</span>
          </>
        )}
      </div>
    </div>
  )
}
