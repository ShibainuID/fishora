/**
 * TickMeter. DESIGN.md 8.5.
 *
 * Five hairline ticks. Filled ticks are 2px solid; empty ticks are 2px at 20%
 * opacity. Not a progress bar, not a filled track, not a dashboard widget.
 */
export interface TickMeterProps {
  value: number
}

const SEGMENTS = 5

export function TickMeter({ value }: TickMeterProps) {
  const filled = Math.min(SEGMENTS, Math.max(0, Math.round(value * SEGMENTS)))

  return (
    <div className="flex items-center gap-1" aria-hidden>
      {Array.from({ length: SEGMENTS }, (_, i) => (
        <span
          key={i}
          data-tick={i < filled ? 'filled' : 'empty'}
          className={[
            'h-0.5 w-3',
            i < filled ? 'bg-ink' : 'bg-ink/20',
          ].join(' ')}
        />
      ))}
    </div>
  )
}
