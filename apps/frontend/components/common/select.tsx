'use client'

import { useId } from 'react'
import type { SelectHTMLAttributes } from 'react'
import { CaretDown } from '@phosphor-icons/react/dist/ssr'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'> {
  label: string
  helper?: string
  error?: string
  options: SelectOption[]
}

/**
 * A labelled select, matched to Field.
 *
 * The option list needs an explicit opaque background and colour of its own. A
 * `bg-transparent` select inherits near-white text from the dark theme but
 * Chrome still paints the dropdown on white, so the choices come out white on
 * white and unreadable. Setting both on the select and on each option is what
 * makes the popup follow the theme.
 */
export function Select({
  label,
  helper,
  error,
  options,
  className = '',
  ...rest
}: SelectProps) {
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
          'relative flex items-center rounded-[var(--radius-input)] bg-surface',
          'border transition-colors duration-150',
          'focus-within:outline focus-within:outline-2',
          'focus-within:outline-offset-2 focus-within:outline-focus',
          invalid ? 'border-state-error' : 'border-line-input',
          className,
        ].join(' ')}
      >
        <select
          {...rest}
          id={id}
          aria-describedby={helper || error ? describedBy : undefined}
          aria-invalid={invalid || undefined}
          // appearance-none: the native arrow is drawn in the platform's own
          // colours and does not follow the theme.
          // rounded-[inherit]: the opaque fill this control needs for its popup
          // was painted square over the wrapper's rounded corners, so the
          // border appeared to have none.
          className="text-body min-h-11 w-full appearance-none rounded-[inherit] bg-surface px-3 pr-10 text-ink outline-none"
        >
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              // Inline, not a class: the popup is rendered by the browser
              // outside the page, so utility classes do not reach it.
              style={{
                backgroundColor: 'var(--color-bg)',
                color: 'var(--color-ink)',
              }}
            >
              {option.label}
            </option>
          ))}
        </select>

        <CaretDown
          size={16}
          aria-hidden
          className="pointer-events-none absolute right-3 text-ink-muted"
        />
      </div>

      {(helper || error) && (
        <p
          id={describedBy}
          className={`text-body-sm ${error ? 'text-state-error' : 'text-ink-muted'}`}
        >
          {error || helper}
        </p>
      )}
    </div>
  )
}
