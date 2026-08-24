'use client'

import { useId } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'
import { WarningCircle } from '@phosphor-icons/react/dist/ssr'

/**
 * Field. DESIGN.md 8.2 and 4.6.
 *
 * Locked rules this component enforces:
 * - Label above the input. Always a real <label for>. Never a placeholder
 *   standing in for a label.
 * - Helper text is always in the DOM, even when empty, so revealing an error
 *   cannot reflow the form under the user's thumb.
 * - Error replaces helper text and wires aria-invalid + aria-describedby.
 * - 44px minimum height, 16px minimum type, so iOS does not zoom on focus.
 */

export interface FieldProps
  // `id` is owned by useId. `prefix` is a real HTML attribute (a URI string on
  // some elements) and is deliberately shadowed here with a richer type.
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'prefix'> {
  label: string
  helper?: string
  error?: string
  /** Rendered inside the input's leading edge, e.g. `Rp` on a price field. */
  prefix?: ReactNode
  /** Rendered inside the trailing edge, e.g. `kg`. */
  suffix?: ReactNode
}

export function Field({
  label,
  helper,
  error,
  prefix,
  suffix,
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
        <input
          {...rest}
          id={id}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className="min-h-11 w-full bg-transparent text-ink outline-none"
        />
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
