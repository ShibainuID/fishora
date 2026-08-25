'use client'

import { useId } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'
import { WarningCircle } from '@phosphor-icons/react/dist/ssr'

export interface FieldProps
  // `prefix` is a real HTML attribute, shadowed here with a richer type.
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'prefix'> {
  label: string
  helper?: string
  error?: string
  /** Inside the leading edge, e.g. `Rp`. */
  prefix?: ReactNode
  /** Inside the trailing edge, e.g. `kg`. */
  suffix?: ReactNode
  /** Renders a textarea. For long free text, where an input is unusable. */
  multiline?: boolean
  rows?: number
}

export function Field({
  label,
  helper,
  error,
  prefix,
  suffix,
  multiline = false,
  rows = 4,
  className = '',
  ...rest
}: FieldProps) {
  const id = useId()
  const describedBy = `${id}-desc`
  const invalid = Boolean(error)

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>

      <div
        className={[
          'flex items-center gap-2 rounded-[var(--radius-input)] bg-surface',
          'border px-3 transition-colors duration-150',
          'focus-within:outline focus-within:outline-2',
          'focus-within:outline-offset-2 focus-within:outline-focus',
          invalid ? 'border-state-error' : 'border-line-input',
          className,
        ].join(' ')}
      >
        {prefix && (
          <span className="text-num-sm shrink-0 text-ink-muted" aria-hidden>
            {prefix}
          </span>
        )}
        {multiline ? (
          <textarea
            {...(rest as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
            id={id}
            rows={rows}
            aria-invalid={invalid || undefined}
            aria-describedby={describedBy}
            className="min-h-11 w-full resize-y bg-transparent py-2 text-ink outline-none"
          />
        ) : (
          <input
            {...rest}
            id={id}
            aria-invalid={invalid || undefined}
            aria-describedby={describedBy}
            className="min-h-11 w-full bg-transparent text-ink outline-none"
          />
        )}
        {suffix && (
          <span className="text-num-sm shrink-0 text-ink-muted" aria-hidden>
            {suffix}
          </span>
        )}
      </div>

      {/* Reserved line. Occupies space whether or not it has content. */}
      <p
        id={describedBy}
        className={[
          'text-body-sm flex min-h-5 items-start gap-1.5',
          invalid ? 'text-state-error' : 'text-ink-muted',
        ].join(' ')}
      >
        {invalid && (
          <WarningCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
        )}
        {error ?? helper ?? ' '}
      </p>
    </div>
  )
}
